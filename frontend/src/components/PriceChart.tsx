import type { LiveWhaleOrderOutcome } from '../types/market'

export type ChartMode = 'line' | 'candles'

type CandleDatum = {
  tickStart: number
  tickEnd: number
  open: number
  high: number
  low: number
  close: number
}

type ChartPoint = {
  x: number
  y: number
  tick: number
}

type PriceChartProps = {
  prices: number[]
  currentTick: number
  lastWhaleOrder?: LiveWhaleOrderOutcome | null
  mode?: ChartMode
}

const MAX_VISIBLE_POINTS = 80
const CANDLE_GROUP_SIZE = 4
const SVG_WIDTH = 960
const SVG_HEIGHT = 320
const MIN_CANDLE_BODY_HEIGHT = 3
const CHART_PADDING = {
  top: 24,
  right: 84,
  bottom: 36,
  left: 20,
}

export function PriceChart({
  prices,
  currentTick,
  lastWhaleOrder = null,
  mode = 'candles',
}: PriceChartProps) {
  const visiblePrices = prices.slice(-MAX_VISIBLE_POINTS)

  if (visiblePrices.length < 2) {
    return (
      <div className="price-chart__empty" role="img" aria-label="Grafica pendiente de datos">
        <p className="price-chart__message">
          Esperando suficientes ticks para dibujar la sesion viva. La grafica aparece en cuanto
          entren varias muestras de precio.
        </p>
      </div>
    )
  }

  const startTick = Math.max(currentTick - visiblePrices.length + 1, 0)
  const candles = buildCandles(visiblePrices, startTick, CANDLE_GROUP_SIZE)
  const shouldUseCandles = mode === 'candles' && candles.length >= 2
  const volumeAvailable = false
  const drawableWidth = SVG_WIDTH - CHART_PADDING.left - CHART_PADDING.right
  const drawableHeight = SVG_HEIGHT - CHART_PADDING.top - CHART_PADDING.bottom
  const minPrice = Math.min(...visiblePrices)
  const maxPrice = Math.max(...visiblePrices)
  const rawRange = maxPrice - minPrice
  const rangePadding = rawRange === 0 ? Math.max(maxPrice * 0.0025, 0.15) : rawRange * 0.16
  const chartMin = minPrice - rangePadding
  const chartMax = maxPrice + rangePadding
  const chartRange = Math.max(chartMax - chartMin, 0.0001)
  const baselineY = CHART_PADDING.top + drawableHeight
  const points: ChartPoint[] = visiblePrices.map((price, index) => ({
    x: CHART_PADDING.left + (drawableWidth * index) / Math.max(visiblePrices.length - 1, 1),
    y: toChartY(price, chartMin, chartRange, drawableHeight),
    tick: startTick + index,
  }))
  const polylinePoints = points.map((point) => `${point.x.toFixed(2)},${point.y.toFixed(2)}`).join(' ')
  const areaPath = [
    `M ${points[0].x.toFixed(2)} ${baselineY.toFixed(2)}`,
    `L ${points[0].x.toFixed(2)} ${points[0].y.toFixed(2)}`,
    ...points.slice(1).map((point) => `L ${point.x.toFixed(2)} ${point.y.toFixed(2)}`),
    `L ${points[points.length - 1].x.toFixed(2)} ${baselineY.toFixed(2)}`,
    'Z',
  ].join(' ')
  const lastPoint = points[points.length - 1]
  const lastCandle = candles[candles.length - 1] ?? null
  const currentMarker = shouldUseCandles && lastCandle
    ? {
        x: getCandleCenterX(candles.length - 1, candles.length, drawableWidth),
        y: toChartY(lastCandle.close, chartMin, chartRange, drawableHeight),
      }
    : {
        x: lastPoint.x,
        y: lastPoint.y,
      }
  const currentPriceLabel = `$${visiblePrices[visiblePrices.length - 1].toFixed(2)}`
  const candleWidth = shouldUseCandles ? (drawableWidth / Math.max(candles.length, 1)) * 0.56 : 0
  const eventTone = lastWhaleOrder?.side ?? 'buy'
  const eventPoint = lastWhaleOrder
    ? shouldUseCandles
      ? resolveCandleEventPoint(candles, lastWhaleOrder.tick, drawableWidth, drawableHeight, chartMin, chartRange)
      : points.find((point) => point.tick === lastWhaleOrder.tick) ?? null
    : null
  const eventLabelWidth = 152
  const eventLabelHeight = 42
  const eventLabelX = eventPoint
    ? Math.min(Math.max(eventPoint.x + 12, 16), SVG_WIDTH - eventLabelWidth - 16)
    : 0
  const eventLabelY = eventPoint
    ? Math.max(eventPoint.y - eventLabelHeight - 12, 12)
    : 0
  const impactSummary = lastWhaleOrder
    ? `${lastWhaleOrder.side.toUpperCase()} ${lastWhaleOrder.price_impact_bps >= 0 ? '+' : ''}${lastWhaleOrder.price_impact_bps.toFixed(2)} bps`
    : 'Sin impacto reciente'
  const chartModeSummary = shouldUseCandles
    ? `Velas agrupadas cada ${CANDLE_GROUP_SIZE} muestras`
    : 'Linea simple por muestra'
  const chartStatusSummary = shouldUseCandles
    ? `${candles.length} velas visibles`
    : `${visiblePrices.length} muestras visibles`
  const guideLines = Array.from({ length: 4 }, (_, index) => {
    const ratio = index / 3
    const y = CHART_PADDING.top + drawableHeight * ratio
    const value = chartMax - chartRange * ratio

    return {
      y,
      value,
    }
  })
  const tickLabels = Array.from(
    new Set([startTick, Math.round((startTick + currentTick) / 2), currentTick]),
  ).map((tickValue) => {
    const tickRatio = (tickValue - startTick) / Math.max(visiblePrices.length - 1, 1)

    return {
      tickValue,
      x: CHART_PADDING.left + drawableWidth * tickRatio,
    }
  })

  return (
    <div className="price-chart">
      <div className="price-chart__frame">
        <svg
          className="price-chart__svg"
          viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
          role="img"
          aria-label={shouldUseCandles ? 'Grafica de velas de la sesion viva' : 'Grafica del precio de la sesion viva'}
        >
          <defs>
            <linearGradient id="price-chart-area" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="rgba(140, 226, 212, 0.36)" />
              <stop offset="100%" stopColor="rgba(140, 226, 212, 0.02)" />
            </linearGradient>
          </defs>

          {guideLines.map((guide) => (
            <g key={guide.y}>
              <line
                className="price-chart__grid-line"
                x1={CHART_PADDING.left}
                x2={SVG_WIDTH - CHART_PADDING.right + 6}
                y1={guide.y}
                y2={guide.y}
              />
              <text
                className="price-chart__axis-label"
                textAnchor="end"
                x={SVG_WIDTH - 8}
                y={guide.y - 6}
              >
                ${guide.value.toFixed(2)}
              </text>
            </g>
          ))}

          {shouldUseCandles ? (
            candles.map((candle, index) => {
              const centerX = getCandleCenterX(index, candles.length, drawableWidth)
              const wickTopY = toChartY(candle.high, chartMin, chartRange, drawableHeight)
              const wickBottomY = toChartY(candle.low, chartMin, chartRange, drawableHeight)
              const openY = toChartY(candle.open, chartMin, chartRange, drawableHeight)
              const closeY = toChartY(candle.close, chartMin, chartRange, drawableHeight)
              const rawBodyHeight = Math.abs(openY - closeY)
              const bodyHeight = Math.max(rawBodyHeight, MIN_CANDLE_BODY_HEIGHT)
              const bodyTopY = rawBodyHeight < MIN_CANDLE_BODY_HEIGHT
                ? ((openY + closeY) / 2) - bodyHeight / 2
                : Math.min(openY, closeY)
              const tone = candle.close >= candle.open ? 'buy' : 'sell'
              const isLast = index === candles.length - 1

              return (
                <g key={`${candle.tickStart}-${candle.tickEnd}`}>
                  <line
                    className={`price-chart__wick price-chart__wick--${tone}${isLast ? ' price-chart__wick--last' : ''}`}
                    x1={centerX}
                    x2={centerX}
                    y1={wickTopY}
                    y2={wickBottomY}
                  />
                  <rect
                    className={`price-chart__candle price-chart__candle--${tone}${isLast ? ' price-chart__candle--last' : ''}`}
                    height={bodyHeight}
                    rx="2"
                    width={candleWidth}
                    x={centerX - candleWidth / 2}
                    y={bodyTopY}
                  />
                </g>
              )
            })
          ) : (
            <>
              <path className="price-chart__area" d={areaPath} />
              <polyline className="price-chart__line" points={polylinePoints} />
            </>
          )}

          {eventPoint && lastWhaleOrder ? (
            <>
              <line
                className={`price-chart__event-line price-chart__event-line--${eventTone}`}
                x1={eventPoint.x}
                x2={eventPoint.x}
                y1={CHART_PADDING.top}
                y2={baselineY}
              />
              <circle
                className={`price-chart__event-dot price-chart__event-dot--${eventTone}`}
                cx={eventPoint.x}
                cy={eventPoint.y}
                r="5"
              />
              <g transform={`translate(${eventLabelX}, ${eventLabelY})`}>
                <rect
                  className={`price-chart__event-label price-chart__event-label--${eventTone}`}
                  height={eventLabelHeight}
                  rx="10"
                  width={eventLabelWidth}
                  x="0"
                  y="0"
                />
                <text className="price-chart__event-text" x="12" y="18">
                  {lastWhaleOrder.side.toUpperCase()} {lastWhaleOrder.price_impact_bps >= 0 ? '+' : ''}
                  {lastWhaleOrder.price_impact_bps.toFixed(2)} bps
                </text>
                <text className="price-chart__event-subtext" x="12" y="31">
                  T{lastWhaleOrder.tick} · {lastWhaleOrder.impact_label}
                </text>
              </g>
            </>
          ) : null}

          <circle className="price-chart__last-point" cx={currentMarker.x} cy={currentMarker.y} r="6" />
          <line
            className="price-chart__current-line"
            x1={currentMarker.x}
            x2={SVG_WIDTH - CHART_PADDING.right + 8}
            y1={currentMarker.y}
            y2={currentMarker.y}
          />
          <text className="price-chart__current-price" textAnchor="end" x={SVG_WIDTH - 8} y={currentMarker.y - 7}>
            {currentPriceLabel}
          </text>
          <text className="price-chart__current-tag" textAnchor="end" x={SVG_WIDTH - 8} y={currentMarker.y + 13}>
            actual
          </text>

          {tickLabels.map((label) => (
            <text
              key={label.tickValue}
              className="price-chart__axis-label"
              textAnchor={label.tickValue === startTick ? 'start' : label.tickValue === currentTick ? 'end' : 'middle'}
              x={label.x}
              y={SVG_HEIGHT - 8}
            >
              T{label.tickValue}
            </text>
          ))}
        </svg>
      </div>

      <div className="price-chart__legend">
        <span>
          Ventana visible <strong>T{startTick}</strong> a <strong>T{currentTick}</strong>
        </span>
        <span>
          {chartModeSummary} <strong>{chartStatusSummary}</strong>
        </span>
        <span>
          Ultimo impacto <strong>{impactSummary}</strong>
        </span>
        <span>
          Volumen <strong>{volumeAvailable ? 'real' : 'pendiente'}</strong>
        </span>
      </div>

      {shouldUseCandles && lastCandle ? (
        <div className="price-chart__ohlc-strip">
          <span>
            O <strong>{lastCandle.open.toFixed(2)}</strong>
          </span>
          <span>
            H <strong>{lastCandle.high.toFixed(2)}</strong>
          </span>
          <span>
            L <strong>{lastCandle.low.toFixed(2)}</strong>
          </span>
          <span>
            C <strong>{lastCandle.close.toFixed(2)}</strong>
          </span>
          <span>
            Rango <strong>T{lastCandle.tickStart} a T{lastCandle.tickEnd}</strong>
          </span>
        </div>
      ) : null}
    </div>
  )
}

function buildCandles(prices: number[], startTick: number, groupSize: number): CandleDatum[] {
  const candles: CandleDatum[] = []

  for (let index = 0; index < prices.length; index += groupSize) {
    const group = prices.slice(index, index + groupSize)
    if (group.length < 2) {
      continue
    }

    candles.push({
      tickStart: startTick + index,
      tickEnd: startTick + index + group.length - 1,
      open: group[0],
      high: Math.max(...group),
      low: Math.min(...group),
      close: group[group.length - 1],
    })
  }

  return candles
}

function getCandleCenterX(index: number, candleCount: number, drawableWidth: number) {
  return CHART_PADDING.left + (drawableWidth * (index + 0.5)) / Math.max(candleCount, 1)
}

function toChartY(price: number, chartMin: number, chartRange: number, drawableHeight: number) {
  return CHART_PADDING.top + drawableHeight - ((price - chartMin) / chartRange) * drawableHeight
}

function resolveCandleEventPoint(
  candles: CandleDatum[],
  tick: number,
  drawableWidth: number,
  drawableHeight: number,
  chartMin: number,
  chartRange: number,
) {
  const candleIndex = candles.findIndex((candle) => tick >= candle.tickStart && tick <= candle.tickEnd)
  if (candleIndex === -1) {
    return null
  }

  const candle = candles[candleIndex]

  return {
    x: getCandleCenterX(candleIndex, candles.length, drawableWidth),
    y: toChartY(candle.close, chartMin, chartRange, drawableHeight),
  }
}