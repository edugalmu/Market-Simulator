import type {
  HealthResponse,
  LiveSimulationSnapshot,
  LiveWhaleOrderResponse,
  SimulationSummary,
  WhaleShockPreview,
} from '../types/market'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'

async function fetchJson<T>(
  path: string,
  signal?: AbortSignal,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    signal,
    ...init,
  })

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`)
  }

  return (await response.json()) as T
}

export const marketApi = {
  getHealth(signal?: AbortSignal) {
    return fetchJson<HealthResponse>('/health', signal)
  },
  getBootstrap(signal?: AbortSignal) {
    return fetchJson<SimulationSummary>('/simulation/bootstrap', signal)
  },
  getWhaleShockPreview(signal?: AbortSignal) {
    return fetchJson<WhaleShockPreview>(
      '/simulation/whale-shock/preview?side=sell&notional=3000',
      signal,
    )
  },
  getLiveSimulation(signal?: AbortSignal) {
    return fetchJson<LiveSimulationSnapshot>('/simulation/live', signal)
  },
  startLiveSimulation(tickIntervalMs = 750, signal?: AbortSignal) {
    return fetchJson<LiveSimulationSnapshot>(
      `/simulation/live/start?tick_interval_ms=${tickIntervalMs}`,
      signal,
      { method: 'POST' },
    )
  },
  stopLiveSimulation(signal?: AbortSignal) {
    return fetchJson<LiveSimulationSnapshot>('/simulation/live/stop', signal, {
      method: 'POST',
    })
  },
  playLiveSimulation(tickIntervalMs?: number, signal?: AbortSignal) {
    const intervalQuery = tickIntervalMs === undefined ? '' : `?tick_interval_ms=${tickIntervalMs}`

    return fetchJson<LiveSimulationSnapshot>(
      `/simulation/live/play${intervalQuery}`,
      signal,
      { method: 'POST' },
    )
  },
  stepLiveSimulation(ticks = 1, signal?: AbortSignal) {
    return fetchJson<LiveSimulationSnapshot>(
      `/simulation/live/step?ticks=${ticks}`,
      signal,
      { method: 'POST' },
    )
  },
  executeLiveWhaleOrder(
    side: 'buy' | 'sell',
    notional: number,
    signal?: AbortSignal,
  ) {
    return fetchJson<LiveWhaleOrderResponse>(
      '/simulation/live/whale-order',
      signal,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ side, notional }),
      },
    )
  },
}
