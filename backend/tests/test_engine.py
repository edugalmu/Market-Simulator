from app.core.events import OrderSide
from app.simulation.engine import SimulationEngine
from app.simulation.live import LiveSimulationService, REGIME_PARAMS
from app.simulation.models import SessionConfig


def expected_preloaded_ticks(tick_interval_ms: int) -> int:
    _ = tick_interval_ms
    return 10 * 60


def assert_ohlcv_bar_invariants(bar) -> None:
    assert bar.high >= bar.open
    assert bar.high >= bar.close
    assert bar.low <= bar.open
    assert bar.low <= bar.close
    assert bar.trades >= 0
    assert bar.volume >= 0


def test_bootstrap_session_respects_target_agent_count() -> None:
    engine = SimulationEngine(gpu_enabled=False)
    summary = engine.bootstrap_session(SessionConfig())

    assert sum(entry.count for entry in summary.agent_mix) == 1000
    assert summary.order_book.best_bid < summary.order_book.best_ask
    assert summary.metrics.active_compute_backend == "cpu"


def test_gpu_auto_falls_back_to_cpu_when_disabled() -> None:
    engine = SimulationEngine(gpu_enabled=False)
    summary = engine.bootstrap_session(SessionConfig(compute_mode="gpu_auto"))

    assert summary.metrics.active_compute_backend == "cpu"


def test_whale_sell_preview_consumes_bid_depth_and_moves_price() -> None:
    engine = SimulationEngine(gpu_enabled=False)
    preview = engine.preview_whale_shock(
        SessionConfig(),
        side="sell",
        notional=3_000.0,
    )

    assert preview.shock.side == "sell"
    assert preview.order_book_after.bid_depth < preview.order_book_before.bid_depth
    assert preview.shock.price_impact_bps < 0
    assert preview.whale_balance.cash_reserved == 0


def test_whale_buy_preview_consumes_ask_depth_and_releases_cash_reserve() -> None:
    engine = SimulationEngine(gpu_enabled=False)
    preview = engine.preview_whale_shock(
        SessionConfig(),
        side="buy",
        notional=2_500.0,
    )

    assert preview.shock.side == "buy"
    assert preview.order_book_after.ask_depth < preview.order_book_before.ask_depth
    assert preview.whale_balance.cash_reserved == 0
    assert preview.whale_balance.asset_free > 0


def test_live_session_step_advances_ticks_and_preserves_depth() -> None:
    service = LiveSimulationService()
    snapshot = service.start(
        SessionConfig(),
        gpu_enabled=False,
        auto_run=False,
    )
    preload_ticks = expected_preloaded_ticks(snapshot.tick_interval_ms)

    advanced = service.step(ticks=6)
    service.reset()

    assert snapshot.tick == preload_ticks
    assert len(snapshot.ohlcv_history) == snapshot.tick
    assert advanced.tick == preload_ticks + 6
    assert advanced.last_tick is not None
    assert advanced.last_tick.active_agents > 0
    assert advanced.order_book.best_bid < advanced.order_book.best_ask
    assert advanced.order_book.bid_depth > 0
    assert advanced.order_book.ask_depth > 0
    assert len(set(advanced.recent_mid_prices)) > 1
    assert len(advanced.ohlcv_history) == advanced.tick
    assert advanced.ohlcv_history[-1].tick == advanced.tick

    for bar in advanced.ohlcv_history:
        assert_ohlcv_bar_invariants(bar)


def test_live_whale_order_uses_current_session_state() -> None:
    service = LiveSimulationService()
    service.start(SessionConfig(), gpu_enabled=False, auto_run=False)
    service.step(ticks=8)
    before = service.get_snapshot(raise_if_missing=True)

    response = service.execute_whale_order(side="buy", notional=3_000.0)
    service.reset()

    assert before.order_book.mid_price != SessionConfig().initial_price
    assert response.snapshot.session_id == before.session_id
    assert response.whale_order.mid_price_before == before.order_book.mid_price
    assert response.whale_order.mid_price_after >= response.whale_order.mid_price_before
    assert response.whale_balance.cash_free >= 0


def test_live_ohlcv_history_marks_whale_buy_and_sell_events() -> None:
    service = LiveSimulationService()
    service.start(SessionConfig(seed=17), gpu_enabled=False, auto_run=False)
    service.step(ticks=5)

    buy_response = service.execute_whale_order(side="buy", notional=3_000.0)
    sell_response = service.execute_whale_order(side="sell", notional=3_000.0)
    service.reset()

    buy_bar = buy_response.snapshot.ohlcv_history[-1]
    sell_bar = sell_response.snapshot.ohlcv_history[-1]

    assert buy_bar.tick == buy_response.whale_order.tick
    assert buy_bar.whale_side == "buy"
    assert buy_bar.whale_impact_bps == buy_response.whale_order.price_impact_bps
    assert buy_bar.trades == buy_response.whale_order.trades_executed
    assert buy_bar.volume == buy_response.whale_order.matched_quantity
    assert buy_response.whale_order.price_impact_bps >= 0

    assert sell_bar.tick == sell_response.whale_order.tick
    assert sell_bar.whale_side == "sell"
    assert sell_bar.whale_impact_bps == sell_response.whale_order.price_impact_bps
    assert sell_bar.trades == sell_response.whale_order.trades_executed
    assert sell_bar.volume == sell_response.whale_order.matched_quantity
    assert sell_response.whale_order.price_impact_bps <= 0

    for bar in sell_response.snapshot.ohlcv_history:
        assert_ohlcv_bar_invariants(bar)


def test_live_session_play_resumes_without_resetting_state() -> None:
    service = LiveSimulationService()
    snapshot = service.start(
        SessionConfig(seed=23),
        gpu_enabled=False,
        auto_run=False,
        tick_interval_ms=750,
    )
    advanced = service.step(ticks=4)
    paused = service.stop()

    resumed = service.play(tick_interval_ms=125)
    service.reset()

    assert paused.session_id == advanced.session_id
    assert paused.tick == advanced.tick
    assert paused.status == "stopped"
    assert resumed.session_id == snapshot.session_id
    assert resumed.tick == advanced.tick
    assert resumed.tick_interval_ms == 125
    assert resumed.status == "running"


def test_live_game_challenge_tracks_countdown_score_and_final_result() -> None:
    service = LiveSimulationService()
    service.start(SessionConfig(seed=31), gpu_enabled=False, auto_run=False)

    started = service.start_game(duration_ticks=60)
    assert started.game.status == "running"
    assert started.game.mode == "whale_challenge"
    assert started.game.remaining_ticks == 60

    advanced = service.step(ticks=4)
    assert advanced.game.remaining_ticks == 56

    whale_response = service.execute_whale_order(side="buy", notional=3_000.0)
    assert whale_response.snapshot.game.remaining_ticks == 55
    assert whale_response.snapshot.game.score != 0
    assert whale_response.snapshot.game.score_breakdown.volume_score > 0

    ended = service.end_game()
    assert ended.game.status == "ended"
    assert ended.game.final_result is not None
    assert ended.game.final_result.whale_orders == 1

    reset = service.reset_game()
    service.reset()

    assert reset.game.status == "idle"
    assert reset.game.final_result is None
    assert reset.game.score == 0
    assert reset.game.remaining_ticks == 60


def test_live_snapshot_exposes_aggregated_order_book_levels() -> None:
    service = LiveSimulationService()
    snapshot = service.start(SessionConfig(seed=41), gpu_enabled=False, auto_run=False)
    service.reset()

    assert snapshot.order_book.bids
    assert snapshot.order_book.asks
    assert len(snapshot.order_book.bids) <= 10
    assert len(snapshot.order_book.asks) <= 10
    assert snapshot.order_book.bids[0].price <= snapshot.order_book.best_bid
    assert snapshot.order_book.asks[0].price >= snapshot.order_book.best_ask
    assert all(level.orders >= 1 for level in snapshot.order_book.bids)
    assert all(level.orders >= 1 for level in snapshot.order_book.asks)


def test_live_snapshot_includes_market_regime() -> None:
    service = LiveSimulationService()
    snapshot = service.start(SessionConfig(seed=47), gpu_enabled=False, auto_run=False)
    service.reset()

    valid_regimes = {
        "neutral",
        "accumulation",
        "uptrend",
        "distribution",
        "downtrend",
        "panic",
        "short_squeeze",
        "post_whale_consolidation",
    }

    assert snapshot.market_regime.name in valid_regimes
    assert round(snapshot.market_regime.buy_bias + snapshot.market_regime.sell_bias, 6) == 1.0


def test_market_regime_ticks_remaining_decrease_and_can_transition() -> None:
    service = LiveSimulationService()
    snapshot = service.start(SessionConfig(seed=48), gpu_enabled=False, auto_run=False)
    session = service._session
    assert session is not None

    before_ticks = snapshot.market_regime.ticks_remaining
    next_snapshot = service.step(ticks=1)
    assert next_snapshot.market_regime.ticks_remaining <= before_ticks

    session.market_regime.ticks_remaining = 1
    previous_name = session.market_regime.name
    transitioned = service.step(ticks=1)
    service.reset()

    assert transitioned.market_regime.ticks_remaining > 0
    assert transitioned.market_regime.reason in {"timer_transition", "breakout_volume", "support_break_panic", "resistance_break_squeeze"}
    assert transitioned.market_regime.name != ""
    assert transitioned.market_regime.name != previous_name or transitioned.market_regime.reason == "timer_transition"


def test_large_whale_buy_can_trigger_post_whale_consolidation() -> None:
    service = LiveSimulationService()
    service.start(SessionConfig(seed=49), gpu_enabled=False, auto_run=False)
    response = service.execute_whale_order(side="buy", notional=75_000.0)
    service.reset()

    assert response.snapshot.market_regime.name == "post_whale_consolidation"
    assert response.snapshot.market_regime.reason == "whale_buy_shock"


def test_large_whale_sell_can_trigger_post_whale_consolidation() -> None:
    service = LiveSimulationService()
    service.start(SessionConfig(seed=50), gpu_enabled=False, auto_run=False)
    response = service.execute_whale_order(side="sell", notional=75_000.0)
    service.reset()

    assert response.snapshot.market_regime.name == "post_whale_consolidation"
    assert response.snapshot.market_regime.reason == "whale_sell_shock"


def test_panic_and_short_squeeze_have_more_gap_probability_than_neutral() -> None:
    assert REGIME_PARAMS["panic"]["gap_probability"] > REGIME_PARAMS["neutral"]["gap_probability"]
    assert REGIME_PARAMS["short_squeeze"]["gap_probability"] > REGIME_PARAMS["neutral"]["gap_probability"]


def test_order_book_preserves_some_orders_between_ticks() -> None:
    service = LiveSimulationService()
    service.start(SessionConfig(seed=44), gpu_enabled=False, auto_run=False)
    session = service._session
    assert session is not None

    order_id = session.order_book.add_limit_order(
        side=OrderSide.BUY,
        price=max((session.order_book.best_bid or session.last_price) - 5.0, 1.0),
        quantity=2.0,
        agent_id=999_000,
        strategy_type="test_persistent",
        created_tick=session.tick,
        ttl_ticks=5,
    )
    assert order_id is not None

    advanced = service.step(ticks=1)
    current_order_ids = {order.order_id for order in session.order_book.bid_orders + session.order_book.ask_orders}
    service.reset()

    assert order_id in current_order_ids
    assert advanced.order_book.best_bid <= advanced.order_book.best_ask


def test_orders_expire_by_ttl() -> None:
    service = LiveSimulationService()
    service.start(SessionConfig(seed=45), gpu_enabled=False, auto_run=False)
    session = service._session
    assert session is not None

    order_id = session.order_book.add_limit_order(
        side=OrderSide.BUY,
        price=(session.order_book.best_bid or session.last_price) - 1.0,
        quantity=1.0,
        agent_id=999_001,
        strategy_type="test",
        created_tick=session.tick,
        ttl_ticks=1,
    )
    assert order_id is not None

    service.step(ticks=1)
    service.reset()

    surviving_ids = {order.order_id for order in session.order_book.bid_orders + session.order_book.ask_orders}
    assert order_id not in surviving_ids


def test_normal_agents_keep_non_negative_balances() -> None:
    service = LiveSimulationService()
    service.start(SessionConfig(seed=46), gpu_enabled=False, auto_run=False)
    service.step(ticks=20)
    session = service._session
    assert session is not None

    for profile in session.profiles:
        balance = session.ledger.get_balance(profile.agent_id)
        assert balance.cash_free >= -1e-9
        assert balance.cash_reserved >= -1e-9
        assert balance.asset_free >= -1e-9
        assert balance.asset_reserved >= -1e-9

    service.reset()


def test_live_session_preload_ticks_do_not_change_with_speed() -> None:
    fast_snapshot = LiveSimulationService().start(
        SessionConfig(seed=51),
        gpu_enabled=False,
        auto_run=False,
        tick_interval_ms=125,
    )
    slow_service = LiveSimulationService()
    slow_snapshot = slow_service.start(
        SessionConfig(seed=52),
        gpu_enabled=False,
        auto_run=False,
        tick_interval_ms=750,
    )
    slow_service.reset()

    assert fast_snapshot.tick == 600
    assert slow_snapshot.tick == 600
    assert fast_snapshot.simulated_tick_interval_ms == 1000
    assert slow_snapshot.simulated_tick_interval_ms == 1000


def test_live_session_whale_starts_with_one_fifth_of_total_capital() -> None:
    service = LiveSimulationService()
    snapshot = service.start(SessionConfig(seed=61), gpu_enabled=False, auto_run=False)
    service.reset()

    total_capital = snapshot.metrics.total_agent_equity + snapshot.whale_balance.initial_total_equity
    whale_share = snapshot.whale_balance.initial_total_equity / total_capital

    assert round(whale_share, 2) == 0.20


def test_live_session_starts_with_neutral_whale_pnl_after_preload() -> None:
    service = LiveSimulationService()
    snapshot = service.start(SessionConfig(seed=62), gpu_enabled=False, auto_run=False)
    service.reset()

    assert round(snapshot.whale_balance.total_equity, 2) == round(snapshot.whale_balance.initial_total_equity, 2)


def test_live_snapshot_exposes_top_agents() -> None:
    service = LiveSimulationService()
    snapshot = service.start(SessionConfig(seed=71), gpu_enabled=False, auto_run=False)
    service.reset()

    assert len(snapshot.top_agents) == 10
    assert snapshot.top_agents[0].equity >= snapshot.top_agents[-1].equity
    assert all(entry.alias for entry in snapshot.top_agents)


def test_live_session_agent_cash_grows_after_one_simulated_minute() -> None:
    service = LiveSimulationService()
    snapshot = service.start(SessionConfig(seed=81), gpu_enabled=False, auto_run=False)
    before_equity = snapshot.metrics.total_agent_equity

    advanced = service.step(ticks=60)
    service.reset()

    assert advanced.metrics.total_agent_equity > before_equity


def test_live_whale_order_is_deterministic_for_same_seed() -> None:
    service_a = LiveSimulationService()
    service_b = LiveSimulationService()

    service_a.start(SessionConfig(seed=11), gpu_enabled=False, auto_run=False)
    service_b.start(SessionConfig(seed=11), gpu_enabled=False, auto_run=False)

    result_a = service_a.execute_whale_order(side="sell", notional=3_000.0)
    result_b = service_b.execute_whale_order(side="sell", notional=3_000.0)

    service_a.reset()
    service_b.reset()

    assert result_a.whale_order.matched_notional == result_b.whale_order.matched_notional
    assert result_a.whale_order.average_fill_price == result_b.whale_order.average_fill_price
    assert result_a.whale_order.price_impact_bps == result_b.whale_order.price_impact_bps
    assert result_a.snapshot.order_book.mid_price == result_b.snapshot.order_book.mid_price
    assert result_a.whale_balance.cash_free == result_b.whale_balance.cash_free
