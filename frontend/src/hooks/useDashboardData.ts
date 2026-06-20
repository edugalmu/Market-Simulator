import { useCallback, useEffect, useRef, useState } from 'react'

import { marketApi } from '../api/client'
import type {
  HealthResponse,
  LiveSimulationSnapshot,
  SimulationSummary,
  WhaleShockPreview,
} from '../types/market'

type DashboardState = {
  loading: boolean
  liveLoading: boolean
  actionLoading: boolean
  error: string | null
  liveError: string | null
  health: HealthResponse | null
  summary: SimulationSummary | null
  whalePreview: WhaleShockPreview | null
  liveSession: LiveSimulationSnapshot | null
}

const initialState: DashboardState = {
  loading: true,
  liveLoading: true,
  actionLoading: false,
  error: null,
  liveError: null,
  health: null,
  summary: null,
  whalePreview: null,
  liveSession: null,
}

export function useDashboardData() {
  const [state, setState] = useState<DashboardState>(initialState)
  const pollerRef = useRef<number | null>(null)
  const pollIntervalRef = useRef<number | null>(null)

  const stopPolling = useCallback(() => {
    if (pollerRef.current !== null) {
      window.clearInterval(pollerRef.current)
      pollerRef.current = null
    }

    pollIntervalRef.current = null
  }, [])

  const startPolling = useCallback((intervalMs = 1000) => {
    const nextIntervalMs = Math.max(intervalMs, 150)

    if (pollerRef.current !== null && pollIntervalRef.current === nextIntervalMs) {
      return
    }

    stopPolling()

    pollerRef.current = window.setInterval(() => {
      marketApi
        .getLiveSimulation()
        .then((nextSession) => {
          if (nextSession.status === 'running') {
            startPolling(nextSession.tick_interval_ms)
          } else {
            stopPolling()
          }

          setState((current) => ({
            ...current,
            liveLoading: false,
            liveError: null,
            liveSession: nextSession,
          }))
        })
        .catch((error: unknown) => {
          const message = error instanceof Error ? error.message : 'Unexpected error'
          setState((current) => ({
            ...current,
            liveLoading: false,
            liveError: message,
          }))
        })
    }, nextIntervalMs)
    pollIntervalRef.current = nextIntervalMs
  }, [stopPolling])

  useEffect(() => {
    const abortController = new AbortController()

    async function syncLiveSession(signal?: AbortSignal) {
      try {
        const liveSession = await marketApi.getLiveSimulation(signal)
        if (signal?.aborted) {
          return
        }

        setState((current) => ({
          ...current,
          liveLoading: false,
          liveError: null,
          liveSession,
        }))

        if (liveSession.status === 'running') {
          startPolling(liveSession.tick_interval_ms)
        }

        if (liveSession.status !== 'running') {
          stopPolling()
        }
      } catch (error: unknown) {
        stopPolling()
        const message = error instanceof Error ? error.message : 'Unexpected error'
        if ((error as { message?: string }).message?.includes('404')) {
          setState((current) => ({
            ...current,
            liveLoading: false,
            liveError: null,
            liveSession: null,
          }))
          return
        }

        setState((current) => ({
          ...current,
          liveLoading: false,
          liveError: message,
        }))
      }
    }

    async function startLiveSessionForInterval(tickIntervalMs: number, signal?: AbortSignal) {
      setState((current) => ({
        ...current,
        liveLoading: true,
        actionLoading: true,
        liveError: null,
      }))

      try {
        const liveSession = await marketApi.startLiveSimulation(tickIntervalMs, signal)
        if (signal?.aborted) {
          return
        }

        stopPolling()
        setState((current) => ({
          ...current,
          liveLoading: false,
          actionLoading: false,
          liveError: null,
          liveSession,
        }))
        await syncLiveSession(signal)
      } catch (error: unknown) {
        if (signal?.aborted) {
          return
        }

        setState((current) => ({
          ...current,
          liveLoading: false,
          actionLoading: false,
          liveError:
            error instanceof Error ? error.message : 'No se pudo iniciar la simulacion en vivo.',
        }))
      }
    }

    async function load() {
      setState(initialState)

      const [healthResult, summaryResult, whalePreviewResult] = await Promise.allSettled([
        marketApi.getHealth(abortController.signal),
        marketApi.getBootstrap(abortController.signal),
        marketApi.getWhaleShockPreview(abortController.signal),
      ])

      if (abortController.signal.aborted) {
        return
      }

      const health =
        healthResult.status === 'fulfilled' ? healthResult.value : null
      const summary =
        summaryResult.status === 'fulfilled' ? summaryResult.value : null
      const whalePreview =
        whalePreviewResult.status === 'fulfilled' ? whalePreviewResult.value : null

      const failures = [healthResult, summaryResult, whalePreviewResult].filter(
        (result) => result.status === 'rejected',
      )

      setState({
        loading: false,
        liveLoading: true,
        actionLoading: false,
        error:
          failures.length > 0
            ? 'Backend no disponible todavia. El frontend sigue listo para conectarse en cuanto arranque la API.'
            : null,
        liveError: null,
        health,
        summary,
        whalePreview,
        liveSession: null,
      })

      if (failures.length === 0) {
        await syncLiveSession(abortController.signal)
        setState((current) => current.liveSession || current.liveError
          ? current
          : {
              ...current,
              liveLoading: false,
            })

        if (!abortController.signal.aborted) {
          const snapshot = await marketApi.getLiveSimulation(abortController.signal).catch(() => null)
          if (!snapshot) {
            await startLiveSessionForInterval(750, abortController.signal)
          }
        }
      }
    }

    load().catch((error: unknown) => {
      if (abortController.signal.aborted) {
        return
      }

      setState({
        loading: false,
        error: error instanceof Error ? error.message : 'Unexpected error',
        liveLoading: false,
        actionLoading: false,
        liveError: null,
        health: null,
        summary: null,
        whalePreview: null,
        liveSession: null,
      })
    })

    return () => {
      stopPolling()
      abortController.abort()
    }
  }, [startPolling, stopPolling])

  async function startLiveSession(tickIntervalMs = 750) {
    setState((current) => ({
      ...current,
      actionLoading: true,
      liveError: null,
    }))

    try {
      const liveSession = await marketApi.startLiveSimulation(tickIntervalMs)
      stopPolling()
      startPolling(liveSession.tick_interval_ms)

      setState((current) => ({
        ...current,
        actionLoading: false,
        liveLoading: false,
        liveError: null,
        liveSession,
      }))
    } catch (error: unknown) {
      setState((current) => ({
        ...current,
        actionLoading: false,
        liveError:
          error instanceof Error ? error.message : 'No se pudo reiniciar la simulacion.',
      }))
    }
  }

  async function stopLiveSession() {
    setState((current) => ({
      ...current,
      actionLoading: true,
      liveError: null,
    }))

    try {
      const liveSession = await marketApi.stopLiveSimulation()
      stopPolling()

      setState((current) => ({
        ...current,
        actionLoading: false,
        liveLoading: false,
        liveError: null,
        liveSession,
      }))
    } catch (error: unknown) {
      setState((current) => ({
        ...current,
        actionLoading: false,
        liveError:
          error instanceof Error ? error.message : 'No se pudo detener la simulacion.',
      }))
    }
  }

  async function playLiveSession(tickIntervalMs?: number) {
    setState((current) => ({
      ...current,
      actionLoading: true,
      liveError: null,
    }))

    try {
      const liveSession = await marketApi.playLiveSimulation(tickIntervalMs)
      stopPolling()
      startPolling(liveSession.tick_interval_ms)

      setState((current) => ({
        ...current,
        actionLoading: false,
        liveLoading: false,
        liveError: null,
        liveSession,
      }))
    } catch (error: unknown) {
      setState((current) => ({
        ...current,
        actionLoading: false,
        liveError:
          error instanceof Error ? error.message : 'No se pudo reanudar la simulacion.',
      }))
    }
  }

  async function stepLiveSession(ticks = 1) {
    setState((current) => ({
      ...current,
      actionLoading: true,
      liveError: null,
    }))

    try {
      const liveSession = await marketApi.stepLiveSimulation(ticks)
      setState((current) => ({
        ...current,
        actionLoading: false,
        liveLoading: false,
        liveError: null,
        liveSession,
      }))
    } catch (error: unknown) {
      setState((current) => ({
        ...current,
        actionLoading: false,
        liveError:
          error instanceof Error ? error.message : 'No se pudo avanzar la simulacion.',
      }))
    }
  }

  async function executeWhaleOrder(side: 'buy' | 'sell', notional: number) {
    setState((current) => ({
      ...current,
      actionLoading: true,
      liveError: null,
    }))

    try {
      const response = await marketApi.executeLiveWhaleOrder(side, notional)
      setState((current) => ({
        ...current,
        actionLoading: false,
        liveLoading: false,
        liveError: null,
        liveSession: response.snapshot,
      }))
    } catch (error: unknown) {
      setState((current) => ({
        ...current,
        actionLoading: false,
        liveError:
          error instanceof Error ? error.message : 'No se pudo ejecutar la orden de ballena.',
      }))
    }
  }

  return {
    ...state,
    startLiveSession,
    playLiveSession,
    stopLiveSession,
    stepLiveSession,
    executeWhaleOrder,
  }
}
