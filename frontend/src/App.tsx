import { useState } from 'react'

import { MetricCard } from './components/MetricCard'
import { PriceChart } from './components/PriceChart'
import { SectionCard } from './components/SectionCard'
import { useDashboardData } from './hooks/useDashboardData'
import './App.css'

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
    stopLiveSession,
    stepLiveSession,
    executeWhaleOrder,
  } = useDashboardData()
  const [whaleNotionalInput, setWhaleNotionalInput] = useState('3000')

  const whalePresets = [1000, 3000, 10000, 25000]
  const whaleNotional = Number.parseFloat(whaleNotionalInput.replace(',', '.'))
  const hasValidWhaleNotional = Number.isFinite(whaleNotional) && whaleNotional > 0
  const whaleActionDisabled =
    actionLoading ||
    !liveSession ||
    liveSession.status !== 'running' ||
    !hasValidWhaleNotional
  const lastWhaleOrder = liveSession?.last_whale_order ?? null
  const whaleBalance = liveSession?.whale_balance ?? null
  const chartPrices = (liveSession?.recent_mid_prices ?? []).slice(-80)
  const latestChartPrices = chartPrices.slice(-8)
  const lastImpactSummary = lastWhaleOrder
    ? `${lastWhaleOrder.side.toUpperCase()} ${lastWhaleOrder.price_impact_bps >= 0 ? '+' : ''}${lastWhaleOrder.price_impact_bps.toFixed(2)} bps`
    : 'Sin orden'

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

  return (
    <main className="app-shell">
      <section className="hero-panel">
        <div className="hero-panel__copy">
          <p className="eyebrow">Market Simulator · Scaffold local-first</p>
          <h1>Motor de simulacion separado. Simulacion viva minima ya en marcha.</h1>
          <p className="hero-panel__body">
            La app ya puede abrir una sesion viva en memoria, avanzar por ticks y
            activar subconjuntos de agentes simples que barren liquidez sintetica
            del libro para mover precio, spread y metricas en tiempo real.
          </p>
        </div>

        <div className="hero-panel__status">
          <span className="status-pill">{loading ? 'Cargando backend' : liveStatus}</span>
          <span className="status-pill status-pill--accent">
            {health?.gpu_enabled ? 'GPU habilitada' : 'CPU por defecto'}
          </span>
          {liveSession ? <span className="status-pill">Tick {liveSession.tick}</span> : null}
        </div>

        <div className="control-row">
          <button className="control-button" onClick={() => void startLiveSession()} disabled={actionLoading}>
            {liveSession ? 'Reiniciar simulacion' : 'Iniciar simulacion'}
          </button>
          <button
            className="control-button control-button--secondary"
            onClick={() => void stopLiveSession()}
            disabled={actionLoading || !liveSession || liveSession.status !== 'running'}
          >
            Detener
          </button>
          <button
            className="control-button control-button--ghost"
            onClick={() => void stepLiveSession(5)}
            disabled={actionLoading || !liveSession}
          >
            Avanzar 5 ticks
          </button>
        </div>
      </section>

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

      {error ? <p className="banner banner--warning">{error}</p> : null}
      {liveError ? <p className="banner banner--warning">{liveError}</p> : null}

      <section className="content-grid">
        <div className="market-focus-card">
          <SectionCard
            title="Mercado en vivo"
            eyebrow="Grafica principal"
            aside={<span className="micro-tag">{chartPrices.length > 0 ? `${chartPrices.length} muestras` : 'sin muestras'}</span>}
          >
            <div className="chart-summary-grid">
              <MetricCard
                label="Precio actual"
                value={liveSession ? `$${liveSession.order_book.mid_price.toFixed(2)}` : '--'}
                tone="accent"
              />
              <MetricCard
                label="Tick"
                value={liveSession ? `T${liveSession.tick}` : '--'}
              />
              <MetricCard
                label="Ultimo impacto"
                value={lastImpactSummary}
              />
              <MetricCard
                label="Spread"
                value={liveSession ? `${liveSession.order_book.spread_bps.toFixed(2)} bps` : '--'}
              />
            </div>

            <PriceChart
              prices={chartPrices}
              currentTick={liveSession?.tick ?? 0}
              lastWhaleOrder={lastWhaleOrder}
              mode="candles"
            />

            {latestChartPrices.length > 0 ? (
              <div className="price-strip price-strip--chart">
                {latestChartPrices.map((price, index) => {
                  const fullIndex = chartPrices.length - latestChartPrices.length + index
                  const tickLabel = Math.max(
                    (liveSession?.tick ?? 0) - (chartPrices.length - 1 - fullIndex),
                    0,
                  )
                  const impactTick = lastWhaleOrder?.tick === tickLabel
                  const isCurrent = tickLabel === (liveSession?.tick ?? -1)
                  const chipClassName = [
                    'price-chip',
                    isCurrent ? 'price-chip--current' : '',
                    impactTick ? `price-chip--${lastWhaleOrder?.side ?? 'impact'}` : '',
                  ]
                    .filter(Boolean)
                    .join(' ')

                  return (
                    <div className={chipClassName} key={`${price}-${tickLabel}`}>
                      <span>T{tickLabel}</span>
                      <strong>${price.toFixed(2)}</strong>
                    </div>
                  )
                })}
              </div>
            ) : null}

            <p className="section-note">
              La grafica agrupa el `mid-price` vivo en bloques para construir velas simples con
              apertura, maximo, minimo y cierre. El volumen real por barra todavia no viene del
              backend, asi que esta primera version prioriza la lectura visual del movimiento.
            </p>
          </SectionCard>
        </div>

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
          title="Control de ballena"
          eyebrow="Modo jugable"
          aside={<span className={whaleImpactTone}>{lastWhaleOrder?.impact_label ?? 'SIN IMPACTO'}</span>}
        >
          <div className="notional-row">
            {whalePresets.map((preset) => {
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
          <label className="input-stack">
            <span>Notional manual</span>
            <input
              className="control-input"
              type="number"
              min="1"
              step="100"
              value={whaleNotionalInput}
              onChange={(event) => setWhaleNotionalInput(event.target.value)}
            />
          </label>
          <div className="control-row">
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
          <p className="section-note">
            Estas ordenes actuan sobre el libro vivo actual. El backend devuelve el fill, el impacto
            y el balance actualizado de la ballena; la UI solo lo representa.
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
      </section>
    </main>
  )
}

export default App
