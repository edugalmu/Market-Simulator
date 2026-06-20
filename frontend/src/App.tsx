import { useState } from 'react'

import { MetricCard } from './components/MetricCard'
import { PriceChart, type ChartBar } from './components/PriceChart'
import { SectionCard } from './components/SectionCard'
import { useDashboardData } from './hooks/useDashboardData'
import type { OhlcvBar } from './types/market'
import './App.css'

type TimeframeSeconds = 1 | 5 | 10 | 30 | 60
type SimulationSpeed = 'normal' | 'fast' | 'very-fast'

const TIMEFRAME_OPTIONS: TimeframeSeconds[] = [1, 5, 10, 30, 60]
const PRELOADED_WINDOW_SECONDS = 10 * 60
const DEFAULT_SIMULATED_TICK_INTERVAL_MS = 1000
const SPEED_TO_INTERVAL_MS: Record<SimulationSpeed, number> = {
  normal: 750,
  fast: 250,
  'very-fast': 125,
}
const VISIBLE_BAR_TARGETS: Record<TimeframeSeconds, number> = {
  1: 120,
  5: 120,
  10: 90,
  30: 80,
  60: 60,
}

function App() {
  const {
    actionLoading,
    error,
    liveError,
    health,
    summary,
    whalePreview,
    liveSession,
    startLiveSession,
    playLiveSession,
    startLiveGame,
    endLiveGame,
    resetLiveGame,
    stopLiveSession,
    stepLiveSession,
    executeWhaleOrder,
  } = useDashboardData()
  const [whaleNotionalInput, setWhaleNotionalInput] = useState('3000')
  const [selectedTimeframe, setSelectedTimeframe] = useState<TimeframeSeconds>(1)
  const [isDevMode, setIsDevMode] = useState(false)
  const [selectedSpeed, setSelectedSpeed] = useState<SimulationSpeed>('normal')

  const whalePresets = [1000, 3000, 10000, 25000]
  const visibleWhalePresets = isDevMode ? whalePresets : whalePresets.slice(0, 3)
  const whaleNotional = Number.parseFloat(whaleNotionalInput.replace(',', '.'))
  const hasValidWhaleNotional = Number.isFinite(whaleNotional) && whaleNotional > 0
  const whaleActionDisabled =
    actionLoading ||
    !liveSession ||
    liveSession.status !== 'running' ||
    !hasValidWhaleNotional
  const lastWhaleOrder = liveSession?.last_whale_order ?? null
  const whaleBalance = liveSession?.whale_balance ?? null
  const rawOhlcvHistory = liveSession?.ohlcv_history ?? []
  const configuredTickIntervalMs = SPEED_TO_INTERVAL_MS[selectedSpeed]
  const simulatedTickIntervalMs = liveSession?.simulated_tick_interval_ms ?? DEFAULT_SIMULATED_TICK_INTERVAL_MS
  const referenceTimeMs = getReferenceTimeMs(liveSession?.updated_at)
  const visibleBarCount = VISIBLE_BAR_TARGETS[selectedTimeframe]
  const visiblePriceSampleCount = Math.ceil((PRELOADED_WINDOW_SECONDS * 1000) / simulatedTickIntervalMs) + 1
  const chartPrices = (liveSession?.recent_mid_prices ?? []).slice(-visiblePriceSampleCount)
  const chartBars = aggregateOhlcvBars(rawOhlcvHistory, selectedTimeframe, simulatedTickIntervalMs).slice(-visibleBarCount)
  const fallbackBars = buildGroupedPriceBars(chartPrices, liveSession?.tick ?? 0, selectedTimeframe, simulatedTickIntervalMs).slice(-visibleBarCount)
  const activeChartBars = chartBars.length > 0 ? chartBars : fallbackBars
  const whaleCashTotal = whaleBalance ? whaleBalance.cash_free + whaleBalance.cash_reserved : null
  const whaleTokenTotal = whaleBalance ? whaleBalance.asset_free + whaleBalance.asset_reserved : null
  const liveOrderBook = liveSession?.order_book ?? null
  const marketRegime = liveSession?.market_regime ?? null
  const liveIcebergs = liveSession?.icebergs ?? null
  const topAgents = liveSession?.top_agents ?? []
  const totalAgentEquity = liveSession?.metrics.total_agent_equity ?? null
  const initialWhaleEquity = whaleBalance?.initial_total_equity ?? null
  const estimatedPnl = whaleBalance
    && initialWhaleEquity !== null
    ? whaleBalance.total_equity - initialWhaleEquity
    : null
  const executedPnl = whaleBalance && whaleCashTotal !== null && whaleTokenTotal !== null
    && initialWhaleEquity !== null
    ? whaleCashTotal + whaleTokenTotal * whaleBalance.initial_mark_price - initialWhaleEquity
    : null
  const totalVisibleCapital = totalAgentEquity !== null && whaleBalance
    ? totalAgentEquity + whaleBalance.total_equity
    : null
  const whaleCapitalShare = totalVisibleCapital && whaleBalance
    ? (whaleBalance.total_equity / totalVisibleCapital) * 100
    : 0
  const capitalDonutStyle = {
    backgroundImage: `conic-gradient(#ec8a20 0 ${whaleCapitalShare}%, rgba(140, 226, 212, 0.9) ${whaleCapitalShare}% 100%)`,
  }
  const game = liveSession?.game ?? null
  const finalGameResult = game?.final_result ?? null
  const challengeStatusLabel = game?.status === 'running'
    ? 'En marcha'
    : game?.status === 'ended'
      ? 'Terminado'
      : 'Esperando'

  const architecturePillars = [
    'Backend FastAPI desacoplado de la UI',
    '1,000 agentes simples como MVP ampliable',
    'Order book y ledger como fuente unica de verdad',
    'GPU NVIDIA opcional con fallback a CPU',
  ]

  const nextMilestones = [
    'Persistir sesiones reales en SQLite y preparar replay.',
    'Reemplazar market orders sinteticas por un matching continuo mas rico.',
    'Emitir snapshots por streaming para evitar polling desde la UI.',
  ]

  const whaleImpactTone = lastWhaleOrder?.side === 'buy'
    ? 'impact-chip impact-chip--buy'
    : lastWhaleOrder?.side === 'sell'
      ? 'impact-chip impact-chip--sell'
      : 'impact-chip'

  function handlePauseSimulation() {
    if (!liveSession || liveSession.status !== 'running') {
      return
    }

    void stopLiveSession()
  }

  function handleSpeedSelection(speed: SimulationSpeed) {
    const nextInterval = SPEED_TO_INTERVAL_MS[speed]
    setSelectedSpeed(speed)

    if (!liveSession) {
      void startLiveSession(nextInterval)
      return
    }

    void playLiveSession(nextInterval)
  }

  function handleStartChallenge() {
    if (!liveSession) {
      return
    }

    void startLiveGame(60)
  }

  return (
    <main className="app-shell">
      <section className="hero-panel">
        <div className="hero-spotlight">
          <div className="hero-spotlight__header">
            <p className="eyebrow">Mercado en vivo</p>
            <button
              className={`mode-toggle mode-toggle--hero${isDevMode ? ' mode-toggle--active' : ''}`}
              onClick={() => setIsDevMode((current) => !current)}
              type="button"
            >
              Modo DEV
            </button>
          </div>

          <div className="market-toolbar">
            <div className="market-toolbar__top">
              <div className="simulation-box">
                <span className="simulation-box__label">Simulacion</span>
                <div className="simulation-box__actions simulation-box__actions--stacked">
                  <button className="control-button control-button--wide" onClick={() => void startLiveSession(configuredTickIntervalMs)} disabled={actionLoading}>
                    Reiniciar simulacion
                  </button>
                </div>

                <div className="speed-selector speed-selector--full" role="group" aria-label="Controles de pausa y velocidad de simulacion">
                  <button
                    aria-label="Pausar simulacion"
                    className={`speed-button speed-button--icon${liveSession?.status === 'stopped' ? ' speed-button--selected' : ''}`}
                    onClick={handlePauseSimulation}
                    title="Pausa"
                    type="button"
                    disabled={actionLoading || !liveSession || liveSession.status !== 'running'}
                  >
                    ||
                  </button>
                  {([
                    { key: 'normal', label: '>', title: 'Velocidad normal' },
                    { key: 'fast', label: '>>', title: 'Doble play' },
                    { key: 'very-fast', label: '>>>', title: 'Triple play' },
                  ] as const).map((speed) => (
                    <button
                      key={speed.key}
                      aria-label={speed.title}
                      className={`speed-button speed-button--icon${selectedSpeed === speed.key && liveSession?.status === 'running' ? ' speed-button--selected' : ''}`}
                      onClick={() => handleSpeedSelection(speed.key)}
                      title={speed.title}
                      type="button"
                      disabled={actionLoading}
                    >
                      {speed.label}
                    </button>
                  ))}
                </div>

                {isDevMode ? (
                  <div className="simulation-box__footer">
                    <button
                      className="control-button control-button--step"
                      onClick={() => void stepLiveSession(5)}
                      disabled={actionLoading || !liveSession}
                    >
                      Avanzar 5 ticks
                    </button>
                  </div>
                ) : null}
              </div>

              <div className="market-toolbar__side">
                <section className="capital-overview-card capital-overview-card--top" aria-label="Capital total del mercado">
                  <div className="capital-overview-card__visual">
                    <div className="capital-donut capital-donut--compact" style={capitalDonutStyle}>
                      <div className="capital-donut__center">
                        <span>Ballena</span>
                        <strong>{formatPercent(whaleCapitalShare)}</strong>
                      </div>
                    </div>
                    <div className="capital-overview-card__stats">
                      <div className="capital-overview-card__row">
                        <span>Agentes</span>
                        <strong>{totalAgentEquity !== null ? formatCurrency(totalAgentEquity) : '--'}</strong>
                      </div>
                      <div className="capital-overview-card__row">
                        <span>Ballena</span>
                        <strong>{whaleBalance ? formatCurrency(whaleBalance.total_equity) : '--'}</strong>
                      </div>
                      <div className="capital-overview-card__row">
                        <span>Total</span>
                        <strong>{totalVisibleCapital !== null ? formatCurrency(totalVisibleCapital) : '--'}</strong>
                      </div>
                    </div>
                  </div>
                </section>

                <div className="timeframe-selector timeframe-selector--market" role="group" aria-label="Selector de marco temporal de velas">
                  <span className="timeframe-selector__label">Velas</span>
                  <div className="timeframe-selector__actions timeframe-selector__actions--chart">
                    {TIMEFRAME_OPTIONS.map((timeframe) => {
                      const isSelected = selectedTimeframe === timeframe
                      const buttonClassName = [
                        'timeframe-button',
                        isSelected ? 'timeframe-button--selected' : '',
                      ]
                        .filter(Boolean)
                        .join(' ')

                      return (
                        <button
                          key={timeframe}
                          className={buttonClassName}
                          onClick={() => setSelectedTimeframe(timeframe)}
                          type="button"
                        >
                          {formatTimeframeOptionLabel(timeframe)}
                        </button>
                      )
                    })}
                  </div>
                </div>
              </div>
            </div>

            <div className="market-trade-bar">
              <div className="market-trade-bar__presets">
                {visibleWhalePresets.map((preset) => {
                  const selected = Number.parseFloat(whaleNotionalInput.replace(',', '.')) === preset
                  return (
                    <button
                      key={preset}
                      className={`notional-chip${selected ? ' notional-chip--selected' : ''}`}
                      onClick={() => setWhaleNotionalInput(String(preset))}
                      type="button"
                    >
                      {preset.toLocaleString('en-US')}
                    </button>
                  )
                })}
              </div>

              <div className="market-price-card">
                <span>Precio</span>
                <strong>{liveSession ? formatCurrency(liveSession.order_book.mid_price) : '--'}</strong>
              </div>

              {isDevMode ? (
                <label className="input-stack input-stack--compact">
                  <span>Notional</span>
                  <input
                    className="control-input control-input--compact"
                    type="number"
                    min="1"
                    step="100"
                    value={whaleNotionalInput}
                    onChange={(event) => setWhaleNotionalInput(event.target.value)}
                  />
                </label>
              ) : null}

              <div className="market-trade-bar__actions">
                <button
                  className="control-button control-button--buy"
                  onClick={() => void executeWhaleOrder('buy', whaleNotional)}
                  disabled={whaleActionDisabled}
                >
                  Whale Buy
                </button>
                <button
                  className="control-button control-button--sell"
                  onClick={() => void executeWhaleOrder('sell', whaleNotional)}
                  disabled={whaleActionDisabled}
                >
                  Whale Sell
                </button>
              </div>
            </div>
          </div>

          <div className="position-strip">
            <div className="position-pill">
              <span>P&L estimado</span>
              <strong className={getPnlClassName(estimatedPnl)}>
                {formatSignedCurrency(estimatedPnl)}
              </strong>
            </div>
            <div className="position-pill">
              <span>P&L ejecutado</span>
              <strong className={getPnlClassName(executedPnl)}>
                {formatSignedCurrency(executedPnl)}
              </strong>
            </div>
            <div className="position-pill">
              <span>Tokens</span>
              <strong className="position-pill__value">{formatQuantity(whaleTokenTotal, 4)}</strong>
            </div>
            <div className="position-pill">
              <span>Dolares</span>
              <strong className="position-pill__value">{formatCurrency(whaleCashTotal)}</strong>
            </div>
            <div className="position-pill">
              <span>Mcap jugador</span>
              <strong className="position-pill__value">{whaleBalance ? formatCurrency(whaleBalance.total_equity) : '--'}</strong>
            </div>
          </div>

          <PriceChart
            prices={chartPrices}
            bars={activeChartBars}
            currentTick={liveSession?.tick ?? 0}
            mode="candles"
            tickIntervalMs={simulatedTickIntervalMs}
            referenceTimeMs={referenceTimeMs}
          />

          <div className={`post-chart-grid${isDevMode ? ' post-chart-grid--dev' : ''}`}>
            <section className="challenge-card" aria-label="Whale Challenge">
              <div className="challenge-card__header">
                <div className="challenge-card__copy">
                  <p className="challenge-card__eyebrow">Whale Challenge</p>
                  <h3 className="challenge-card__title">60 segundos</h3>
                  <p className="challenge-card__objective">
                    Objetivo: mueve el mercado y maximiza el P&amp;L ejecutado sin quedarte sin liquidez.
                  </p>
                </div>
                <span className={`challenge-status challenge-status--${game?.status ?? 'idle'}`}>
                  {challengeStatusLabel}
                </span>
              </div>

              <div className="challenge-card__stats">
                <div className="challenge-stat">
                  <span>Tiempo</span>
                  <strong>{game ? `${game.remaining_ticks}s` : '60s'}</strong>
                </div>
                <div className="challenge-stat">
                  <span>Score</span>
                  <strong>{formatGameScore(game?.score ?? 0)}</strong>
                </div>
                <div className="challenge-stat">
                  <span>Estado</span>
                  <strong>{challengeStatusLabel}</strong>
                </div>
              </div>

              <div className="challenge-breakdown">
                <span>P&amp;L score {formatGameScore(game?.score_breakdown.pnl_score ?? 0)}</span>
                <span>Impacto {formatGameScore(game?.score_breakdown.impact_score ?? 0)}</span>
                <span>Volumen {formatGameScore(game?.score_breakdown.volume_score ?? 0)}</span>
              </div>

              <div className="challenge-card__actions">
                {game?.status === 'running' ? (
                  <button
                    className="control-button control-button--secondary"
                    onClick={() => void endLiveGame()}
                    disabled={actionLoading || !liveSession}
                    type="button"
                  >
                    Terminar reto
                  </button>
                ) : (
                  <button
                    className="control-button"
                    onClick={handleStartChallenge}
                    disabled={actionLoading || !liveSession}
                    type="button"
                  >
                    {game?.status === 'ended' ? 'Reintentar reto' : 'Iniciar reto 60s'}
                  </button>
                )}

                <button
                  className="control-button control-button--secondary"
                  onClick={() => void resetLiveGame()}
                  disabled={actionLoading || !liveSession || game?.status === 'idle'}
                  type="button"
                >
                  Reiniciar reto
                </button>
              </div>

              {finalGameResult ? (
                <div className="challenge-result">
                  <div className="challenge-result__item">
                    <span>Resultado final</span>
                    <strong>{formatGameScore(finalGameResult.score)}</strong>
                  </div>
                  <div className="challenge-result__item">
                    <span>P&amp;L ejecutado</span>
                    <strong>{formatSignedCurrency(finalGameResult.pnl_executed)}</strong>
                  </div>
                  <div className="challenge-result__item">
                    <span>Maximo impacto</span>
                    <strong>{finalGameResult.max_impact_bps.toFixed(2)} bps</strong>
                  </div>
                  <div className="challenge-result__item">
                    <span>Volumen ballena</span>
                    <strong>{formatGameScore(finalGameResult.total_volume)}</strong>
                  </div>
                  <div className="challenge-result__item">
                    <span>Ordenes ejecutadas</span>
                    <strong>{finalGameResult.whale_orders}</strong>
                  </div>
                  <div className="challenge-result__item">
                    <span>Precio final</span>
                    <strong>${finalGameResult.ending_price.toFixed(2)}</strong>
                  </div>
                </div>
              ) : null}
            </section>

            {isDevMode ? (
              <div className="dev-side-stack">
                <section className="regime-card" aria-label="Market Regime">
                  <div className="regime-card__header">
                    <div>
                      <p className="order-book-card__eyebrow">Market Regime</p>
                      <h3 className="order-book-card__title">{marketRegime?.name ?? '--'}</h3>
                    </div>
                    <span className="micro-tag">
                      {marketRegime ? `${marketRegime.ticks_remaining} ticks` : '--'}
                    </span>
                  </div>

                  <div className="regime-card__grid">
                    <div className="regime-card__item">
                      <span>Buy / Sell</span>
                      <strong>
                        {marketRegime
                          ? `${formatPercent(marketRegime.buy_bias * 100)} / ${formatPercent(marketRegime.sell_bias * 100)}`
                          : '--'}
                      </strong>
                    </div>
                    <div className="regime-card__item">
                      <span>Volatilidad</span>
                      <strong>{marketRegime ? `${marketRegime.volatility_multiplier.toFixed(2)}x` : '--'}</strong>
                    </div>
                    <div className="regime-card__item">
                      <span>Liquidez</span>
                      <strong>{marketRegime ? `${marketRegime.liquidity_multiplier.toFixed(2)}x` : '--'}</strong>
                    </div>
                    <div className="regime-card__item">
                      <span>Spread</span>
                      <strong>{marketRegime ? `${marketRegime.spread_multiplier.toFixed(2)}x` : '--'}</strong>
                    </div>
                    <div className="regime-card__item">
                      <span>Gaps</span>
                      <strong>{marketRegime ? formatPercent(marketRegime.gap_probability * 100) : '--'}</strong>
                    </div>
                    <div className="regime-card__item">
                      <span>Motivo</span>
                      <strong>{marketRegime?.reason ?? '--'}</strong>
                    </div>
                  </div>
                </section>

                <section className="iceberg-card" aria-label="Icebergs">
                  <div className="regime-card__header">
                    <div>
                      <p className="order-book-card__eyebrow">Icebergs</p>
                      <h3 className="order-book-card__title">Absorción oculta</h3>
                    </div>
                  </div>

                  <div className="regime-card__grid">
                    <div className="regime-card__item">
                      <span>Activos</span>
                      <strong>{liveIcebergs ? liveIcebergs.active : '--'}</strong>
                    </div>
                    <div className="regime-card__item">
                      <span>Bid / Ask</span>
                      <strong>{liveIcebergs ? `${liveIcebergs.bid_count} / ${liveIcebergs.ask_count}` : '--'}</strong>
                    </div>
                    <div className="regime-card__item">
                      <span>Absorción</span>
                      <strong>{liveIcebergs ? formatCurrency(liveIcebergs.recent_absorbed_notional) : '--'}</strong>
                    </div>
                    <div className="regime-card__item">
                      <span>Último absorbido</span>
                      <strong>{liveIcebergs ? formatCurrency(liveIcebergs.last_absorbed_notional) : '--'}</strong>
                    </div>
                    <div className="regime-card__item">
                      <span>Último nivel</span>
                      <strong>
                        {liveIcebergs && liveIcebergs.last_absorption_price !== null && liveIcebergs.last_absorption_side
                          ? `${formatCurrency(liveIcebergs.last_absorption_price)} ${liveIcebergs.last_absorption_side.toUpperCase()}`
                          : '--'}
                      </strong>
                    </div>
                    <div className="regime-card__item">
                      <span>Ticks desde absorción</span>
                      <strong>{liveIcebergs?.ticks_since_absorption ?? '--'}</strong>
                    </div>
                  </div>
                </section>

                <section className="order-book-card" aria-label="Order Book">
                  <div className="order-book-card__header">
                    <div>
                      <p className="order-book-card__eyebrow">Order Book</p>
                      <h3 className="order-book-card__title">Liquidez visible</h3>
                    </div>
                    <span className="micro-tag">
                      Spread {liveOrderBook ? `${liveOrderBook.spread_bps.toFixed(2)} bps` : '--'}
                    </span>
                  </div>

                  <div className="order-book-card__summary">
                    <div className="order-book-card__stat">
                      <span>Best bid</span>
                      <strong>{liveOrderBook ? `$${liveOrderBook.best_bid.toFixed(2)}` : '--'}</strong>
                    </div>
                    <div className="order-book-card__stat">
                      <span>Best ask</span>
                      <strong>{liveOrderBook ? `$${liveOrderBook.best_ask.toFixed(2)}` : '--'}</strong>
                    </div>
                    <div className="order-book-card__stat">
                      <span>Bid depth</span>
                      <strong>{liveOrderBook ? formatBookNumber(liveOrderBook.bid_depth) : '--'}</strong>
                    </div>
                    <div className="order-book-card__stat">
                      <span>Ask depth</span>
                      <strong>{liveOrderBook ? formatBookNumber(liveOrderBook.ask_depth) : '--'}</strong>
                    </div>
                  </div>

                  <div className="order-book-table">
                    <div className="order-book-table__side">
                      <div className="order-book-table__heading">Bids</div>
                      {(liveOrderBook?.bids ?? []).map((level) => (
                        <div className="order-book-row order-book-row--bid" key={`bid-${level.price}`}>
                          <div
                            className="order-book-row__bar order-book-row__bar--bid"
                            style={{ width: `${getOrderBookBarWidth(level.quantity, liveOrderBook?.bids ?? [], liveOrderBook?.asks ?? [])}%` }}
                          />
                          <div className="order-book-row__content">
                            <strong>{level.price.toFixed(2)}</strong>
                            <span>{formatBookNumber(level.quantity)}</span>
                            <em>{level.orders} ord</em>
                          </div>
                        </div>
                      ))}
                    </div>

                    <div className="order-book-table__side">
                      <div className="order-book-table__heading">Asks</div>
                      {(liveOrderBook?.asks ?? []).map((level) => (
                        <div className="order-book-row order-book-row--ask" key={`ask-${level.price}`}>
                          <div
                            className="order-book-row__bar order-book-row__bar--ask"
                            style={{ width: `${getOrderBookBarWidth(level.quantity, liveOrderBook?.bids ?? [], liveOrderBook?.asks ?? [])}%` }}
                          />
                          <div className="order-book-row__content">
                            <strong>{level.price.toFixed(2)}</strong>
                            <span>{formatBookNumber(level.quantity)}</span>
                            <em>{level.orders} ord</em>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </section>
              </div>
            ) : null}
          </div>
        </div>
      </section>

      {error ? <p className="banner banner--warning">{error}</p> : null}
      {liveError ? <p className="banner banner--warning">{liveError}</p> : null}

      {isDevMode ? (
        <section className="metrics-grid">
          <MetricCard label="Backend" value={health ? health.phase : 'pendiente'} tone="accent" />
          <MetricCard label="Sesion viva" value={liveSession?.status ?? 'sin sesion'} />
          <MetricCard
            label="Agentes objetivo"
            value={(liveSession?.config.agent_count ?? summary?.config.agent_count ?? 1000).toLocaleString('en-US')}
          />
          <MetricCard
            label="Precio medio"
            value={liveSession ? `$${liveSession.order_book.mid_price.toFixed(2)}` : summary ? `$${summary.order_book.mid_price.toFixed(2)}` : '$100.00'}
          />
          <MetricCard
            label="Compute activo"
            value={liveSession?.metrics.active_compute_backend ?? summary?.metrics.active_compute_backend ?? 'cpu'}
          />
        </section>
      ) : null}

      {isDevMode ? <section className="content-grid">

        <SectionCard
          title="Sesion en vivo"
          eyebrow="Motor activo"
          aside={<span className="micro-tag">{liveSession?.session_id ?? 'sin iniciar'}</span>}
        >
          <div className="mini-grid">
            <MetricCard label="Estado" value={liveSession?.status ?? 'idle'} tone="accent" />
            <MetricCard label="Tick actual" value={liveSession ? liveSession.tick.toString() : '--'} />
            <MetricCard
              label="Intervalo"
              value={liveSession ? `${liveSession.tick_interval_ms} ms` : '--'}
            />
            <MetricCard
              label="Ultimo precio"
              value={liveSession ? `$${liveSession.order_book.mid_price.toFixed(2)}` : '--'}
            />
          </div>
          <div className="mix-table">
            <div className="mix-row">
              <span>Agentes activos ultimo tick</span>
              <strong>{liveSession?.last_tick?.active_agents ?? '--'}</strong>
            </div>
            <div className="mix-row">
              <span>Trades ejecutados</span>
              <strong>{liveSession?.last_tick?.trades_executed ?? '--'}</strong>
            </div>
            <div className="mix-row">
              <span>Notional matcheado</span>
              <strong>
                {liveSession?.last_tick
                  ? `$${liveSession.last_tick.matched_notional.toFixed(2)}`
                  : '--'}
              </strong>
            </div>
            <div className="mix-row">
              <span>Cambio de precio</span>
              <strong>
                {liveSession?.last_tick
                  ? `${liveSession.last_tick.price_change_bps.toFixed(2)} bps`
                  : '--'}
              </strong>
            </div>
          </div>
          <p className="section-note">
            La sesion viva se inicia automaticamente al cargar la app si no existe una activa.
            Usa reiniciar para arrancar otra desde la seed base o avanzar ticks manuales si la detienes.
          </p>
        </SectionCard>

        <SectionCard
          title="Arquitectura aprobada"
          eyebrow="Base de trabajo"
          aside={<span className="micro-tag">Windows local → Web</span>}
        >
          <ul className="bullet-list">
            {architecturePillars.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </SectionCard>

        <SectionCard
          title="Sesion bootstrap"
          eyebrow="API conectada"
          aside={<span className="micro-tag">{summary?.session_id ?? 'sin backend'}</span>}
        >
          <div className="mini-grid">
            <MetricCard
              label="Best bid"
              value={summary ? `$${summary.order_book.best_bid.toFixed(2)}` : '--'}
            />
            <MetricCard
              label="Best ask"
              value={summary ? `$${summary.order_book.best_ask.toFixed(2)}` : '--'}
            />
            <MetricCard
              label="Spread"
              value={summary ? `${summary.order_book.spread_bps.toFixed(2)} bps` : '--'}
            />
            <MetricCard
              label="Patrimonio medio"
              value={summary ? `$${summary.metrics.average_agent_equity.toFixed(2)}` : '--'}
            />
          </div>
          <p className="section-note">
            El bootstrap sigue siendo una sesión base sin agentes operando,
            pero ya convive con un preview de whale shock que ejecuta un barrido
            real del libro por API.
          </p>
        </SectionCard>

        <SectionCard
          title="Whale shock preview"
          eyebrow="Shock sintetico puntual"
          aside={<span className="micro-tag">{whalePreview?.shock.side ?? 'sell'} market sweep</span>}
        >
          <div className="mini-grid">
            <MetricCard
              label="Notional"
              value={whalePreview ? `$${whalePreview.shock.requested_notional.toFixed(0)}` : '--'}
            />
            <MetricCard
              label="Impacto"
              value={whalePreview ? `${whalePreview.shock.price_impact_bps.toFixed(2)} bps` : '--'}
              tone="accent"
            />
            <MetricCard
              label="Trades"
              value={whalePreview ? whalePreview.shock.trades_executed.toString() : '--'}
            />
            <MetricCard
              label="Precio medio"
              value={whalePreview ? `$${whalePreview.shock.average_fill_price.toFixed(2)}` : '--'}
            />
          </div>
          <div className="mix-table">
            <div className="mix-row">
              <span>Bid depth antes</span>
              <strong>
                {whalePreview
                  ? formatBookNumber(whalePreview.order_book_before.bid_depth)
                  : '--'}
              </strong>
            </div>
            <div className="mix-row">
              <span>Bid depth despues</span>
              <strong>
                {whalePreview
                  ? formatBookNumber(whalePreview.order_book_after.bid_depth)
                  : '--'}
              </strong>
            </div>
            <div className="mix-row">
              <span>Cash libre del whale</span>
              <strong>
                {whalePreview
                  ? `$${whalePreview.whale_balance.cash_free.toFixed(2)}`
                  : '--'}
              </strong>
            </div>
          </div>
          <p className="section-note">
            Este preview usa el mismo motor del backend para consumir liquidez y
            liquidar reservas. Todavía no persiste la sesión ni reinyecta el shock
            sobre un mercado en marcha.
          </p>
        </SectionCard>

        <SectionCard
          title="Ultima orden de ballena"
          eyebrow="Shock sobre sesion viva"
          aside={<span className={whaleImpactTone}>{lastWhaleOrder?.side ?? 'sin orden'}</span>}
        >
          <div className="mini-grid">
            <MetricCard
              label="Notional solicitado"
              value={lastWhaleOrder ? `$${lastWhaleOrder.requested_notional.toFixed(0)}` : '--'}
            />
            <MetricCard
              label="Notional ejecutado"
              value={lastWhaleOrder ? `$${lastWhaleOrder.matched_notional.toFixed(2)}` : '--'}
            />
            <MetricCard
              label="Cantidad ejecutada"
              value={lastWhaleOrder ? lastWhaleOrder.matched_quantity.toFixed(4) : '--'}
            />
            <MetricCard
              label="Precio medio fill"
              value={lastWhaleOrder ? `$${lastWhaleOrder.average_fill_price.toFixed(2)}` : '--'}
            />
            <MetricCard
              label="Impacto"
              value={lastWhaleOrder ? `${lastWhaleOrder.price_impact_bps.toFixed(2)} bps` : '--'}
              tone="accent"
            />
            <MetricCard
              label="Trades ejecutados"
              value={lastWhaleOrder ? lastWhaleOrder.trades_executed.toString() : '--'}
            />
          </div>
          <div className="mix-table">
            <div className="mix-row">
              <span>Precio antes</span>
              <strong>{lastWhaleOrder ? `$${lastWhaleOrder.mid_price_before.toFixed(2)}` : '--'}</strong>
            </div>
            <div className="mix-row">
              <span>Precio despues</span>
              <strong>{lastWhaleOrder ? `$${lastWhaleOrder.mid_price_after.toFixed(2)}` : '--'}</strong>
            </div>
            <div className="mix-row">
              <span>Variacion absoluta</span>
              <strong>{lastWhaleOrder ? lastWhaleOrder.absolute_price_change.toFixed(2) : '--'}</strong>
            </div>
            <div className="mix-row">
              <span>Liquidez restante lado impactado</span>
              <strong>{lastWhaleOrder ? lastWhaleOrder.remaining_side_depth.toFixed(4) : '--'}</strong>
            </div>
            <div className="mix-row">
              <span>Cantidad restante sin ejecutar</span>
              <strong>{lastWhaleOrder ? lastWhaleOrder.quantity_remaining.toFixed(4) : '--'}</strong>
            </div>
          </div>
        </SectionCard>

        <SectionCard title="Balance ballena" eyebrow="Cuenta de control">
          <div className="mini-grid">
            <MetricCard
              label="Cash libre"
              value={whaleBalance ? formatCurrency(whaleBalance.cash_free) : '--'}
            />
            <MetricCard
              label="Cash reservado"
              value={whaleBalance ? formatCurrency(whaleBalance.cash_reserved) : '--'}
            />
            <MetricCard
              label="Asset libre"
              value={whaleBalance ? formatQuantity(whaleBalance.asset_free, 4) : '--'}
            />
            <MetricCard
              label="Asset reservado"
              value={whaleBalance ? formatQuantity(whaleBalance.asset_reserved, 4) : '--'}
            />
            <MetricCard
              label="Equity"
              value={whaleBalance ? formatCurrency(whaleBalance.total_equity) : '--'}
              tone="accent"
            />
          </div>
        </SectionCard>

        <SectionCard title="Top 10 agentes" eyebrow="Leaderboard dinamico">
          <div className="mix-table">
            {topAgents.map((agent, index) => (
              <div className="mix-row" key={agent.agent_id}>
                <span>{`${index + 1}. ${agent.alias} · ${agent.strategy}`}</span>
                <strong>{formatCurrency(agent.equity)}</strong>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Siguientes hitos" eyebrow="Ruta inmediata">
          <ol className="ordered-list">
            {nextMilestones.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ol>
          <p className="section-note">
            La documentación detallada del plan y la migración a web está en la carpeta
            <code> docs/</code> del repositorio.
          </p>
        </SectionCard>
      </section> : null}
    </main>
  )
}

function aggregateOhlcvBars(bars: OhlcvBar[], timeframeSeconds: number, tickIntervalMs: number): ChartBar[] {
  if (bars.length === 0) {
    return []
  }

  const aggregatedGroups: OhlcvBar[][] = []
  let currentBucketKey: number | null = null
  let currentGroup: OhlcvBar[] = []

  bars.forEach((bar) => {
    const bucketKey = getTimeBucketKey(bar.tick, timeframeSeconds, tickIntervalMs)

    if (currentBucketKey === null || bucketKey === currentBucketKey) {
      currentBucketKey = bucketKey
      currentGroup.push(bar)
      return
    }

    aggregatedGroups.push(currentGroup)
    currentBucketKey = bucketKey
    currentGroup = [bar]
  })

  if (currentGroup.length > 0) {
    aggregatedGroups.push(currentGroup)
  }

  return trimLeadingPartialGroups(aggregatedGroups, timeframeSeconds, tickIntervalMs)
    .map((group) => buildBackendChartBar(group))
}

function buildGroupedPriceBars(prices: number[], currentTick: number, timeframeSeconds: number, tickIntervalMs: number): ChartBar[] {
  if (prices.length === 0) {
    return []
  }

  const startTick = Math.max(currentTick - prices.length + 1, 0)
  const groupedBars: Array<Array<{ tick: number, price: number }>> = []
  let currentBucketKey: number | null = null
  let currentGroup: Array<{ tick: number, price: number }> = []

  prices.forEach((price, index) => {
    const tick = startTick + index
    const bucketKey = getTimeBucketKey(tick, timeframeSeconds, tickIntervalMs)

    if (currentBucketKey === null || bucketKey === currentBucketKey) {
      currentBucketKey = bucketKey
      currentGroup.push({ tick, price })
      return
    }

    groupedBars.push(currentGroup)
    currentBucketKey = bucketKey
    currentGroup = [{ tick, price }]
  })

  if (currentGroup.length > 0) {
    groupedBars.push(currentGroup)
  }

  return trimLeadingPartialGroups(groupedBars, timeframeSeconds, tickIntervalMs)
    .map((group) => buildGroupedChartBar(group))
}

function trimLeadingPartialGroups<T extends { tick: number }>(
  groups: T[][],
  timeframeSeconds: number,
  tickIntervalMs: number,
) {
  if (groups.length <= 1) {
    return groups
  }

  const timeframeMs = Math.max(timeframeSeconds, 1) * 1000
  const safeTickIntervalMs = Math.max(tickIntervalMs, 1)
  const expectedTicksPerBar = Math.round(timeframeMs / safeTickIntervalMs)
  if (expectedTicksPerBar <= 1) {
    return groups
  }

  let firstCompleteIndex = 0
  while (firstCompleteIndex < groups.length - 1 && groups[firstCompleteIndex].length < expectedTicksPerBar) {
    firstCompleteIndex += 1
  }

  return groups.slice(firstCompleteIndex)
}

function buildBackendChartBar(group: OhlcvBar[]): ChartBar {
  const latestWhaleBar = [...group]
    .reverse()
    .find((bar) => bar.whale_side !== null)

  return {
    tickStart: group[0].tick,
    tickEnd: group[group.length - 1].tick,
    open: group[0].open,
    high: Math.max(...group.map((bar) => bar.high)),
    low: Math.min(...group.map((bar) => bar.low)),
    close: group[group.length - 1].close,
    volume: roundChartMetric(group.reduce((sum, bar) => sum + bar.volume, 0)),
    trades: group.reduce((sum, bar) => sum + bar.trades, 0),
    whaleSide: latestWhaleBar?.whale_side ?? null,
    whaleImpactBps: latestWhaleBar?.whale_impact_bps ?? null,
    source: 'backend',
  }
}

function buildGroupedChartBar(group: Array<{ tick: number, price: number }>): ChartBar {
  return {
    tickStart: group[0].tick,
    tickEnd: group[group.length - 1].tick,
    open: group[0].price,
    high: Math.max(...group.map((entry) => entry.price)),
    low: Math.min(...group.map((entry) => entry.price)),
    close: group[group.length - 1].price,
    volume: null,
    trades: null,
    whaleSide: null,
    whaleImpactBps: null,
    source: 'grouped',
  }
}

function getTimeBucketKey(tick: number, timeframeSeconds: number, tickIntervalMs: number) {
  const elapsedMs = Math.max(tick - 1, 0) * Math.max(tickIntervalMs, 1)
  const timeframeMs = Math.max(timeframeSeconds, 1) * 1000

  return Math.floor(elapsedMs / timeframeMs)
}

function formatCurrency(value: number | null) {
  if (value === null) {
    return '--'
  }

  return `$${value.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

function formatSignedCurrency(value: number | null) {
  if (value === null) {
    return '--'
  }

  const normalizedValue = Math.abs(value) < 0.005 ? 0 : value

  const prefix = normalizedValue > 0 ? '+' : ''
  return `${prefix}$${normalizedValue.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

function getPnlClassName(value: number | null) {
  if (value === null || Math.abs(value) < 0.005) {
    return 'position-pill__value'
  }

  return value > 0
    ? 'position-pill__value position-pill__value--positive'
    : 'position-pill__value position-pill__value--negative'
}

function formatTimeframeOptionLabel(timeframe: TimeframeSeconds) {
  if (timeframe >= 60) {
    return `${timeframe / 60} min`
  }

  return `${timeframe}s`
}

function formatGameScore(value: number) {
  return value.toLocaleString('en-US', {
    minimumFractionDigits: Math.abs(value) >= 1000 ? 0 : 2,
    maximumFractionDigits: 2,
  })
}

function formatPercent(value: number) {
  return `${value.toFixed(1)}%`
}

function formatBookNumber(value: number) {
  return value.toLocaleString('en-US', {
    minimumFractionDigits: value >= 100 ? 0 : 2,
    maximumFractionDigits: 2,
  })
}

function getOrderBookBarWidth(quantity: number, bids: Array<{ quantity: number }>, asks: Array<{ quantity: number }>) {
  const maxQuantity = Math.max(...bids.map((level) => level.quantity), ...asks.map((level) => level.quantity), 0)
  if (maxQuantity <= 0) {
    return 0
  }

  return Math.max((quantity / maxQuantity) * 100, 6)
}

function formatQuantity(value: number | null, digits: number) {
  if (value === null) {
    return '--'
  }

  return value.toLocaleString('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

function getReferenceTimeMs(updatedAt?: string) {
  const parsed = updatedAt ? Date.parse(updatedAt) : Number.NaN

  return Number.isNaN(parsed) ? Date.now() : parsed
}

function roundChartMetric(value: number) {
  return Math.round(value * 1_000_000) / 1_000_000
}

export default App
