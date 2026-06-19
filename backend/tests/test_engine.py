from app.simulation.engine import SimulationEngine
from app.simulation.live import LiveSimulationService
from app.simulation.models import SessionConfig


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

    advanced = service.step(ticks=6)
    service.reset()

    assert snapshot.tick == 1
    assert len(snapshot.ohlcv_history) == 1
    assert advanced.tick == 7
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
