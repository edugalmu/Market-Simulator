export type ChartMode = 'line' | 'candles'

export type ChartBar = {
  tickStart: number
  tickEnd: number
  open: number
  high: number
  low: number
  close: number
  volume: number | null
  trades: number | null
  whaleSide: 'buy' | 'sell' | null
  whaleImpactBps: number | null
  source: 'backend' | 'grouped'
}

type CandleDatum = {
  tickStart: number
  tickEnd: number
  open: number
  high: number
  low: number
  close: number
  volume: number | null
  trades: number | null
  whaleSide: 'buy' | 'sell' | null
  whaleImpactBps: number | null
  source: 'backend' | 'grouped'
}

type ChartPoint = {
  x: number
  y: number
  tick: number
}

type AxisAnchor = 'start' | 'middle' | 'end'

type PriceChartProps = {
  prices: number[]
  bars?: ChartBar[]
  currentTick: number
  mode?: ChartMode
  tickIntervalMs?: number
  referenceTimeMs?: number
}

const MAX_VISIBLE_POINTS = 620
const SVG_WIDTH = 960
const SVG_HEIGHT = 392
const MIN_CANDLE_BODY_HEIGHT = 3
const VOLUME_HEIGHT = 66
const VOLUME_GAP = 14
const CHART_PADDING = {
  top: 24,
  right: 104,
  bottom: 34,
  left: 20,
}

export function PriceChart({
  prices,
  bars = [],
  currentTick,
  mode = 'candles',
  tickIntervalMs = 750,
  referenceTimeMs = 0,
}: PriceChartProps) {
  const visiblePrices = prices.slice(-MAX_VISIBLE_POINTS)
  const visibleBars = bars.slice(-MAX_VISIBLE_POINTS)
  const hasChartBars = visibleBars.length > 0
  const fallbackStartTick = Math.max(currentTick - visiblePrices.length + 1, 0)
  const fallbackCandles = buildCandles(visiblePrices, fallbackStartTick, 1)
  const candles = hasChartBars
    ? visibleBars.map((bar) => ({
        tickStart: bar.tickStart,
        tickEnd: bar.tickEnd,
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
        volume: bar.volume,
        trades: bar.trades,
        whaleSide: bar.whaleSide,
        whaleImpactBps: bar.whaleImpactBps,
        source: bar.source,
      }))
    : fallbackCandles
  const hasFallbackLine = visiblePrices.length >= 2

  if (!hasChartBars && !hasFallbackLine) {
    return (
      <div className="price-chart__empty" role="img" aria-label="Grafica pendiente de datos">
        <p className="price-chart__message">
          Esperando suficientes ticks para dibujar la sesion viva. La grafica aparece en cuanto
          entren varias muestras de precio.
        </p>
      </div>
    )
  }

  const shouldUseCandles = mode === 'candles' && candles.length >= 2
  const drawableWidth = SVG_WIDTH - CHART_PADDING.left - CHART_PADDING.right
  const drawableHeight = SVG_HEIGHT - CHART_PADDING.top - CHART_PADDING.bottom
  const priceDrawableHeight = drawableHeight - VOLUME_HEIGHT - VOLUME_GAP
  const volumeTopY = CHART_PADDING.top + priceDrawableHeight + VOLUME_GAP
  const volumeBaseY = volumeTopY + VOLUME_HEIGHT
  const priceSamples = shouldUseCandles
    ? candles.flatMap((candle) => [candle.open, candle.high, candle.low, candle.close])
    : visiblePrices
  const minPrice = Math.min(...priceSamples)
  const maxPrice = Math.max(...priceSamples)
  const rawRange = maxPrice - minPrice
  const rangePadding = rawRange === 0 ? Math.max(maxPrice * 0.0025, 0.15) : rawRange * 0.16
  const chartMin = minPrice - rangePadding
  const chartMax = maxPrice + rangePadding
  const chartRange = Math.max(chartMax - chartMin, 0.0001)
  const baselineY = CHART_PADDING.top + priceDrawableHeight
  const points: ChartPoint[] = visiblePrices.map((price, index) => ({
    x: CHART_PADDING.left + (drawableWidth * index) / Math.max(visiblePrices.length - 1, 1),
    y: toChartY(price, chartMin, chartRange, priceDrawableHeight),
    tick: fallbackStartTick + index,
  }))
  const polylinePoints = points.map((point) => `${point.x.toFixed(2)},${point.y.toFixed(2)}`).join(' ')
  const areaPath = points.length >= 2
    ? [
        `M ${points[0].x.toFixed(2)} ${baselineY.toFixed(2)}`,
        `L ${points[0].x.toFixed(2)} ${points[0].y.toFixed(2)}`,
        ...points.slice(1).map((point) => `L ${point.x.toFixed(2)} ${point.y.toFixed(2)}`),
        `L ${points[points.length - 1].x.toFixed(2)} ${baselineY.toFixed(2)}`,
        'Z',
      ].join(' ')
    : ''
  const fallbackCurrentPrice = visiblePrices[visiblePrices.length - 1] ?? 0
  const lastPoint = points[points.length - 1] ?? {
    x: CHART_PADDING.left,
    y: toChartY(fallbackCurrentPrice, chartMin, chartRange, priceDrawableHeight),
    tick: currentTick,
  }
  const lastCandle = candles[candles.length - 1] ?? null
  const currentMarker = (mode === 'candles' && lastCandle)
    ? {
        x: getCandleCenterX(candles.length - 1, candles.length, drawableWidth),
        y: toChartY(lastCandle.close, chartMin, chartRange, priceDrawableHeight),
      }
    : {
        x: lastPoint.x,
        y: lastPoint.y,
      }
  const currentPriceValue = lastCandle ? lastCandle.close : fallbackCurrentPrice
  const currentPriceLabel = `$${currentPriceValue.toFixed(2)}`
  const candleWidth = shouldUseCandles ? (drawableWidth / Math.max(candles.length, 1)) * 0.56 : 0
  const volumeBars = buildVolumeBars(candles, drawableWidth, candleWidth, volumeTopY, volumeBaseY)
  const guideLines = Array.from({ length: 4 }, (_, index) => {
    const ratio = index / 3
    const y = CHART_PADDING.top + priceDrawableHeight * ratio
    const value = chartMax - chartRange * ratio

    return {
      y,
      value,
    }
  })
  const tickLabels = candles.length > 0
    ? buildCandleTimeLabels(candles, drawableWidth, currentTick, tickIntervalMs, referenceTimeMs)
    : Array.from(
        new Set([fallbackStartTick, Math.round((fallbackStartTick + currentTick) / 2), currentTick]),
      ).map((tickValue) => {
        const tickRatio = (tickValue - fallbackStartTick) / Math.max(visiblePrices.length - 1, 1)

        return {
          tickValue: formatTickClock(tickValue, currentTick, tickIntervalMs, referenceTimeMs),
          x: CHART_PADDING.left + drawableWidth * tickRatio,
          textAnchor: (tickValue === fallbackStartTick ? 'start' : tickValue === currentTick ? 'end' : 'middle') as AxisAnchor,
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
              const wickTopY = toChartY(candle.high, chartMin, chartRange, priceDrawableHeight)
              const wickBottomY = toChartY(candle.low, chartMin, chartRange, priceDrawableHeight)
              const openY = toChartY(candle.open, chartMin, chartRange, priceDrawableHeight)
              const closeY = toChartY(candle.close, chartMin, chartRange, priceDrawableHeight)
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

          {volumeBars.length > 0 ? (
            <>
              <line
                className="price-chart__volume-baseline"
                x1={CHART_PADDING.left}
                x2={SVG_WIDTH - CHART_PADDING.right + 6}
                y1={volumeBaseY}
                y2={volumeBaseY}
              />
              {volumeBars.map((bar) => (
                <rect
                  key={`${bar.tickStart}-${bar.tickEnd}`}
                  className={`price-chart__volume-bar price-chart__volume-bar--${bar.tone}`}
                  height={bar.height}
                  rx="2"
                  width={bar.width}
                  x={bar.x}
                  y={bar.y}
                />
              ))}
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
              textAnchor={label.textAnchor}
              x={label.x}
              y={SVG_HEIGHT - 8}
            >
              {label.tickValue}
            </text>
          ))}
        </svg>
      </div>

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
      volume: null,
      trades: null,
      whaleSide: null,
      whaleImpactBps: null,
      source: 'grouped',
    })
  }

  return candles
}

function buildCandleTimeLabels(
  candles: CandleDatum[],
  drawableWidth: number,
  currentTick: number,
  tickIntervalMs: number,
  referenceTimeMs: number,
) {
  const candidateIndices = [0, Math.floor((candles.length - 1) / 2), candles.length - 1]
  const seenTimes = new Set<string>()

  return candidateIndices.flatMap((index) => {
    const candle = candles[index]
    if (!candle) {
      return []
    }

    const timeLabel = formatTickClock(candle.tickEnd, currentTick, tickIntervalMs, referenceTimeMs)
    if (seenTimes.has(timeLabel)) {
      return []
    }

    seenTimes.add(timeLabel)
    return {
      tickValue: timeLabel,
      x: getCandleCenterX(index, candles.length, drawableWidth),
      textAnchor: (index === 0 ? 'start' : index === candles.length - 1 ? 'end' : 'middle') as AxisAnchor,
    }
  })
}

function getCandleCenterX(index: number, candleCount: number, drawableWidth: number) {
  return CHART_PADDING.left + (drawableWidth * (index + 0.5)) / Math.max(candleCount, 1)
}

function toChartY(price: number, chartMin: number, chartRange: number, drawableHeight: number) {
  return CHART_PADDING.top + drawableHeight - ((price - chartMin) / chartRange) * drawableHeight
}

function buildVolumeBars(
  candles: CandleDatum[],
  drawableWidth: number,
  candleWidth: number,
  volumeTopY: number,
  volumeBaseY: number,
) {
  const volumes = candles.map((candle) => candle.volume ?? 0)
  const maxVolume = Math.max(...volumes, 0)
  if (maxVolume <= 0) {
    return []
  }

  return candles.map((candle, index) => {
    const centerX = getCandleCenterX(index, candles.length, drawableWidth)
    const height = Math.max(((candle.volume ?? 0) / maxVolume) * (volumeBaseY - volumeTopY), 2)
    const tone = candle.close >= candle.open ? 'buy' : 'sell'
    const width = Math.max(candleWidth, 6)

    return {
      tickStart: candle.tickStart,
      tickEnd: candle.tickEnd,
      x: centerX - width / 2,
      y: volumeBaseY - height,
      width,
      height,
      tone,
    }
  })
}

function formatTickClock(tick: number, currentTick: number, tickIntervalMs: number, referenceTimeMs: number) {
  const tickDistance = Math.max(currentTick - tick, 0)
  const tickTimeMs = referenceTimeMs - tickDistance * Math.max(tickIntervalMs, 1)

  return new Intl.DateTimeFormat('es-ES', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(tickTimeMs))
}

