from fastapi.testclient import TestClient

from app.main import app
from app.simulation.live import get_live_simulation_service


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Market Simulator API"
    assert payload["default_compute_mode"] == "cpu"


def test_whale_shock_preview_endpoint() -> None:
    response = client.get("/api/v1/simulation/whale-shock/preview?side=sell&notional=2500")

    assert response.status_code == 200
    payload = response.json()
    assert payload["shock"]["side"] == "sell"
    assert payload["order_book_after"]["bid_depth"] < payload["order_book_before"]["bid_depth"]


def test_live_simulation_endpoints() -> None:
    live_service = get_live_simulation_service()
    live_service.reset()

    start_response = client.post("/api/v1/simulation/live/start?tick_interval_ms=400")
    assert start_response.status_code == 200
    start_payload = start_response.json()
    assert start_payload["status"] == "running"
    assert start_payload["tick"] >= 1

    read_response = client.get("/api/v1/simulation/live")
    assert read_response.status_code == 200
    assert read_response.json()["session_id"] == start_payload["session_id"]

    stop_response = client.post("/api/v1/simulation/live/stop")
    assert stop_response.status_code == 200
    assert stop_response.json()["status"] == "stopped"

    play_response = client.post("/api/v1/simulation/live/play?tick_interval_ms=125")
    assert play_response.status_code == 200
    play_payload = play_response.json()
    assert play_payload["status"] == "running"
    assert play_payload["session_id"] == start_payload["session_id"]
    assert play_payload["tick"] >= stop_response.json()["tick"]
    assert play_payload["tick_interval_ms"] == 125

    live_service.reset()


def test_live_whale_order_endpoint_buy_and_sell() -> None:
    live_service = get_live_simulation_service()
    live_service.reset()

    start_response = client.post("/api/v1/simulation/live/start?tick_interval_ms=5000")
    assert start_response.status_code == 200

    before_response = client.get("/api/v1/simulation/live")
    assert before_response.status_code == 200
    before_payload = before_response.json()

    buy_response = client.post(
        "/api/v1/simulation/live/whale-order",
        json={"side": "buy", "notional": 3000},
    )
    assert buy_response.status_code == 200
    buy_payload = buy_response.json()
    assert buy_payload["snapshot"]["session_id"] == before_payload["session_id"]
    assert buy_payload["whale_order"]["side"] == "buy"
    assert buy_payload["whale_order"]["mid_price_before"] == before_payload["order_book"]["mid_price"]
    assert buy_payload["whale_order"]["mid_price_after"] >= buy_payload["whale_order"]["mid_price_before"]
    assert buy_payload["whale_order"]["price_impact_bps"] >= 0
    assert buy_payload["whale_balance"]["cash_free"] >= 0
    assert buy_payload["whale_balance"]["asset_free"] >= 0

    sell_response = client.post(
        "/api/v1/simulation/live/whale-order",
        json={"side": "sell", "notional": 3000},
    )
    assert sell_response.status_code == 200
    sell_payload = sell_response.json()
    assert sell_payload["whale_order"]["side"] == "sell"
    assert sell_payload["whale_order"]["trades_executed"] > 0
    assert sell_payload["whale_order"]["price_impact_bps"] <= 0
    assert sell_payload["whale_order"]["remaining_side_depth"] >= 0
    assert sell_payload["whale_balance"]["cash_free"] >= 0
    assert sell_payload["whale_balance"]["asset_free"] >= 0

    live_service.reset()


def test_live_game_endpoints() -> None:
    live_service = get_live_simulation_service()
    live_service.reset()

    start_response = client.post("/api/v1/simulation/live/start?tick_interval_ms=750")
    assert start_response.status_code == 200

    game_start_response = client.post("/api/v1/simulation/live/game/start?duration_ticks=60")
    assert game_start_response.status_code == 200
    assert game_start_response.json()["game"]["status"] == "running"

    step_response = client.post("/api/v1/simulation/live/step?ticks=3")
    assert step_response.status_code == 200
    assert step_response.json()["game"]["remaining_ticks"] == 57

    whale_response = client.post(
        "/api/v1/simulation/live/whale-order",
        json={"side": "buy", "notional": 3000},
    )
    assert whale_response.status_code == 200
    assert whale_response.json()["snapshot"]["game"]["score"] != 0
    assert whale_response.json()["snapshot"]["game"]["score_breakdown"]["volume_score"] > 0

    end_response = client.post("/api/v1/simulation/live/game/end")
    assert end_response.status_code == 200
    assert end_response.json()["game"]["status"] == "ended"
    assert end_response.json()["game"]["final_result"] is not None

    reset_response = client.post("/api/v1/simulation/live/game/reset")
    assert reset_response.status_code == 200
    assert reset_response.json()["game"]["status"] == "idle"
    assert reset_response.json()["game"]["final_result"] is None

    live_service.reset()


def test_live_snapshot_order_book_levels_include_order_counts() -> None:
    live_service = get_live_simulation_service()
    live_service.reset()

    start_response = client.post("/api/v1/simulation/live/start?tick_interval_ms=750")
    assert start_response.status_code == 200
    payload = start_response.json()

    assert payload["order_book"]["bids"]
    assert payload["order_book"]["asks"]
    assert payload["order_book"]["bids"][0]["orders"] >= 1
    assert payload["order_book"]["asks"][0]["orders"] >= 1

    live_service.reset()
