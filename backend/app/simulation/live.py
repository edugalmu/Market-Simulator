from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from math import pi, sin
from random import Random
from threading import Event, Lock, Thread, current_thread
from uuid import uuid4

from app.agents.base import AgentProfile, StrategyType
from app.agents.registry import summarize_agent_mix
from app.core.events import OrderSide
from app.core.ledger import AgentBalance, Ledger
from app.core.matching import MatchResult, execute_market_buy_by_notional, execute_market_order
from app.core.order_book import OrderBook
from app.simulation.engine import SimulationEngine
from app.simulation.models import (
    AgentMixEntry,
    GameFinalResult,
    GameScoreBreakdown,
    LiveGameState,
    LiveSimulationSnapshot,
    LiveWhaleOrderOutcome,
    LiveWhaleOrderResponse,
    MarketRegimeState,
    OhlcvBar,
    SessionConfig,
    TickReport,
    TopAgentEntry,
    WhaleBalanceSnapshot,
)
from app.simulation.scheduler import select_active_agent_count


DEFAULT_TICK_INTERVAL_MS = 750
SIMULATED_TICK_INTERVAL_MS = 1000
MAX_PRICE_HISTORY = 24
MAX_OHLCV_HISTORY = 80
PRELOADED_WINDOW_MS = 10 * 60 * 1000
PRELOADED_HISTORY_MARGIN = 12
RIVAL_WHALE_COUNT = 9
RIVAL_WHALE_SHARE_PER_WHALE = 0.02
RIVAL_WHALE_CASH_WEIGHT = 0.50
RIVAL_WHALE_LEVERAGE_MIN = 1.4
RIVAL_WHALE_LEVERAGE_MAX = 3.2
MONEY_GROWTH_INTERVAL_TICKS = 60
MONEY_GROWTH_MULTIPLIER = 1.03
TEN_MINUTE_SENTIMENT_INTERVAL_TICKS = 10 * 60
ONE_MINUTE_SENTIMENT_INTERVAL_TICKS = 60
WHALE_AGENT_ID = 0
WHALE_TARGET_CAPITAL_SHARE = 0.20
WHALE_CASH_WEIGHT = 0.50
SHOCK_BIAS_DECAY = 0.72
MAX_SHOCK_BIAS_BPS = 85.0
WHALE_CHALLENGE_MODE = "whale_challenge"
WHALE_CHALLENGE_DURATION_TICKS = 60
WHALE_SHOCK_THRESHOLD_USD = 50_000
PANIC_PRICE_CHANGE_BPS = -120.0
SHORT_SQUEEZE_PRICE_CHANGE_BPS = 120.0

REGIME_PARAMS: dict[str, dict[str, float | tuple[int, int]]] = {
    "neutral": {
        "duration": (100, 500),
        "buy_bias": 0.50,
        "sell_bias": 0.50,
        "volatility_multiplier": 0.5,
        "liquidity_multiplier": 1.5,
        "spread_multiplier": 1.0,
        "whale_activity_multiplier": 0.7,
        "momentum_multiplier": 0.8,
        "mean_reversion_multiplier": 1.2,
        "maker_cancel_multiplier": 0.8,
        "gap_probability": 0.08,
    },
    "accumulation": {
        "duration": (80, 300),
        "buy_bias": 0.58,
        "sell_bias": 0.42,
        "volatility_multiplier": 0.7,
        "liquidity_multiplier": 1.2,
        "spread_multiplier": 1.1,
        "whale_activity_multiplier": 0.8,
        "momentum_multiplier": 0.9,
        "mean_reversion_multiplier": 1.3,
        "maker_cancel_multiplier": 0.9,
        "gap_probability": 0.10,
    },
    "uptrend": {
        "duration": (50, 200),
        "buy_bias": 0.70,
        "sell_bias": 0.30,
        "volatility_multiplier": 1.2,
        "liquidity_multiplier": 1.0,
        "spread_multiplier": 1.2,
        "whale_activity_multiplier": 1.0,
        "momentum_multiplier": 1.5,
        "mean_reversion_multiplier": 0.7,
        "maker_cancel_multiplier": 1.0,
        "gap_probability": 0.15,
    },
    "distribution": {
        "duration": (80, 300),
        "buy_bias": 0.42,
        "sell_bias": 0.58,
        "volatility_multiplier": 0.8,
        "liquidity_multiplier": 1.2,
        "spread_multiplier": 1.1,
        "whale_activity_multiplier": 0.8,
        "momentum_multiplier": 0.9,
        "mean_reversion_multiplier": 1.3,
        "maker_cancel_multiplier": 0.9,
        "gap_probability": 0.12,
    },
    "downtrend": {
        "duration": (50, 200),
        "buy_bias": 0.30,
        "sell_bias": 0.70,
        "volatility_multiplier": 1.3,
        "liquidity_multiplier": 0.9,
        "spread_multiplier": 1.3,
        "whale_activity_multiplier": 1.0,
        "momentum_multiplier": 1.5,
        "mean_reversion_multiplier": 0.7,
        "maker_cancel_multiplier": 1.1,
        "gap_probability": 0.18,
    },
    "panic": {
        "duration": (10, 30),
        "buy_bias": 0.10,
        "sell_bias": 0.90,
        "volatility_multiplier": 3.0,
        "liquidity_multiplier": 0.3,
        "spread_multiplier": 4.0,
        "whale_activity_multiplier": 1.8,
        "momentum_multiplier": 2.0,
        "mean_reversion_multiplier": 0.3,
        "maker_cancel_multiplier": 3.0,
        "gap_probability": 0.50,
    },
    "short_squeeze": {
        "duration": (5, 20),
        "buy_bias": 0.95,
        "sell_bias": 0.05,
        "volatility_multiplier": 4.0,
        "liquidity_multiplier": 0.2,
        "spread_multiplier": 5.0,
        "whale_activity_multiplier": 2.0,
        "momentum_multiplier": 2.5,
        "mean_reversion_multiplier": 0.2,
        "maker_cancel_multiplier": 3.5,
        "gap_probability": 0.55,
    },
    "post_whale_consolidation": {
        "duration": (30, 80),
        "buy_bias": 0.50,
        "sell_bias": 0.50,
        "volatility_multiplier": 0.2,
        "liquidity_multiplier": 0.5,
        "spread_multiplier": 2.5,
        "whale_activity_multiplier": 0.4,
        "momentum_multiplier": 0.5,
        "mean_reversion_multiplier": 1.0,
        "maker_cancel_multiplier": 1.8,
        "gap_probability": 0.35,
    },
}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@dataclass(slots=True)
class AgentRuntimeState:
    fair_value_estimate: float
    aggression_level: float
    cooldown_ticks: int
    last_action_tick: int = -10_000
    intent_side: int = 0
    intent_ticks_remaining: int = 0
    risk_appetite: float = 1.0
    inventory_target: float = 0.0
    directional_side: int = 0
    directional_ticks_remaining: int = 0


@dataclass(slots=True)
class AgentActionResult:
    side: OrderSide
    match_result: MatchResult | None = None
    placed_limit: bool = False


@dataclass(slots=True)
class RivalWhaleState:
    whale_id: int
    alias: str
    cash: float
    asset: float
    leverage_limit: float
    aggression: float
    cooldown_ticks: int
    last_action_tick: int = -10_000

    def total_equity(self, mark_price: float) -> float:
        return self.cash + self.asset * mark_price


@dataclass(slots=True)
class WhaleMoodState:
    session_score: float
    ten_minute_score: float
    minute_score: float
    next_ten_minute_roll_tick: int
    next_minute_roll_tick: int


@dataclass(slots=True)
class RegimeRuntimeState:
    name: str
    ticks_remaining: int
    buy_bias: float
    sell_bias: float
    volatility_multiplier: float
    liquidity_multiplier: float
    spread_multiplier: float
    whale_activity_multiplier: float
    momentum_multiplier: float
    mean_reversion_multiplier: float
    maker_cancel_multiplier: float
    gap_probability: float
    reason: str | None = None


@dataclass(slots=True)
class GameRuntimeState:
    mode: str | None = None
    status: str = "idle"
    started_at_tick: int | None = None
    duration_ticks: int = WHALE_CHALLENGE_DURATION_TICKS
    remaining_ticks: int = WHALE_CHALLENGE_DURATION_TICKS
    score: float = 0.0
    score_breakdown: dict[str, float] = field(
        default_factory=lambda: {
            "pnl_score": 0.0,
            "impact_score": 0.0,
            "volume_score": 0.0,
        }
    )
    final_result: GameFinalResult | None = None
    starting_price: float | None = None
    total_whale_impact_bps: float = 0.0
    max_whale_impact_bps: float = 0.0
    total_whale_volume: float = 0.0
    whale_orders: int = 0


@dataclass(slots=True)
class LiveSessionState:
    session_id: str
    config: SessionConfig
    engine: SimulationEngine
    active_backend: str
    profiles: list[AgentProfile]
    ledger: Ledger
    whale_ledger: Ledger
    order_book: OrderBook
    rng: Random
    tick_interval_ms: int
    running: bool
    last_price: float
    whale_initial_cash: float
    whale_initial_asset: float
    whale_initial_mark_price: float
    whale_initial_total_equity: float
    preloaded_ticks_total: int
    preload_pattern: str
    rival_whales: list[RivalWhaleState]
    whale_mood: WhaleMoodState
    market_regime: RegimeRuntimeState
    next_cash_growth_tick: int
    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)
    tick: int = 0
    structural_bias_bps: float = 0.0
    cumulative_trades: int = 0
    cumulative_matched_notional: float = 0.0
    cumulative_matched_quantity: float = 0.0
    price_history: deque[float] = field(
        default_factory=lambda: deque(maxlen=MAX_PRICE_HISTORY)
    )
    ohlcv_history: deque[OhlcvBar] = field(
        default_factory=lambda: deque(maxlen=MAX_OHLCV_HISTORY)
    )
    runtime_state: dict[int, AgentRuntimeState] = field(default_factory=dict)
    game: GameRuntimeState = field(default_factory=GameRuntimeState)
    last_tick: TickReport | None = None
    last_whale_order: LiveWhaleOrderOutcome | None = None


class LiveSimulationService:
    def __init__(self) -> None:
        self._lock = Lock()
        self._session: LiveSessionState | None = None
        self._thread: Thread | None = None
        self._stop_event = Event()

    def start(
        self,
        config: SessionConfig,
        *,
        gpu_enabled: bool,
        tick_interval_ms: int = DEFAULT_TICK_INTERVAL_MS,
        auto_run: bool = True,
    ) -> LiveSimulationSnapshot:
        self.reset()

        engine = SimulationEngine(gpu_enabled=gpu_enabled)
        active_backend, profiles, ledger, order_book = engine.build_market_state(config)
        order_book.ensure_depth_around(config.initial_price, base_quantity=8.0)
        rng = Random(config.seed)
        whale_initial_cash, whale_initial_asset = _build_whale_initial_portfolio(
            config,
            reference_price=config.initial_price,
        )
        whale_initial_total_equity = round(
            whale_initial_cash + whale_initial_asset * config.initial_price,
            6,
        )
        rival_whales = _build_rival_whales(
            total_agent_equity=ledger.total_equity(config.initial_price),
            reference_price=config.initial_price,
            rng=rng,
        )
        whale_mood = _build_whale_mood_state(rng, current_tick=0)
        whale_ledger = Ledger(
            {
                WHALE_AGENT_ID: AgentBalance(
                    cash_free=whale_initial_cash,
                    cash_reserved=0.0,
                    asset_free=whale_initial_asset,
                    asset_reserved=0.0,
                )
            }
        )
        history_size = _history_size_for()
        preloaded_tick_count = _preloaded_tick_count()
        preload_pattern = _choose_preload_pattern(rng)
        market_regime = _build_initial_market_regime(preload_pattern=preload_pattern, rng=rng)

        session = LiveSessionState(
            session_id=f"live-{config.seed}-{uuid4().hex[:8]}",
            config=config,
            engine=engine,
            active_backend=active_backend,
            profiles=profiles,
            ledger=ledger,
            whale_ledger=whale_ledger,
            order_book=order_book,
            rng=rng,
            tick_interval_ms=tick_interval_ms,
            running=auto_run,
            last_price=order_book.mid_price or config.initial_price,
            whale_initial_cash=whale_initial_cash,
            whale_initial_asset=whale_initial_asset,
            whale_initial_mark_price=config.initial_price,
            whale_initial_total_equity=whale_initial_total_equity,
            preloaded_ticks_total=preloaded_tick_count,
            preload_pattern=preload_pattern,
            rival_whales=rival_whales,
            whale_mood=whale_mood,
            market_regime=market_regime,
            next_cash_growth_tick=MONEY_GROWTH_INTERVAL_TICKS,
            price_history=deque([order_book.mid_price or config.initial_price], maxlen=history_size),
            ohlcv_history=deque(maxlen=history_size),
            runtime_state={
                profile.agent_id: AgentRuntimeState(
                    fair_value_estimate=round(
                        config.initial_price * (1 + rng.uniform(-0.025, 0.025)),
                        4,
                    ),
                    aggression_level=round(rng.uniform(0.7, 1.3), 4),
                    cooldown_ticks=_cooldown_for(profile.strategy),
                    risk_appetite=round(rng.uniform(0.85, 1.45), 4),
                    inventory_target=round(config.initial_asset * rng.uniform(0.35, 1.65), 4),
                )
                for profile in profiles
            },
        )

        with self._lock:
            self._stop_event = Event()
            self._session = session
            for _ in range(preloaded_tick_count):
                self._advance_session_locked(session)
            self._reset_whale_baseline_locked(session)

        if auto_run:
            thread = Thread(
                target=self._run_loop,
                args=(session.session_id, self._stop_event),
                daemon=True,
                name="market-simulator-live-loop",
            )
            self._thread = thread
            thread.start()

        return self.get_snapshot(raise_if_missing=True)

    def get_snapshot(self, *, raise_if_missing: bool = False) -> LiveSimulationSnapshot | None:
        with self._lock:
            if self._session is None:
                if raise_if_missing:
                    raise LookupError("No live simulation session is currently active.")
                return None

            return self._build_snapshot(self._session)

    def step(self, *, ticks: int = 1) -> LiveSimulationSnapshot:
        with self._lock:
            if self._session is None:
                raise LookupError("No live simulation session is currently active.")

            for _ in range(ticks):
                self._advance_session_locked(self._session)

            return self._build_snapshot(self._session)

    def execute_whale_order(
        self,
        *,
        side: OrderSide | str,
        notional: float,
    ) -> LiveWhaleOrderResponse:
        with self._lock:
            if self._session is None:
                raise LookupError("No live simulation session is currently active.")
            if notional <= 0:
                raise ValueError("Whale order notional must be positive.")

            return self._execute_whale_order_locked(
                self._session,
                side=OrderSide(side),
                notional=notional,
            )

    def stop(self) -> LiveSimulationSnapshot:
        snapshot = self._stop(clear_session=False)
        if snapshot is None:
            raise LookupError("No live simulation session is currently active.")
        return snapshot

    def play(self, *, tick_interval_ms: int | None = None) -> LiveSimulationSnapshot:
        thread_to_join: Thread | None = None
        thread_to_start: Thread | None = None

        with self._lock:
            if self._session is None:
                raise LookupError("No live simulation session is currently active.")

            session = self._session
            interval_changed = (
                tick_interval_ms is not None
                and tick_interval_ms != session.tick_interval_ms
            )
            if tick_interval_ms is not None:
                session.tick_interval_ms = tick_interval_ms

            session.running = True
            session.updated_at = _utc_now()

            should_restart_thread = (
                self._thread is None
                or not self._thread.is_alive()
                or self._stop_event.is_set()
                or interval_changed
            )
            if should_restart_thread:
                if self._thread is not None and self._thread.is_alive():
                    self._stop_event.set()
                    thread_to_join = self._thread

                self._stop_event = Event()
                thread_to_start = Thread(
                    target=self._run_loop,
                    args=(session.session_id, self._stop_event),
                    daemon=True,
                    name="market-simulator-live-loop",
                )
                self._thread = thread_to_start

            snapshot = self._build_snapshot(session)

        if (
            thread_to_join is not None
            and thread_to_join.is_alive()
            and thread_to_join is not current_thread()
        ):
            thread_to_join.join(timeout=2.0)

        if thread_to_start is not None:
            thread_to_start.start()

        return snapshot

    def start_game(
        self,
        *,
        mode: str = WHALE_CHALLENGE_MODE,
        duration_ticks: int = WHALE_CHALLENGE_DURATION_TICKS,
    ) -> LiveSimulationSnapshot:
        with self._lock:
            if self._session is None:
                raise LookupError("No live simulation session is currently active.")

            session = self._session
            session.game = GameRuntimeState(
                mode=mode,
                status="running",
                started_at_tick=session.tick,
                duration_ticks=duration_ticks,
                remaining_ticks=duration_ticks,
                starting_price=session.last_price,
            )
            session.updated_at = _utc_now()
            self._refresh_game_score_locked(session)

            return self._build_snapshot(session)

    def end_game(self) -> LiveSimulationSnapshot:
        with self._lock:
            if self._session is None:
                raise LookupError("No live simulation session is currently active.")

            self._end_game_locked(self._session)
            return self._build_snapshot(self._session)

    def reset_game(self) -> LiveSimulationSnapshot:
        with self._lock:
            if self._session is None:
                raise LookupError("No live simulation session is currently active.")

            duration_ticks = self._session.game.duration_ticks or WHALE_CHALLENGE_DURATION_TICKS
            self._session.game = GameRuntimeState(
                duration_ticks=duration_ticks,
                remaining_ticks=duration_ticks,
            )
            self._session.updated_at = _utc_now()
            return self._build_snapshot(self._session)

    def reset(self) -> None:
        self._stop(clear_session=True)

    def _stop(self, *, clear_session: bool) -> LiveSimulationSnapshot | None:
        thread_to_join: Thread | None = None

        with self._lock:
            session = self._session
            if session is None:
                return None

            session.running = False
            session.updated_at = _utc_now()
            self._stop_event.set()
            thread_to_join = self._thread
            self._thread = None
            snapshot = self._build_snapshot(session)

        if (
            thread_to_join is not None
            and thread_to_join.is_alive()
            and thread_to_join is not current_thread()
        ):
            thread_to_join.join(timeout=2.0)

        if clear_session:
            with self._lock:
                self._session = None
            return None

        return snapshot

    def _run_loop(self, session_id: str, stop_event: Event) -> None:
        while True:
            with self._lock:
                if self._session is None or self._session.session_id != session_id:
                    return
                if not self._session.running:
                    return

                interval_seconds = max(self._session.tick_interval_ms / 1000, 0.1)

            if stop_event.wait(interval_seconds):
                return

            with self._lock:
                if self._session is None or self._session.session_id != session_id:
                    return
                if not self._session.running:
                    return

                self._advance_session_locked(self._session)

    def _advance_session_locked(self, session: LiveSessionState) -> None:
        session.tick += 1
        self._advance_market_regime_locked(session)
        self._roll_whale_mood_locked(session)
        self._apply_cash_growth_locked(session)
        session.order_book.expire_orders()
        session.order_book.cancel_random_orders(
            rng=session.rng,
            max_ratio=0.03,
            min_age_ticks=4,
            current_tick=session.tick,
        )
        session.order_book.cancel_random_orders(
            rng=session.rng,
            max_ratio=min(0.10 * session.market_regime.maker_cancel_multiplier, 0.45),
            min_age_ticks=1,
            current_tick=session.tick,
            strategy_type=StrategyType.MARKET_MAKER.value,
        )
        price_before = session.last_price
        short_anchor = sum(session.price_history) / len(session.price_history)
        active_count = select_active_agent_count(
            len(session.profiles),
            activation_ratio=0.03,
        )
        sampled_profiles = session.rng.sample(session.profiles, k=active_count)

        active_agents = 0
        buy_orders = 0
        sell_orders = 0
        trades_executed = 0
        matched_notional = 0.0
        matched_quantity = 0.0
        observed_prices = [price_before]

        for profile in sampled_profiles:
            runtime = session.runtime_state[profile.agent_id]
            if session.tick - runtime.last_action_tick <= runtime.cooldown_ticks:
                continue

            result = self._execute_profile_action(
                session,
                profile,
                runtime,
                current_price=price_before,
                anchor_price=short_anchor,
            )
            if result is None:
                continue

            runtime.last_action_tick = session.tick
            active_agents += 1
            if result.side == OrderSide.BUY:
                buy_orders += 1
            else:
                sell_orders += 1

            if result.match_result is not None:
                trades_executed += result.match_result.trades_executed
                matched_notional += result.match_result.matched_notional
                matched_quantity += result.match_result.quantity_matched
                observed_prices.append(session.order_book.mid_price or result.match_result.average_fill_price or price_before)

        rival_flow = self._execute_rival_whales_locked(
            session,
            current_price=price_before,
        )
        active_agents += rival_flow[0]
        buy_orders += rival_flow[1]
        sell_orders += rival_flow[2]
        trades_executed += rival_flow[3]
        matched_notional += rival_flow[4]
        matched_quantity += rival_flow[5]
        observed_prices.extend(rival_flow[6])
        rival_pressure_bps = rival_flow[7]

        flow_imbalance = buy_orders - sell_orders
        drift_bps = max(
            min(
                flow_imbalance * 1.35
                + session.structural_bias_bps
                + _preload_pattern_bias_bps(session)
                + _market_mood_bias_bps(session)
                + _market_regime_drift_bps(session)
                + rival_pressure_bps
                + session.rng.uniform(-0.8, 0.8),
                16.0 * session.market_regime.volatility_multiplier,
            ),
            -14.0 * session.market_regime.volatility_multiplier,
        )
        reference_price = max(price_before * (1 + drift_bps / 10_000), 1.0)
        session.order_book.ensure_depth_around(
            reference_price,
            base_quantity=_base_liquidity_for_bias(session.structural_bias_bps) * session.market_regime.liquidity_multiplier,
            created_tick=session.tick,
            ttl_ticks=8,
            strategy_type=StrategyType.MARKET_MAKER.value,
            spacing_bps=10.0 * session.market_regime.spread_multiplier,
            rng=session.rng,
            gap_probability=session.market_regime.gap_probability,
        )
        price_after = session.order_book.mid_price or reference_price
        session.last_price = round(price_after, 4)
        session.price_history.append(session.last_price)
        observed_prices.append(price_after)
        session.updated_at = _utc_now()
        session.structural_bias_bps = _decay_bias(session.structural_bias_bps)
        session.cumulative_trades += trades_executed
        session.cumulative_matched_notional += matched_notional
        session.cumulative_matched_quantity += matched_quantity

        price_change_bps = 0.0
        if price_before > 0:
            price_change_bps = round(
                ((price_after - price_before) / price_before) * 10_000,
                4,
            )

        _handle_market_regime_reaction_locked(
            session,
            price_change_bps=price_change_bps,
            trades_executed=trades_executed,
        )

        session.last_tick = TickReport(
            tick=session.tick,
            active_agents=active_agents,
            buy_orders=buy_orders,
            sell_orders=sell_orders,
            trades_executed=trades_executed,
            matched_notional=round(matched_notional, 6),
            matched_quantity=round(matched_quantity, 6),
            price_change_bps=price_change_bps,
            mid_price=session.last_price,
        )
        self._append_ohlcv_bar(
            session,
            tick=session.tick,
            open_price=price_before,
            close_price=session.last_price,
            observed_prices=observed_prices,
            volume=matched_quantity,
            trades=trades_executed,
        )
        self._update_game_state_locked(session)

    def _execute_whale_order_locked(
        self,
        session: LiveSessionState,
        *,
        side: OrderSide,
        notional: float,
    ) -> LiveWhaleOrderResponse:
        price_before = session.last_price
        observed_prices = [price_before]
        whale_balance_before = session.whale_ledger.get_balance(WHALE_AGENT_ID)

        if side == OrderSide.BUY:
            if notional > whale_balance_before.cash_free:
                raise ValueError("Whale account has insufficient free cash for this order.")

            session.whale_ledger.reserve_cash(WHALE_AGENT_ID, notional)
            result = execute_market_buy_by_notional(
                session.order_book,
                notional=notional,
                reference_price=price_before,
            )
            session.whale_ledger.apply_buy_fill(
                WHALE_AGENT_ID,
                spent_cash=result.matched_notional,
                received_asset=result.quantity_matched,
            )
            session.whale_ledger.release_cash(
                WHALE_AGENT_ID,
                session.whale_ledger.get_balance(WHALE_AGENT_ID).cash_reserved,
            )
            remaining_side_depth = session.order_book.ask_depth
        else:
            requested_quantity = round(notional / price_before, 6)
            if requested_quantity > whale_balance_before.asset_free:
                raise ValueError("Whale account has insufficient free asset for this order.")

            session.whale_ledger.reserve_asset(WHALE_AGENT_ID, requested_quantity)
            sell_result = execute_market_order(
                session.order_book,
                side=side,
                quantity=requested_quantity,
            )
            result = MatchResult(
                side=sell_result.side,
                requested_notional=round(notional, 6),
                requested_quantity=requested_quantity,
                matched_notional=sell_result.matched_notional,
                trades_executed=sell_result.trades_executed,
                quantity_matched=sell_result.quantity_matched,
                quantity_remaining=sell_result.quantity_remaining,
                average_fill_price=sell_result.average_fill_price,
            )
            session.whale_ledger.apply_sell_fill(
                WHALE_AGENT_ID,
                sold_asset=result.quantity_matched,
                received_cash=result.matched_notional,
            )
            session.whale_ledger.release_asset(
                WHALE_AGENT_ID,
                session.whale_ledger.get_balance(WHALE_AGENT_ID).asset_reserved,
            )
            remaining_side_depth = session.order_book.bid_depth

        price_after = _resolve_post_trade_price(
            session.order_book,
            fallback_price=price_before,
            fill_price=result.average_fill_price,
            side=side,
        )
        absolute_price_change = round(price_after - price_before, 6)
        price_impact_bps = 0.0
        if price_before > 0:
            price_impact_bps = round(
                ((price_after - price_before) / price_before) * 10_000,
                4,
            )
        observed_prices.append(price_after)

        session.tick += 1
        session.last_price = round(price_after, 4)
        session.price_history.append(session.last_price)
        session.updated_at = _utc_now()
        session.structural_bias_bps = max(
            min(session.structural_bias_bps * 0.35 + price_impact_bps * 0.85, MAX_SHOCK_BIAS_BPS),
            -MAX_SHOCK_BIAS_BPS,
        )
        session.cumulative_trades += result.trades_executed
        session.cumulative_matched_notional += result.matched_notional
        session.cumulative_matched_quantity += result.quantity_matched

        whale_order = LiveWhaleOrderOutcome(
            side=side.value,
            tick=session.tick,
            requested_notional=round(notional, 6),
            requested_quantity=result.requested_quantity,
            matched_notional=result.matched_notional,
            matched_quantity=result.quantity_matched,
            quantity_remaining=result.quantity_remaining,
            average_fill_price=result.average_fill_price,
            trades_executed=result.trades_executed,
            price_impact_bps=price_impact_bps,
            mid_price_before=round(price_before, 4),
            mid_price_after=session.last_price,
            absolute_price_change=absolute_price_change,
            remaining_side_depth=round(remaining_side_depth, 4),
            impact_label="BUY IMPACT" if side == OrderSide.BUY else "SELL IMPACT",
        )
        session.last_whale_order = whale_order
        session.last_tick = TickReport(
            tick=session.tick,
            active_agents=1,
            buy_orders=1 if side == OrderSide.BUY else 0,
            sell_orders=1 if side == OrderSide.SELL else 0,
            trades_executed=result.trades_executed,
            matched_notional=result.matched_notional,
            matched_quantity=result.quantity_matched,
            price_change_bps=price_impact_bps,
            mid_price=session.last_price,
        )
        self._append_ohlcv_bar(
            session,
            tick=session.tick,
            open_price=price_before,
            close_price=session.last_price,
            observed_prices=observed_prices,
            volume=result.quantity_matched,
            trades=result.trades_executed,
            whale_side=side,
            whale_impact_bps=price_impact_bps,
        )
        self._record_whale_game_activity_locked(session, whale_order)
        _handle_player_whale_regime_shock_locked(
            session,
            side=side,
            requested_notional=notional,
            remaining_side_depth=remaining_side_depth,
            matched_notional=result.matched_notional,
        )
        self._update_game_state_locked(session)

        whale_balance = self._build_whale_balance_snapshot(session)
        snapshot = self._build_snapshot(session)
        return LiveWhaleOrderResponse(
            snapshot=snapshot,
            whale_order=whale_order,
            whale_balance=whale_balance,
        )

    def _execute_rival_whales_locked(
        self,
        session: LiveSessionState,
        *,
        current_price: float,
    ) -> tuple[int, int, int, int, float, float, list[float], float]:
        mood_bias = _market_mood_bias(session)
        active_whales = 0
        buy_orders = 0
        sell_orders = 0
        trades_executed = 0
        matched_notional = 0.0
        matched_quantity = 0.0
        observed_prices: list[float] = []
        pressure_bps = 0.0

        for whale in session.rival_whales:
            if session.tick - whale.last_action_tick <= whale.cooldown_ticks:
                continue

            activation_threshold = min(
                (0.12 + abs(mood_bias) * 0.24 + whale.aggression * 0.05)
                * session.market_regime.whale_activity_multiplier,
                0.72,
            )
            if session.rng.random() > activation_threshold:
                continue

            side = OrderSide.BUY if session.rng.random() < _market_buy_probability(session, mood_bias) else OrderSide.SELL
            notional_equity = max(abs(whale.total_equity(current_price)), current_price * 120)
            leverage_multiplier = 1 + whale.leverage_limit * (0.45 + abs(mood_bias)) * session.market_regime.volatility_multiplier

            if side == OrderSide.BUY:
                requested_notional = max(
                    450.0,
                    notional_equity * whale.aggression * session.rng.uniform(0.004, 0.012) * leverage_multiplier,
                )
                result = execute_market_buy_by_notional(
                    session.order_book,
                    notional=requested_notional,
                    reference_price=current_price,
                )
                whale.cash -= result.matched_notional
                whale.asset += result.quantity_matched
                buy_orders += 1
            else:
                requested_quantity = max(
                    2.0,
                    (notional_equity / max(current_price, 1e-9))
                    * whale.aggression
                    * session.rng.uniform(0.004, 0.012)
                    * leverage_multiplier,
                )
                result = execute_market_order(
                    session.order_book,
                    side=side,
                    quantity=requested_quantity,
                )
                whale.cash += result.matched_notional
                whale.asset -= result.quantity_matched
                sell_orders += 1

            whale.last_action_tick = session.tick
            active_whales += 1
            trades_executed += result.trades_executed
            matched_notional += result.matched_notional
            matched_quantity += result.quantity_matched
            observed_prices.append(session.order_book.mid_price or result.average_fill_price or current_price)

            direction_sign = 1 if side == OrderSide.BUY else -1
            pressure_bps += direction_sign * min(result.matched_notional / 12_500, 8.5) * (0.8 + abs(mood_bias))

        return (
            active_whales,
            buy_orders,
            sell_orders,
            trades_executed,
            matched_notional,
            matched_quantity,
            observed_prices,
            pressure_bps,
        )

    def _roll_whale_mood_locked(self, session: LiveSessionState) -> None:
        if session.tick >= session.whale_mood.next_ten_minute_roll_tick:
            session.whale_mood.ten_minute_score = session.rng.randint(0, 100)
            session.whale_mood.next_ten_minute_roll_tick += TEN_MINUTE_SENTIMENT_INTERVAL_TICKS

        if session.tick >= session.whale_mood.next_minute_roll_tick:
            session.whale_mood.minute_score = session.rng.randint(0, 100)
            session.whale_mood.next_minute_roll_tick += ONE_MINUTE_SENTIMENT_INTERVAL_TICKS

    def _apply_cash_growth_locked(self, session: LiveSessionState) -> None:
        if session.tick < session.next_cash_growth_tick:
            return

        while session.tick >= session.next_cash_growth_tick:
            session.ledger.scale_cash(MONEY_GROWTH_MULTIPLIER)
            for whale in session.rival_whales:
                whale.cash *= MONEY_GROWTH_MULTIPLIER

            session.next_cash_growth_tick += MONEY_GROWTH_INTERVAL_TICKS

    def _execute_profile_action(
        self,
        session: LiveSessionState,
        profile: AgentProfile,
        runtime: AgentRuntimeState,
        *,
        current_price: float,
        anchor_price: float,
    ) -> AgentActionResult | None:
        runtime.fair_value_estimate = round(
            runtime.fair_value_estimate * 0.995
            + current_price * 0.005
            + session.rng.uniform(-0.03, 0.03),
            4,
        )

        side = _decide_side(
            session,
            profile,
            runtime,
            current_price=current_price,
            anchor_price=anchor_price,
        )
        if side is None:
            return None

        balance = session.ledger.get_balance(profile.agent_id)
        use_market_order = _should_use_market_order(session, profile, runtime)
        if side == OrderSide.BUY:
            notional = _buy_notional(session, profile, runtime, cash_free=balance.cash_free)
            if notional <= 1e-9:
                return None

            if not use_market_order:
                limit_price = _build_limit_price(
                    side=side,
                    current_price=current_price,
                    best_bid=session.order_book.best_bid,
                    best_ask=session.order_book.best_ask,
                    strategy=profile.strategy,
                    rng=session.rng,
                )
                session.order_book.add_limit_order(
                    side=side,
                    price=limit_price,
                    quantity=max(notional / max(current_price, 1e-9), 0.0001),
                    agent_id=profile.agent_id,
                    strategy_type=profile.strategy.value,
                    created_tick=session.tick,
                    ttl_ticks=_ttl_for_strategy(profile.strategy, session.rng),
                )
                return AgentActionResult(side=side, placed_limit=True)

            session.ledger.reserve_cash(profile.agent_id, notional)
            result = execute_market_buy_by_notional(
                session.order_book,
                notional=notional,
                reference_price=current_price,
            )
            session.ledger.apply_buy_fill(
                profile.agent_id,
                spent_cash=result.matched_notional,
                received_asset=result.quantity_matched,
            )
            session.ledger.release_cash(
                profile.agent_id,
                session.ledger.get_balance(profile.agent_id).cash_reserved,
            )
            return AgentActionResult(side=side, match_result=result) if result.trades_executed > 0 else None

        quantity = _sell_quantity(session, profile, runtime, asset_free=balance.asset_free)
        if quantity <= 1e-9:
            return None

        if not use_market_order:
            limit_price = _build_limit_price(
                side=side,
                current_price=current_price,
                best_bid=session.order_book.best_bid,
                best_ask=session.order_book.best_ask,
                strategy=profile.strategy,
                rng=session.rng,
            )
            session.order_book.add_limit_order(
                side=side,
                price=limit_price,
                quantity=quantity,
                agent_id=profile.agent_id,
                strategy_type=profile.strategy.value,
                created_tick=session.tick,
                ttl_ticks=_ttl_for_strategy(profile.strategy, session.rng),
            )
            return AgentActionResult(side=side, placed_limit=True)

        session.ledger.reserve_asset(profile.agent_id, quantity)
        result = execute_market_order(
            session.order_book,
            side=side,
            quantity=quantity,
        )
        session.ledger.apply_sell_fill(
            profile.agent_id,
            sold_asset=result.quantity_matched,
            received_cash=result.matched_notional,
        )
        session.ledger.release_asset(
            profile.agent_id,
            session.ledger.get_balance(profile.agent_id).asset_reserved,
        )
        return AgentActionResult(side=side, match_result=result) if result.trades_executed > 0 else None

    def _build_snapshot(self, session: LiveSessionState) -> LiveSimulationSnapshot:
        fallback_price = session.last_price
        return LiveSimulationSnapshot(
            session_id=session.session_id,
            status="running" if session.running else "stopped",
            tick=session.tick,
            tick_interval_ms=session.tick_interval_ms,
            simulated_tick_interval_ms=SIMULATED_TICK_INTERVAL_MS,
            created_at=session.created_at,
            updated_at=session.updated_at,
            config=session.config,
            agent_mix=[
                AgentMixEntry(strategy=strategy, count=count)
                for strategy, count in summarize_agent_mix(session.profiles).items()
            ],
            order_book=session.engine.build_order_book_snapshot(
                session.order_book,
                fallback_price=fallback_price,
            ),
            metrics=session.engine.build_metrics(
                session.ledger,
                session.order_book,
                session.active_backend,
                fallback_price=fallback_price,
            ),
            recent_mid_prices=list(session.price_history),
            ohlcv_history=list(session.ohlcv_history),
            last_tick=session.last_tick,
            market_regime=self._build_market_regime_snapshot(session.market_regime),
            whale_balance=self._build_whale_balance_snapshot(session),
            last_whale_order=session.last_whale_order,
            top_agents=self._build_top_agents(session),
            game=self._build_game_snapshot(session),
            notes=[
                "Live session runs in memory and advances by tick while the app process stays open.",
                "Agents currently send small market intents against replenished synthetic liquidity.",
                "Whale orders act on the live order book and leave a visible multi-tick price bias.",
            ],
        )

    def _build_whale_balance_snapshot(
        self,
        session: LiveSessionState,
    ) -> WhaleBalanceSnapshot:
        whale_balance = session.whale_ledger.get_balance(WHALE_AGENT_ID)
        return WhaleBalanceSnapshot(
            cash_free=round(whale_balance.cash_free, 6),
            cash_reserved=round(whale_balance.cash_reserved, 6),
            asset_free=round(whale_balance.asset_free, 6),
            asset_reserved=round(whale_balance.asset_reserved, 6),
            initial_cash=round(session.whale_initial_cash, 6),
            initial_asset=round(session.whale_initial_asset, 6),
            initial_mark_price=round(session.whale_initial_mark_price, 6),
            initial_total_equity=round(session.whale_initial_total_equity, 6),
            total_equity=round(whale_balance.total_equity(session.last_price), 6),
        )

    def _build_market_regime_snapshot(self, regime: RegimeRuntimeState) -> MarketRegimeState:
        return MarketRegimeState(
            name=regime.name,
            ticks_remaining=regime.ticks_remaining,
            buy_bias=regime.buy_bias,
            sell_bias=regime.sell_bias,
            volatility_multiplier=regime.volatility_multiplier,
            liquidity_multiplier=regime.liquidity_multiplier,
            spread_multiplier=regime.spread_multiplier,
            whale_activity_multiplier=regime.whale_activity_multiplier,
            momentum_multiplier=regime.momentum_multiplier,
            mean_reversion_multiplier=regime.mean_reversion_multiplier,
            maker_cancel_multiplier=regime.maker_cancel_multiplier,
            gap_probability=regime.gap_probability,
            reason=regime.reason,
        )

    def _advance_market_regime_locked(self, session: LiveSessionState) -> None:
        session.market_regime.ticks_remaining = max(session.market_regime.ticks_remaining - 1, 0)
        if session.market_regime.ticks_remaining > 0:
            return

        next_regime = _pick_next_market_regime(session.market_regime.name, session.rng)
        session.market_regime = _build_market_regime(next_regime, rng=session.rng, reason="timer_transition")

    def _append_ohlcv_bar(
        self,
        session: LiveSessionState,
        *,
        tick: int,
        open_price: float,
        close_price: float,
        observed_prices: list[float],
        volume: float,
        trades: int,
        whale_side: OrderSide | None = None,
        whale_impact_bps: float | None = None,
    ) -> None:
        candle_prices = [
            round(price, 4)
            for price in [open_price, *observed_prices, close_price]
            if price > 0
        ]
        if not candle_prices:
            candle_prices = [round(close_price, 4)]

        session.ohlcv_history.append(
            OhlcvBar(
                tick=tick,
                open=round(open_price, 4),
                high=max(candle_prices),
                low=min(candle_prices),
                close=round(close_price, 4),
                volume=round(volume, 6),
                trades=trades,
                whale_side=whale_side.value if whale_side is not None else None,
                whale_impact_bps=whale_impact_bps,
            )
        )

    def _build_top_agents(self, session: LiveSessionState) -> list[TopAgentEntry]:
        ranked_profiles = sorted(
            session.profiles,
            key=lambda profile: session.ledger.get_balance(profile.agent_id).total_equity(session.last_price),
            reverse=True,
        )[:10]

        return [
            TopAgentEntry(
                agent_id=profile.agent_id,
                alias=_build_agent_alias(profile.agent_id),
                strategy=profile.strategy.value,
                equity=round(
                    session.ledger.get_balance(profile.agent_id).total_equity(session.last_price),
                    2,
                ),
            )
            for profile in ranked_profiles
        ]

    def _reset_whale_baseline_locked(self, session: LiveSessionState) -> None:
        current_agent_equity = session.ledger.total_equity(session.last_price)
        whale_initial_cash, whale_initial_asset = _build_whale_initial_portfolio(
            session.config,
            reference_price=session.last_price,
            total_agent_equity=current_agent_equity,
        )
        session.whale_initial_cash = whale_initial_cash
        session.whale_initial_asset = whale_initial_asset
        session.whale_initial_mark_price = session.last_price
        session.whale_initial_total_equity = round(
            whale_initial_cash + whale_initial_asset * session.last_price,
            6,
        )
        session.rival_whales = _build_rival_whales(
            total_agent_equity=current_agent_equity,
            reference_price=session.last_price,
            rng=session.rng,
        )
        session.whale_mood = _build_whale_mood_state(session.rng, current_tick=session.tick)
        session.next_cash_growth_tick = session.tick + MONEY_GROWTH_INTERVAL_TICKS
        session.whale_ledger = Ledger(
            {
                WHALE_AGENT_ID: AgentBalance(
                    cash_free=whale_initial_cash,
                    cash_reserved=0.0,
                    asset_free=whale_initial_asset,
                    asset_reserved=0.0,
                )
            }
        )

    def _build_game_snapshot(self, session: LiveSessionState) -> LiveGameState:
        return LiveGameState(
            mode=session.game.mode,
            status=session.game.status,
            started_at_tick=session.game.started_at_tick,
            duration_ticks=session.game.duration_ticks,
            remaining_ticks=session.game.remaining_ticks,
            score=round(session.game.score, 6),
            score_breakdown=GameScoreBreakdown(**session.game.score_breakdown),
            final_result=session.game.final_result,
        )

    def _update_game_state_locked(self, session: LiveSessionState) -> None:
        if session.game.status != "running" or session.game.started_at_tick is None:
            return

        elapsed_ticks = max(session.tick - session.game.started_at_tick, 0)
        session.game.remaining_ticks = max(session.game.duration_ticks - elapsed_ticks, 0)
        self._refresh_game_score_locked(session)
        if session.game.remaining_ticks == 0:
            self._end_game_locked(session)

    def _record_whale_game_activity_locked(
        self,
        session: LiveSessionState,
        whale_order: LiveWhaleOrderOutcome,
    ) -> None:
        if session.game.status != "running":
            return

        session.game.total_whale_impact_bps = round(
            session.game.total_whale_impact_bps + abs(whale_order.price_impact_bps),
            6,
        )
        session.game.max_whale_impact_bps = round(
            max(session.game.max_whale_impact_bps, abs(whale_order.price_impact_bps)),
            6,
        )
        session.game.total_whale_volume = round(
            session.game.total_whale_volume + whale_order.matched_notional,
            6,
        )
        session.game.whale_orders += 1

    def _refresh_game_score_locked(self, session: LiveSessionState) -> None:
        pnl_executed = _calculate_executed_pnl(session)
        session.game.score_breakdown = {
            "pnl_score": round(pnl_executed, 6),
            "impact_score": round(session.game.total_whale_impact_bps * 10, 6),
            "volume_score": round(session.game.total_whale_volume * 0.01, 6),
        }
        session.game.score = round(sum(session.game.score_breakdown.values()), 6)

    def _end_game_locked(self, session: LiveSessionState) -> None:
        if session.game.status == "idle":
            return
        if session.game.status == "ended":
            return

        self._refresh_game_score_locked(session)
        starting_price = session.game.starting_price or session.config.initial_price
        session.game.final_result = GameFinalResult(
            score=round(session.game.score, 6),
            pnl_executed=round(_calculate_executed_pnl(session), 6),
            max_impact_bps=round(session.game.max_whale_impact_bps, 6),
            total_volume=round(session.game.total_whale_volume, 6),
            whale_orders=session.game.whale_orders,
            ending_price=round(session.last_price, 4),
            starting_price=round(starting_price, 4),
        )
        session.game.status = "ended"
        session.updated_at = _utc_now()


def _cooldown_for(strategy: StrategyType) -> int:
    if strategy == StrategyType.NOISE:
        return 0
    if strategy == StrategyType.MOMENTUM:
        return 1
    if strategy in {StrategyType.MEAN_REVERSION, StrategyType.VALUE}:
        return 2
    if strategy == StrategyType.MARKET_MAKER:
        return 2
    if strategy == StrategyType.DIRECTIONAL_FUND:
        return 3
    if strategy == StrategyType.AGGRESSIVE_WHALE:
        return 8
    return 3


def _ttl_for_strategy(strategy: StrategyType, rng: Random) -> int:
    if strategy == StrategyType.NOISE:
        return rng.randint(2, 5)
    if strategy in {StrategyType.MOMENTUM, StrategyType.DIRECTIONAL_FUND}:
        return rng.randint(4, 10)
    if strategy in {StrategyType.MEAN_REVERSION, StrategyType.VALUE}:
        return rng.randint(8, 18)
    if strategy == StrategyType.MARKET_MAKER:
        return rng.randint(5, 9)
    if strategy == StrategyType.AGGRESSIVE_WHALE:
        return rng.randint(2, 4)
    return rng.randint(4, 8)


def _build_initial_market_regime(*, preload_pattern: str, rng: Random) -> RegimeRuntimeState:
    mapping = {
        "bullish": "accumulation",
        "bearish": "distribution",
        "lateral": "neutral",
        "mixed": "neutral",
    }
    return _build_market_regime(mapping.get(preload_pattern, "neutral"), rng=rng, reason="initial_seed")


def _build_market_regime(name: str, *, rng: Random, reason: str | None) -> RegimeRuntimeState:
    params = REGIME_PARAMS[name]
    duration_min, duration_max = params["duration"]
    return RegimeRuntimeState(
        name=name,
        ticks_remaining=rng.randint(duration_min, duration_max),
        buy_bias=params["buy_bias"],
        sell_bias=params["sell_bias"],
        volatility_multiplier=params["volatility_multiplier"],
        liquidity_multiplier=params["liquidity_multiplier"],
        spread_multiplier=params["spread_multiplier"],
        whale_activity_multiplier=params["whale_activity_multiplier"],
        momentum_multiplier=params["momentum_multiplier"],
        mean_reversion_multiplier=params["mean_reversion_multiplier"],
        maker_cancel_multiplier=params["maker_cancel_multiplier"],
        gap_probability=params["gap_probability"],
        reason=reason,
    )


def _pick_next_market_regime(current_name: str, rng: Random) -> str:
    transitions = {
        "neutral": ["accumulation", "distribution", "neutral", "uptrend", "downtrend"],
        "accumulation": ["uptrend", "neutral", "distribution"],
        "uptrend": ["uptrend", "distribution", "neutral"],
        "distribution": ["downtrend", "neutral", "accumulation"],
        "downtrend": ["downtrend", "accumulation", "neutral"],
        "panic": ["post_whale_consolidation", "neutral", "accumulation"],
        "short_squeeze": ["post_whale_consolidation", "distribution", "neutral"],
        "post_whale_consolidation": ["neutral", "accumulation", "distribution"],
    }
    return rng.choice(transitions.get(current_name, ["neutral"]))


def _decide_side(
    session: LiveSessionState,
    profile: AgentProfile,
    runtime: AgentRuntimeState,
    *,
    current_price: float,
    anchor_price: float,
) -> OrderSide | None:
    rng = session.rng
    price_bias = 0.0
    if anchor_price > 0:
        price_bias = (current_price - anchor_price) / anchor_price

    fair_value_gap = 0.0
    if runtime.fair_value_estimate > 0:
        fair_value_gap = (current_price - runtime.fair_value_estimate) / runtime.fair_value_estimate

    if runtime.intent_ticks_remaining > 0 and runtime.intent_side != 0:
        runtime.intent_ticks_remaining = max(runtime.intent_ticks_remaining - 1, 0)
        return OrderSide.BUY if runtime.intent_side > 0 else OrderSide.SELL

    strategy = profile.strategy
    if strategy == StrategyType.NOISE:
        return OrderSide.BUY if rng.random() < session.market_regime.buy_bias else OrderSide.SELL

    if strategy == StrategyType.MOMENTUM:
        if price_bias > 0.0006:
            runtime.intent_side = 1
            runtime.intent_ticks_remaining = rng.randint(5, 12)
            return OrderSide.BUY
        if price_bias < -0.0006:
            runtime.intent_side = -1
            runtime.intent_ticks_remaining = rng.randint(5, 12)
            return OrderSide.SELL
        regime_buy = min(max(session.market_regime.buy_bias + 0.06, 0.08), 0.92)
        return OrderSide.BUY if rng.random() < regime_buy else OrderSide.SELL

    if strategy in {StrategyType.MEAN_REVERSION, StrategyType.VALUE}:
        if price_bias > 0.0010 or fair_value_gap > 0.0013:
            runtime.intent_side = -1
            runtime.intent_ticks_remaining = rng.randint(6, 14)
            return OrderSide.SELL
        if price_bias < -0.0010 or fair_value_gap < -0.0013:
            runtime.intent_side = 1
            runtime.intent_ticks_remaining = rng.randint(6, 14)
            return OrderSide.BUY
        return None

    if strategy == StrategyType.MARKET_MAKER:
        if abs(price_bias) < 0.0006:
            return None
        return OrderSide.SELL if price_bias > 0 else OrderSide.BUY

    if strategy == StrategyType.DIRECTIONAL_FUND:
        if runtime.directional_ticks_remaining <= 0:
            runtime.directional_ticks_remaining = rng.randint(20, 45)
            if abs(price_bias) > 0.0004:
                runtime.directional_side = 1 if price_bias > 0 else -1
            else:
                runtime.directional_side = 1 if rng.random() < session.market_regime.buy_bias else -1

        runtime.directional_ticks_remaining = max(runtime.directional_ticks_remaining - 1, 0)
        runtime.intent_side = runtime.directional_side
        runtime.intent_ticks_remaining = max(runtime.directional_ticks_remaining, 1)
        return OrderSide.BUY if runtime.directional_side >= 0 else OrderSide.SELL

    if strategy == StrategyType.AGGRESSIVE_WHALE:
        bullish_threshold = 0.44 + max(price_bias, 0) * 120
        runtime.intent_side = 1 if bullish_threshold >= 0.5 else -1
        runtime.intent_ticks_remaining = rng.randint(2, 6)
        return OrderSide.BUY if rng.random() < bullish_threshold else OrderSide.SELL

    if fair_value_gap > 0.0015:
        return OrderSide.SELL
    if fair_value_gap < -0.0015:
        return OrderSide.BUY
    return OrderSide.BUY if rng.random() < 0.5 else OrderSide.SELL


def _buy_notional(
    session: LiveSessionState,
    profile: AgentProfile,
    runtime: AgentRuntimeState,
    *,
    cash_free: float,
) -> float:
    if cash_free <= 1e-9:
        return 0.0

    base_ratio = {
        StrategyType.NOISE: 0.0007,
        StrategyType.MOMENTUM: 0.0016,
        StrategyType.MEAN_REVERSION: 0.0009,
        StrategyType.VALUE: 0.0010,
        StrategyType.MARKET_MAKER: 0.0005,
        StrategyType.DIRECTIONAL_FUND: 0.0034,
        StrategyType.AGGRESSIVE_WHALE: 0.0055,
        StrategyType.FUNDAMENTAL: 0.0010,
    }[profile.strategy]
    ratio = base_ratio * runtime.aggression_level * session.rng.uniform(0.75, 1.25)
    ratio *= runtime.risk_appetite
    if profile.strategy in {StrategyType.MOMENTUM, StrategyType.DIRECTIONAL_FUND, StrategyType.AGGRESSIVE_WHALE}:
        ratio *= session.market_regime.momentum_multiplier
    if profile.strategy in {StrategyType.MEAN_REVERSION, StrategyType.VALUE}:
        ratio *= session.market_regime.mean_reversion_multiplier
    ratio *= session.market_regime.volatility_multiplier
    return round(max(0.0, cash_free * ratio), 6)


def _sell_quantity(
    session: LiveSessionState,
    profile: AgentProfile,
    runtime: AgentRuntimeState,
    *,
    asset_free: float,
) -> float:
    if asset_free <= 1e-9:
        return 0.0

    base_ratio = {
        StrategyType.NOISE: 0.08,
        StrategyType.MOMENTUM: 0.12,
        StrategyType.MEAN_REVERSION: 0.09,
        StrategyType.VALUE: 0.08,
        StrategyType.MARKET_MAKER: 0.05,
        StrategyType.DIRECTIONAL_FUND: 0.14,
        StrategyType.AGGRESSIVE_WHALE: 0.18,
        StrategyType.FUNDAMENTAL: 0.10,
    }[profile.strategy]
    ratio = base_ratio * runtime.aggression_level * session.rng.uniform(0.7, 1.2)
    ratio *= runtime.risk_appetite
    if profile.strategy in {StrategyType.MOMENTUM, StrategyType.DIRECTIONAL_FUND, StrategyType.AGGRESSIVE_WHALE}:
        ratio *= session.market_regime.momentum_multiplier
    if profile.strategy in {StrategyType.MEAN_REVERSION, StrategyType.VALUE}:
        ratio *= session.market_regime.mean_reversion_multiplier
    ratio *= session.market_regime.volatility_multiplier
    return round(max(0.0, asset_free * min(ratio, 0.35)), 6)


def _should_use_market_order(
    session: LiveSessionState,
    profile: AgentProfile,
    runtime: AgentRuntimeState,
) -> bool:
    mood_bias = abs(_market_mood_bias(session))
    if profile.strategy == StrategyType.NOISE:
        return session.rng.random() < 0.18
    if profile.strategy == StrategyType.MOMENTUM:
        return session.rng.random() < min((0.30 + mood_bias * 0.18) * session.market_regime.momentum_multiplier, 0.92)
    if profile.strategy in {StrategyType.MEAN_REVERSION, StrategyType.VALUE}:
        return session.rng.random() < 0.12
    if profile.strategy == StrategyType.MARKET_MAKER:
        return False
    if profile.strategy == StrategyType.DIRECTIONAL_FUND:
        return session.rng.random() < min((0.42 + mood_bias * 0.22) * session.market_regime.momentum_multiplier, 0.96)
    if profile.strategy == StrategyType.AGGRESSIVE_WHALE:
        return True
    return session.rng.random() < 0.2


def _build_limit_price(
    *,
    side: OrderSide,
    current_price: float,
    best_bid: float | None,
    best_ask: float | None,
    strategy: StrategyType,
    rng: Random,
) -> float:
    spread_anchor = max((best_ask or current_price) - (best_bid or current_price), 0.02)

    if strategy == StrategyType.MARKET_MAKER:
        offset = spread_anchor * rng.uniform(0.4, 1.2)
    elif strategy in {StrategyType.MEAN_REVERSION, StrategyType.VALUE}:
        offset = spread_anchor * rng.uniform(1.2, 2.6)
    elif strategy == StrategyType.NOISE:
        offset = spread_anchor * rng.uniform(0.8, 1.8)
    else:
        offset = spread_anchor * rng.uniform(0.25, 1.0)

    price = current_price - offset if side == OrderSide.BUY else current_price + offset
    return round(max(price, 0.01), 2)


def _resolve_post_trade_price(
    order_book: OrderBook,
    *,
    fallback_price: float,
    fill_price: float,
    side: OrderSide,
) -> float:
    if order_book.mid_price is not None:
        return round(order_book.mid_price, 4)

    if side == OrderSide.BUY and order_book.best_bid is not None:
        return round(max(order_book.best_bid, fill_price or fallback_price), 4)

    if side == OrderSide.SELL and order_book.best_ask is not None:
        return round(min(order_book.best_ask, fill_price or fallback_price), 4)

    if fill_price > 0:
        return round(fill_price, 4)

    return round(fallback_price, 4)


def _choose_preload_pattern(rng: Random) -> str:
    return rng.choice(["bullish", "bearish", "lateral", "mixed"])


def _build_agent_alias(agent_id: int) -> str:
    prefixes = [
        "Atlas",
        "Nova",
        "Vector",
        "Apex",
        "Helix",
        "Falcon",
        "Orion",
        "Titan",
        "Meridian",
        "Pulse",
    ]
    suffixes = [
        "Capital",
        "Flow",
        "Dynamics",
        "Partners",
        "Desk",
        "Signal",
        "Liquidity",
        "Point",
        "Labs",
        "Holdings",
    ]

    return f"{prefixes[agent_id % len(prefixes)]} {suffixes[(agent_id * 3) % len(suffixes)]}"


def _preload_pattern_bias_bps(session: LiveSessionState) -> float:
    if session.tick > session.preloaded_ticks_total:
        return 0.0

    progress = session.tick / max(session.preloaded_ticks_total, 1)
    oscillation = sin(progress * pi * 6)

    if session.preload_pattern == "bullish":
        return 0.95 + oscillation * 0.55

    if session.preload_pattern == "bearish":
        return -0.95 + oscillation * 0.55

    if session.preload_pattern == "lateral":
        return oscillation * 1.15

    if progress < 0.25:
        return 0.85 + oscillation * 0.45
    if progress < 0.5:
        return oscillation * 0.95
    if progress < 0.75:
        return -1.05 + oscillation * 0.5
    return 0.65 + oscillation * 0.65


def _build_whale_initial_portfolio(
    config: SessionConfig,
    *,
    reference_price: float,
    total_agent_equity: float | None = None,
) -> tuple[float, float]:
    total_agent_equity = total_agent_equity or config.agent_count * (
        config.initial_cash + config.initial_asset * config.initial_price
    )
    whale_initial_equity = total_agent_equity * (
        WHALE_TARGET_CAPITAL_SHARE / (1 - WHALE_TARGET_CAPITAL_SHARE)
    )
    whale_initial_cash = whale_initial_equity * WHALE_CASH_WEIGHT
    whale_initial_asset = (whale_initial_equity - whale_initial_cash) / max(reference_price, 1e-9)

    return round(whale_initial_cash, 6), round(whale_initial_asset, 6)


def _empty_game_score_breakdown() -> dict[str, float]:
    return {
        "pnl_score": 0.0,
        "impact_score": 0.0,
        "volume_score": 0.0,
    }


def _calculate_executed_pnl(session: LiveSessionState) -> float:
    whale_balance = session.whale_ledger.get_balance(WHALE_AGENT_ID)
    cash_total = whale_balance.cash_free + whale_balance.cash_reserved
    asset_total = whale_balance.asset_free + whale_balance.asset_reserved
    initial_equity = session.whale_initial_total_equity

    return cash_total + asset_total * session.whale_initial_mark_price - initial_equity


def _build_rival_whales(
    *,
    total_agent_equity: float,
    reference_price: float,
    rng: Random,
) -> list[RivalWhaleState]:
    rival_equity = total_agent_equity * RIVAL_WHALE_SHARE_PER_WHALE
    rival_cash = rival_equity * RIVAL_WHALE_CASH_WEIGHT
    rival_asset = (rival_equity - rival_cash) / max(reference_price, 1e-9)

    return [
        RivalWhaleState(
            whale_id=index + 1,
            alias=_build_agent_alias(10_000 + index),
            cash=round(rival_cash, 6),
            asset=round(rival_asset, 6),
            leverage_limit=round(rng.uniform(RIVAL_WHALE_LEVERAGE_MIN, RIVAL_WHALE_LEVERAGE_MAX), 3),
            aggression=round(rng.uniform(1.1, 1.8), 3),
            cooldown_ticks=rng.randint(2, 6),
        )
        for index in range(RIVAL_WHALE_COUNT)
    ]


def _build_whale_mood_state(rng: Random, *, current_tick: int) -> WhaleMoodState:
    return WhaleMoodState(
        session_score=rng.randint(0, 100),
        ten_minute_score=rng.randint(0, 100),
        minute_score=rng.randint(0, 100),
        next_ten_minute_roll_tick=current_tick + TEN_MINUTE_SENTIMENT_INTERVAL_TICKS,
        next_minute_roll_tick=current_tick + ONE_MINUTE_SENTIMENT_INTERVAL_TICKS,
    )


def _market_mood_bias(session: LiveSessionState) -> float:
    average_score = (
        session.whale_mood.session_score
        + session.whale_mood.ten_minute_score
        + session.whale_mood.minute_score
    ) / 3

    return (average_score - 50) / 50


def _market_mood_bias_bps(session: LiveSessionState) -> float:
    return round(_market_mood_bias(session) * 6.5, 4)


def _market_buy_probability(session: LiveSessionState, mood_bias: float) -> float:
    probability = session.market_regime.buy_bias + mood_bias * 0.18 + session.rng.uniform(-0.08, 0.08)
    return max(min(probability, 0.94), 0.06)


def _market_regime_drift_bps(session: LiveSessionState) -> float:
    return round((session.market_regime.buy_bias - session.market_regime.sell_bias) * 7.5, 4)


def _handle_market_regime_reaction_locked(
    session: LiveSessionState,
    *,
    price_change_bps: float,
    trades_executed: int,
) -> None:
    if price_change_bps <= PANIC_PRICE_CHANGE_BPS:
        session.market_regime = _build_market_regime("panic", rng=session.rng, reason="support_break_panic")
        return

    if price_change_bps >= SHORT_SQUEEZE_PRICE_CHANGE_BPS:
        session.market_regime = _build_market_regime("short_squeeze", rng=session.rng, reason="resistance_break_squeeze")
        return

    if trades_executed >= 40 and abs(price_change_bps) >= 45:
        next_regime = "uptrend" if price_change_bps > 0 else "downtrend"
        session.market_regime = _build_market_regime(next_regime, rng=session.rng, reason="breakout_volume")


def _handle_player_whale_regime_shock_locked(
    session: LiveSessionState,
    *,
    side: OrderSide,
    requested_notional: float,
    remaining_side_depth: float,
    matched_notional: float,
) -> None:
    consumed_visible_liquidity = False
    pre_shock_depth = max(remaining_side_depth + matched_notional / max(session.last_price, 1e-9), 1e-9)
    if pre_shock_depth > 0:
        consumed_visible_liquidity = (matched_notional / max(session.last_price, 1e-9)) >= pre_shock_depth * 0.05

    if requested_notional < WHALE_SHOCK_THRESHOLD_USD and not consumed_visible_liquidity:
        return

    reason = "whale_buy_shock" if side == OrderSide.BUY else "whale_sell_shock"
    session.market_regime = _build_market_regime("post_whale_consolidation", rng=session.rng, reason=reason)


def _preloaded_tick_count() -> int:
    return max((PRELOADED_WINDOW_MS + SIMULATED_TICK_INTERVAL_MS - 1) // SIMULATED_TICK_INTERVAL_MS, 1)


def _history_size_for() -> int:
    return max(_preloaded_tick_count() + PRELOADED_HISTORY_MARGIN, MAX_OHLCV_HISTORY)


def _decay_bias(value: float) -> float:
    decayed = value * SHOCK_BIAS_DECAY
    if abs(decayed) < 0.35:
        return 0.0
    return round(decayed, 4)


def _base_liquidity_for_bias(structural_bias_bps: float) -> float:
    if abs(structural_bias_bps) >= 25:
        return 20.0
    if abs(structural_bias_bps) >= 10:
        return 24.0
    return 28.0


_live_simulation_service = LiveSimulationService()


def get_live_simulation_service() -> LiveSimulationService:
    return _live_simulation_service