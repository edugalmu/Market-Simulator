from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SessionConfig(BaseModel):
    seed: int = 7
    agent_count: int = 1000
    initial_price: float = 100.0
    initial_cash: float = 50000.0
    initial_asset: float = 1.25
    compute_mode: Literal["cpu", "gpu_auto", "gpu_force"] = "cpu"


class AgentMixEntry(BaseModel):
    strategy: str
    count: int


class OrderBookLevel(BaseModel):
    price: float
    quantity: float


class OrderBookSnapshot(BaseModel):
    best_bid: float
    best_ask: float
    mid_price: float
    spread_bps: float
    bid_depth: float
    ask_depth: float
    bids: list[OrderBookLevel] = Field(default_factory=list)
    asks: list[OrderBookLevel] = Field(default_factory=list)


class MarketMetrics(BaseModel):
    market_cap: float
    average_agent_equity: float
    total_asset_inventory: float
    active_compute_backend: str


class SimulationSummary(BaseModel):
    session_id: str
    status: Literal["bootstrap"]
    config: SessionConfig
    agent_mix: list[AgentMixEntry]
    order_book: OrderBookSnapshot
    metrics: MarketMetrics
    notes: list[str] = Field(default_factory=list)


class TickReport(BaseModel):
    tick: int
    active_agents: int
    buy_orders: int
    sell_orders: int
    trades_executed: int
    matched_notional: float
    matched_quantity: float
    price_change_bps: float
    mid_price: float


class OhlcvBar(BaseModel):
    tick: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    trades: int
    whale_side: Literal["buy", "sell"] | None = None
    whale_impact_bps: float | None = None


class LiveWhaleOrderRequest(BaseModel):
    side: Literal["buy", "sell"]
    notional: float = Field(gt=0)


class WhaleBalanceSnapshot(BaseModel):
    cash_free: float
    cash_reserved: float
    asset_free: float
    asset_reserved: float
    total_equity: float


class WhaleShockOutcome(BaseModel):
    side: Literal["buy", "sell"]
    requested_notional: float
    requested_quantity: float
    matched_notional: float
    matched_quantity: float
    quantity_remaining: float
    average_fill_price: float
    trades_executed: int
    price_impact_bps: float


class LiveWhaleOrderOutcome(WhaleShockOutcome):
    tick: int
    mid_price_before: float
    mid_price_after: float
    absolute_price_change: float
    remaining_side_depth: float
    impact_label: str


class GameScoreBreakdown(BaseModel):
    pnl_score: float = 0.0
    impact_score: float = 0.0
    volume_score: float = 0.0


class GameFinalResult(BaseModel):
    score: float
    pnl_executed: float
    max_impact_bps: float
    total_volume: float
    whale_orders: int
    ending_price: float
    starting_price: float


class LiveGameState(BaseModel):
    mode: Literal["whale_challenge"] | None = None
    status: Literal["idle", "running", "ended"] = "idle"
    started_at_tick: int | None = None
    duration_ticks: int = 60
    remaining_ticks: int = 60
    score: float = 0.0
    score_breakdown: GameScoreBreakdown = Field(default_factory=GameScoreBreakdown)
    final_result: GameFinalResult | None = None


class LiveSimulationSnapshot(BaseModel):
    session_id: str
    status: Literal["running", "stopped"]
    tick: int
    tick_interval_ms: int
    created_at: str
    updated_at: str
    config: SessionConfig
    agent_mix: list[AgentMixEntry]
    order_book: OrderBookSnapshot
    metrics: MarketMetrics
    recent_mid_prices: list[float] = Field(default_factory=list)
    ohlcv_history: list[OhlcvBar] = Field(default_factory=list)
    last_tick: TickReport | None = None
    whale_balance: WhaleBalanceSnapshot
    last_whale_order: LiveWhaleOrderOutcome | None = None
    game: LiveGameState = Field(default_factory=LiveGameState)
    notes: list[str] = Field(default_factory=list)


class WhaleShockPreview(BaseModel):
    session_id: str
    config: SessionConfig
    shock: WhaleShockOutcome
    order_book_before: OrderBookSnapshot
    order_book_after: OrderBookSnapshot
    whale_balance: WhaleBalanceSnapshot
    notes: list[str] = Field(default_factory=list)


class LiveWhaleOrderResponse(BaseModel):
    snapshot: LiveSimulationSnapshot
    whale_order: LiveWhaleOrderOutcome
    whale_balance: WhaleBalanceSnapshot
