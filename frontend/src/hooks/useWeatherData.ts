import { useCallback, useEffect, useRef, useState } from 'react'

import { ApiError, getWeather, refreshCache } from '../api'
import type { WeatherResponse } from '../api'

/** Query parameters that identify one forecast. */
export interface WeatherQuery {
  readonly latitude: number
  readonly longitude: number
  readonly hours: number
}

/** Coarse state of the dashboard data, used to pick a loading treatment. */
export type WeatherStatus = 'idle' | 'loading' | 'refreshing' | 'success' | 'error'

/** Value returned by {@link useWeatherData}. */
export interface WeatherDataState {
  readonly data: WeatherResponse | null
  readonly status: WeatherStatus
  readonly error: ApiError | null
  /** True while a request is in flight, whether or not stale data is on screen. */
  readonly isBusy: boolean
  /** True when data is on screen but a newer request is in flight. */
  readonly isRefreshing: boolean
  /** Drop the backend cache, then refetch. */
  readonly refresh: () => void
}

/** Coerce any thrown value into an {@link ApiError}. */
function toApiError(cause: unknown, fallback: string): ApiError {
  return cause instanceof ApiError
    ? cause
    : new ApiError(fallback, { status: 0, code: null, requestId: '' })
}

/**
 * Load the forecast for one location and window.
 *
 * Guarantees, all of which matter when a user switches location quickly:
 *
 *  - **No stale writes.** Each request gets a monotonically increasing id; a
 *    response is applied only while it is still the newest request.
 *  - **No wasted work.** Starting a request aborts the previous one.
 *  - **No blank flash.** Switching location or window keeps the previous data on
 *    screen while the new request runs, and reports `isRefreshing` instead of
 *    `isLoading`.
 *  - **Errors never wipe good data.** A failure keeps the last good response and
 *    exposes the error alongside it.
 */
export function useWeatherData(query: WeatherQuery | null): WeatherDataState {
  const [data, setData] = useState<WeatherResponse | null>(null)
  const [status, setStatus] = useState<WeatherStatus>('idle')
  const [error, setError] = useState<ApiError | null>(null)

  const requestIdRef = useRef(0)
  const controllerRef = useRef<AbortController | null>(null)
  const latitude = query?.latitude ?? null
  const longitude = query?.longitude ?? null
  const hours = query?.hours ?? null

  const load = useCallback(
    (options: { readonly bypassCache: boolean }) => {
      if (latitude === null || longitude === null || hours === null) {
        return
      }

      const requestId = requestIdRef.current + 1
      requestIdRef.current = requestId

      controllerRef.current?.abort()
      const controller = new AbortController()
      controllerRef.current = controller

      setStatus((current) => (current === 'success' ? 'refreshing' : 'loading'))
      setError(null)

      const fetchForecast = async (): Promise<void> => {
        if (options.bypassCache) {
          try {
            // Best effort: even if this fails the forecast fetch may still work.
            await refreshCache('weather', { signal: controller.signal })
          } catch {
            // Ignored on purpose - the error that matters is surfaced below.
          }
        }
        const response = await getWeather({
          latitude,
          longitude,
          hours,
          signal: controller.signal,
        })
        if (requestId !== requestIdRef.current || controller.signal.aborted) {
          return
        }
        setData(response)
        setStatus('success')
      }

      fetchForecast().catch((cause: unknown) => {
        if (requestId !== requestIdRef.current || controller.signal.aborted) {
          return
        }
        setError(toApiError(cause, 'Could not load weather data.'))
        // The previous payload is kept on purpose: `data` stays non-null so the
        // dashboard can keep rendering it with the error shown alongside.
        setStatus('error')
      })
    },
    [latitude, longitude, hours],
  )

  useEffect(() => {
    load({ bypassCache: false })
    return () => {
      controllerRef.current?.abort()
    }
  }, [load])

  const refresh = useCallback(() => {
    load({ bypassCache: true })
  }, [load])

  return {
    data,
    status,
    error,
    isBusy: status === 'loading' || status === 'refreshing',
    isRefreshing: status === 'refreshing',
    refresh,
  }
}