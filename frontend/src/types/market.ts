export type ComputeMode = 'cpu' | 'gpu_auto' | 'gpu_force'

export type HealthResponse = {
  name: string
  version: string
  phase: string
  compute_modes: string[]
  default_compute_mode: ComputeMode
  gpu_enabled: boolean
  docs: string[]
}

export type SessionConfig = {
  seed: number
  agent_count: number
  initial_price: number
  initial_cash: number
  initial_asset: number
  compute_mode: ComputeMode
}

export type AgentMixEntry = {
  strategy: string
  count: number
}

export type TopAgentEntry = {
  agent_id: number
  alias: string
  strategy: string
  equity: number
}

export type OrderBookLevel = {
  price: number
  quantity: number
  orders: number
}

export type OrderBookSnapshot = {
  best_bid: number
  best_ask: number
  mid_price: number
  spread_bps: number
  bid_depth: number
  ask_depth: number
  bids: OrderBookLevel[]
  asks: OrderBookLevel[]
}

export type MarketMetrics = {
  market_cap: number
  average_agent_equity: number
  total_agent_equity: number
  total_asset_inventory: number
  active_compute_backend: string
}

export type SimulationSummary = {
  session_id: string
  status: 'bootstrap'
  config: SessionConfig
  agent_mix: AgentMixEntry[]
  order_book: OrderBookSnapshot
  metrics: MarketMetrics
  notes: string[]
}

export type TickReport = {
  tick: number
  active_agents: number
  buy_orders: number
  sell_orders: number
  trades_executed: number
  matched_notional: number
  matched_quantity: number
  price_change_bps: number
  mid_price: number
}

export type MarketRegimeState = {
  name: string
  ticks_remaining: number
  buy_bias: number
  sell_bias: number
  volatility_multiplier: number
  liquidity_multiplier: number
  spread_multiplier: number
  whale_activity_multiplier: number
  momentum_multiplier: number
  mean_reversion_multiplier: number
  maker_cancel_multiplier: number
  gap_probability: number
  reason: string | null
}

export type IcebergSummary = {
  active: number
  bid_count: number
  ask_count: number
  recent_absorbed_notional: number
  last_absorption_price: number | null
  last_absorption_side: string | null
}

export type OhlcvBar = {
  tick: number
  open: number
  high: number
  low: number
  close: number
  volume: number
  trades: number
  whale_side: 'buy' | 'sell' | null
  whale_impact_bps: number | null
}

export type LiveWhaleOrderOutcome = {
  tick: number
  side: 'buy' | 'sell'
  impact_label: string
  requested_notional: number
  requested_quantity: number
  matched_notional: number
  matched_quantity: number
  quantity_remaining: number
  average_fill_price: number
  trades_executed: number
  price_impact_bps: number
  mid_price_before: number
  mid_price_after: number
  absolute_price_change: number
  remaining_side_depth: number
}

export type GameScoreBreakdown = {
  pnl_score: number
  impact_score: number
  volume_score: number
}

export type GameFinalResult = {
  score: number
  pnl_executed: number
  max_impact_bps: number
  total_volume: number
  whale_orders: number
  ending_price: number
  starting_price: number
}

export type LiveGameState = {
  mode: 'whale_challenge' | null
  status: 'idle' | 'running' | 'ended'
  started_at_tick: number | null
  duration_ticks: number
  remaining_ticks: number
  score: number
  score_breakdown: GameScoreBreakdown
  final_result: GameFinalResult | null
}

export type LiveSimulationSnapshot = {
  session_id: string
  status: 'running' | 'stopped'
  tick: number
  tick_interval_ms: number
  simulated_tick_interval_ms: number
  created_at: string
  updated_at: string
  config: SessionConfig
  agent_mix: AgentMixEntry[]
  order_book: OrderBookSnapshot
  metrics: MarketMetrics
  recent_mid_prices: number[]
  ohlcv_history: OhlcvBar[]
  last_tick: TickReport | null
  market_regime: MarketRegimeState
  icebergs: IcebergSummary
  whale_balance: WhaleBalanceSnapshot
  last_whale_order: LiveWhaleOrderOutcome | null
  top_agents: TopAgentEntry[]
  game: LiveGameState
  notes: string[]
}

export type WhaleBalanceSnapshot = {
  cash_free: number
  cash_reserved: number
  asset_free: number
  asset_reserved: number
  initial_cash: number
  initial_asset: number
  initial_mark_price: number
  initial_total_equity: number
  total_equity: number
}

export type WhaleShockOutcome = {
  side: 'buy' | 'sell'
  requested_notional: number
  requested_quantity: number
  matched_notional: number
  matched_quantity: number
  quantity_remaining: number
  average_fill_price: number
  trades_executed: number
  price_impact_bps: number
}

export type WhaleShockPreview = {
  session_id: string
  config: SessionConfig
  shock: WhaleShockOutcome
  order_book_before: OrderBookSnapshot
  order_book_after: OrderBookSnapshot
  whale_balance: WhaleBalanceSnapshot
  notes: string[]
}

export type LiveWhaleOrderResponse = {
  snapshot: LiveSimulationSnapshot
  whale_order: LiveWhaleOrderOutcome
  whale_balance: WhaleBalanceSnapshot
}
