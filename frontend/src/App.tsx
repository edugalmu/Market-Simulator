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
const WHALE_INITIAL_CASH = 250_000
const WHALE_INITIAL_ASSET = 5_000
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
    loading,
    liveLoading,
    actionLoading,
    error,
    liveError,
    health,
    summary,
    whalePreview,
    liveSession,
    startLiveSession,
    playLiveSession,
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
  const tickIntervalMs = liveSession?.tick_interval_ms ?? configuredTickIntervalMs
  const referenceTimeMs = getReferenceTimeMs(liveSession?.updated_at)
  const visibleBarCount = VISIBLE_BAR_TARGETS[selectedTimeframe]
  const visiblePriceSampleCount = Math.ceil((PRELOADED_WINDOW_SECONDS * 1000) / tickIntervalMs) + 1
  const chartPrices = (liveSession?.recent_mid_prices ?? []).slice(-visiblePriceSampleCount)
  const chartBars = aggregateOhlcvBars(rawOhlcvHistory, selectedTimeframe, tickIntervalMs).slice(-visibleBarCount)
  const fallbackBars = buildGroupedPriceBars(chartPrices, liveSession?.tick ?? 0, selectedTimeframe, tickIntervalMs).slice(-visibleBarCount)
  const activeChartBars = chartBars.length > 0 ? chartBars : fallbackBars
  const whaleCashTotal = whaleBalance ? whaleBalance.cash_free + whaleBalance.cash_reserved : null
  const whaleTokenTotal = whaleBalance ? whaleBalance.asset_free + whaleBalance.asset_reserved : null
  const initialPrice = liveSession?.config.initial_price ?? summary?.config.initial_price ?? 100
  const initialWhaleEquity = WHALE_INITIAL_CASH + WHALE_INITIAL_ASSET * initialPrice
  const estimatedPnl = whaleBalance
    ? whaleBalance.total_equity - initialWhaleEquity
    : null
  const executedPnl = whaleBalance && whaleCashTotal !== null && whaleTokenTotal !== null
    ? whaleCashTotal + whaleTokenTotal * initialPrice - initialWhaleEquity
    : null

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

  const liveStatus = liveSession?.status === 'running'
    ? 'Simulacion en marcha'
    : liveSession?.status === 'stopped'
      ? 'Simulacion detenida'
      : liveLoading
        ? 'Iniciando simulacion'
        : 'Sin sesion viva'

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

  return (
    <main className="app-shell">
      <section className="hero-panel">
        <div className="hero-spotlight">
          <div className="hero-spotlight__header">
            <p className="eyebrow">Mercado en vivo</p>
            <div className="hero-spotlight__badges">
              <span className="status-pill">{loading ? 'Cargando backend' : liveStatus}</span>
              <span className="status-pill status-pill--accent">
                {health?.gpu_enabled ? 'GPU habilitada' : 'CPU por defecto'}
              </span>
            </div>
          </div>

          <div className="hero-highlights hero-highlights--compact hero-highlights--minimal">
            <div className="hero-stat">
              <span>Precio</span>
              <strong>{liveSession ? `$${liveSession.order_book.mid_price.toFixed(2)}` : '--'}</strong>
            </div>
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

                <div className="simulation-box__footer">
                  <button
                    className={`mode-toggle${isDevMode ? ' mode-toggle--active' : ''}`}
                    onClick={() => setIsDevMode((current) => !current)}
                    type="button"
                  >
                    Modo DEV
                  </button>

                  {isDevMode ? (
                    <button
                      className="control-button control-button--step"
                      onClick={() => void stepLiveSession(5)}
                      disabled={actionLoading || !liveSession}
                    >
                      Avanzar 5 ticks
                    </button>
                  ) : null}
                </div>
              </div>

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
                      {preset.toLocaleString('es-ES')}
                    </button>
                  )
                })}
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
          </div>

          <PriceChart
            prices={chartPrices}
            bars={activeChartBars}
            currentTick={liveSession?.tick ?? 0}
            mode="candles"
            tickIntervalMs={tickIntervalMs}
            referenceTimeMs={referenceTimeMs}
          />
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
            value={(liveSession?.config.agent_count ?? summary?.config.agent_count ?? 1000).toLocaleString('es-ES')}
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
                  ? whalePreview.order_book_before.bid_depth.toLocaleString('es-ES', {
                      maximumFractionDigits: 4,
                    })
                  : '--'}
              </strong>
            </div>
            <div className="mix-row">
              <span>Bid depth despues</span>
              <strong>
                {whalePreview
                  ? whalePreview.order_book_after.bid_depth.toLocaleString('es-ES', {
                      maximumFractionDigits: 4,
                    })
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
              value={whaleBalance ? `$${whaleBalance.cash_free.toFixed(2)}` : '--'}
            />
            <MetricCard
              label="Cash reservado"
              value={whaleBalance ? `$${whaleBalance.cash_reserved.toFixed(2)}` : '--'}
            />
            <MetricCard
              label="Asset libre"
              value={whaleBalance ? whaleBalance.asset_free.toFixed(4) : '--'}
            />
            <MetricCard
              label="Asset reservado"
              value={whaleBalance ? whaleBalance.asset_reserved.toFixed(4) : '--'}
            />
            <MetricCard
              label="Equity"
              value={whaleBalance ? `$${whaleBalance.total_equity.toFixed(2)}` : '--'}
              tone="accent"
            />
          </div>
        </SectionCard>

        <SectionCard title="Mix inicial de agentes" eyebrow="Modelo operativo">
          <div className="mix-table">
            {(liveSession?.agent_mix ?? summary?.agent_mix ?? []).map((entry) => (
              <div className="mix-row" key={entry.strategy}>
                <span>{entry.strategy.replace('_', ' ')}</span>
                <strong>{entry.count.toLocaleString('es-ES')}</strong>
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

  const aggregated: ChartBar[] = []
  let currentBucketKey: number | null = null
  let currentGroup: OhlcvBar[] = []

  bars.forEach((bar) => {
    const bucketKey = getTimeBucketKey(bar.tick, timeframeSeconds, tickIntervalMs)

    if (currentBucketKey === null || bucketKey === currentBucketKey) {
      currentBucketKey = bucketKey
      currentGroup.push(bar)
      return
    }

    aggregated.push(buildBackendChartBar(currentGroup))
    currentBucketKey = bucketKey
    currentGroup = [bar]
  })

  if (currentGroup.length > 0) {
    aggregated.push(buildBackendChartBar(currentGroup))
  }

  return aggregated
}

function buildGroupedPriceBars(prices: number[], currentTick: number, timeframeSeconds: number, tickIntervalMs: number): ChartBar[] {
  if (prices.length === 0) {
    return []
  }

  const startTick = Math.max(currentTick - prices.length + 1, 0)
  const groupedBars: ChartBar[] = []
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

    groupedBars.push(buildGroupedChartBar(currentGroup))
    currentBucketKey = bucketKey
    currentGroup = [{ tick, price }]
  })

  if (currentGroup.length > 0) {
    groupedBars.push(buildGroupedChartBar(currentGroup))
  }

  return groupedBars
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

  return `$${value.toFixed(2)}`
}

function formatSignedCurrency(value: number | null) {
  if (value === null) {
    return '--'
  }

  const prefix = value > 0 ? '+' : ''
  return `${prefix}$${value.toFixed(2)}`
}

function getPnlClassName(value: number | null) {
  if (value === null || value === 0) {
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

function formatQuantity(value: number | null, digits: number) {
  if (value === null) {
    return '--'
  }

  return value.toFixed(digits)
}

function getReferenceTimeMs(updatedAt?: string) {
  const parsed = updatedAt ? Date.parse(updatedAt) : Number.NaN

  return Number.isNaN(parsed) ? Date.now() : parsed
}

function roundChartMetric(value: number) {
  return Math.round(value * 1_000_000) / 1_000_000
}

export default App
