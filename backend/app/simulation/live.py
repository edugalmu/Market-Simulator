from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
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
    LiveSimulationSnapshot,
    LiveWhaleOrderOutcome,
    LiveWhaleOrderResponse,
    OhlcvBar,
    SessionConfig,
    TickReport,
    WhaleBalanceSnapshot,
)
from app.simulation.scheduler import select_active_agent_count


DEFAULT_TICK_INTERVAL_MS = 750
MAX_PRICE_HISTORY = 24
MAX_OHLCV_HISTORY = 80
PRELOADED_WINDOW_MS = 10 * 60 * 1000
PRELOADED_HISTORY_MARGIN = 12
WHALE_AGENT_ID = 0
WHALE_INITIAL_CASH = 250_000.0
WHALE_INITIAL_ASSET = 5_000.0
SHOCK_BIAS_DECAY = 0.72
MAX_SHOCK_BIAS_BPS = 85.0


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@dataclass(slots=True)
class AgentRuntimeState:
    fair_value_estimate: float
    aggression_level: float
    cooldown_ticks: int
    last_action_tick: int = -10_000


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
        whale_ledger = Ledger(
            {
                WHALE_AGENT_ID: AgentBalance(
                    cash_free=WHALE_INITIAL_CASH,
                    cash_reserved=0.0,
                    asset_free=WHALE_INITIAL_ASSET,
                    asset_reserved=0.0,
                )
            }
        )
        history_size = _history_size_for(tick_interval_ms)
        preloaded_tick_count = _preloaded_tick_count(tick_interval_ms)

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
                )
                for profile in profiles
            },
        )

        with self._lock:
            self._stop_event = Event()
            self._session = session
            for _ in range(preloaded_tick_count):
                self._advance_session_locked(session)

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

            trades_executed += result.trades_executed
            matched_notional += result.matched_notional
            matched_quantity += result.quantity_matched
            if result.average_fill_price > 0:
                observed_prices.append(result.average_fill_price)

        flow_imbalance = buy_orders - sell_orders
        drift_bps = max(
            min(
                flow_imbalance * 1.35
                + session.structural_bias_bps
                + session.rng.uniform(-0.8, 0.8),
                16.0,
            ),
            -14.0,
        )
        reference_price = max(price_before * (1 + drift_bps / 10_000), 1.0)
        session.order_book.seed_around(
            reference_price,
            base_quantity=_base_liquidity_for_bias(session.structural_bias_bps),
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
        if result.average_fill_price > 0:
            observed_prices.append(result.average_fill_price)
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

        whale_balance = self._build_whale_balance_snapshot(session)
        snapshot = self._build_snapshot(session)
        return LiveWhaleOrderResponse(
            snapshot=snapshot,
            whale_order=whale_order,
            whale_balance=whale_balance,
        )

    def _execute_profile_action(
        self,
        session: LiveSessionState,
        profile: AgentProfile,
        runtime: AgentRuntimeState,
        *,
        current_price: float,
        anchor_price: float,
    ) -> MatchResult | None:
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
        if side == OrderSide.BUY:
            notional = _buy_notional(session, profile, runtime, cash_free=balance.cash_free)
            if notional <= 1e-9:
                return None

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
            return result if result.trades_executed > 0 else None

        quantity = _sell_quantity(session, profile, runtime, asset_free=balance.asset_free)
        if quantity <= 1e-9:
            return None

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
        return result if result.trades_executed > 0 else None

    def _build_snapshot(self, session: LiveSessionState) -> LiveSimulationSnapshot:
        fallback_price = session.last_price
        return LiveSimulationSnapshot(
            session_id=session.session_id,
            status="running" if session.running else "stopped",
            tick=session.tick,
            tick_interval_ms=session.tick_interval_ms,
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
            whale_balance=self._build_whale_balance_snapshot(session),
            last_whale_order=session.last_whale_order,
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
            total_equity=round(whale_balance.total_equity(session.last_price), 6),
        )

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


def _cooldown_for(strategy: StrategyType) -> int:
    if strategy == StrategyType.NOISE:
        return 0
    if strategy in {StrategyType.MOMENTUM, StrategyType.MEAN_REVERSION}:
        return 1
    if strategy == StrategyType.MARKET_MAKER:
        return 2
    return 3


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

    strategy = profile.strategy
    if strategy == StrategyType.NOISE:
        return OrderSide.BUY if rng.random() < 0.5 else OrderSide.SELL

    if strategy == StrategyType.MOMENTUM:
        if price_bias > 0.0008:
            return OrderSide.BUY
        if price_bias < -0.0008:
            return OrderSide.SELL
        return OrderSide.BUY if rng.random() < 0.52 else OrderSide.SELL

    if strategy == StrategyType.MEAN_REVERSION:
        if price_bias > 0.0012:
            return OrderSide.SELL
        if price_bias < -0.0012:
            return OrderSide.BUY
        return None

    if strategy == StrategyType.MARKET_MAKER:
        if abs(price_bias) < 0.0006:
            return None
        return OrderSide.SELL if price_bias > 0 else OrderSide.BUY

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
        StrategyType.MOMENTUM: 0.0011,
        StrategyType.MEAN_REVERSION: 0.0009,
        StrategyType.MARKET_MAKER: 0.0005,
        StrategyType.FUNDAMENTAL: 0.0010,
    }[profile.strategy]
    ratio = base_ratio * runtime.aggression_level * session.rng.uniform(0.75, 1.25)
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
        StrategyType.MOMENTUM: 0.10,
        StrategyType.MEAN_REVERSION: 0.09,
        StrategyType.MARKET_MAKER: 0.05,
        StrategyType.FUNDAMENTAL: 0.10,
    }[profile.strategy]
    ratio = base_ratio * runtime.aggression_level * session.rng.uniform(0.7, 1.2)
    return round(max(0.0, asset_free * min(ratio, 0.35)), 6)


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


def _preloaded_tick_count(tick_interval_ms: int) -> int:
    safe_interval = max(tick_interval_ms, 1)
    return max((PRELOADED_WINDOW_MS + safe_interval - 1) // safe_interval, 1)


def _history_size_for(tick_interval_ms: int) -> int:
    return max(_preloaded_tick_count(tick_interval_ms) + PRELOADED_HISTORY_MARGIN, MAX_OHLCV_HISTORY)


def _decay_bias(value: float) -> float:
    decayed = value * SHOCK_BIAS_DECAY
    if abs(decayed) < 0.35:
        return 0.0
    return round(decayed, 4)


def _base_liquidity_for_bias(structural_bias_bps: float) -> float:
    if abs(structural_bias_bps) >= 25:
        return 6.8
    if abs(structural_bias_bps) >= 10:
        return 7.4
    return 8.0


_live_simulation_service = LiveSimulationService()


def get_live_simulation_service() -> LiveSimulationService:
    return _live_simulation_service