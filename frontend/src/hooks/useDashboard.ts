import { useCallback, useEffect, useState } from 'react'

import { ApiError, getDefaultLocation } from '../api'
import { HOURS_CHOICES } from '../api'
import type { Location, WeatherResponse } from '../api'
import { useWeatherData } from './useWeatherData'
import type { WeatherStatus } from './useWeatherData'

/** Value returned by {@link useDashboard}. */
export interface DashboardState {
  readonly location: Location | null
  readonly hours: number
  readonly setHours: (hours: number) => void
  readonly selectLocation: (location: Location) => void
  readonly weather: WeatherResponse | null
  readonly status: WeatherStatus
  readonly error: ApiError | null
  readonly isBusy: boolean
  readonly isRefreshing: boolean
  readonly refresh: () => void
  /** Ticks once a minute so the local clock in the hero stays live. */
  readonly now: Date
  /** Failure to resolve the built-in default location. */
  readonly bootstrapError: ApiError | null
}

/** How often the local clock is re-rendered. */
const CLOCK_INTERVAL_MS = 60_000

/**
 * Own the dashboard's state: which place, which window, and the data for both.
 *
 * The default location comes from `GET /api/locations/default`, so the
 * coordinates live in exactly one place (`app/config.py`). If that call fails the
 * dashboard stays usable: the user simply searches for a place.
 */
export function useDashboard(): DashboardState {
  const [location, setLocation] = useState<Location | null>(null)
  const [hours, setHoursState] = useState<number>(HOURS_CHOICES[1] ?? 24)
  const [bootstrapError, setBootstrapError] = useState<ApiError | null>(null)
  const [now, setNow] = useState<Date>(() => new Date())

  useEffect(() => {
    const controller = new AbortController()

    getDefaultLocation({ signal: controller.signal })
      .then(setLocation)
      .catch((cause: unknown) => {
        if (controller.signal.aborted) {
          return
        }
        setBootstrapError(
          cause instanceof ApiError
            ? cause
            : new ApiError('Could not load the default location.', {
                status: 0,
                code: null,
                requestId: '',
              }),
        )
      })

    return () => controller.abort()
  }, [])

  useEffect(() => {
    const timer = window.setInterval(() => {
      setNow(new Date())
    }, CLOCK_INTERVAL_MS)
    return () => window.clearInterval(timer)
  }, [])

  const query = location === null ? null : { ...location, hours }
  const weather = useWeatherData(query)

  const setHours = useCallback((next: number) => {
    setHoursState(next)
  }, [])

  return {
    location,
    hours,
    setHours,
    selectLocation: setLocation,
    weather: weather.data,
    status: weather.status,
    error: weather.error,
    isBusy: weather.isBusy,
    isRefreshing: weather.isRefreshing,
    refresh: weather.refresh,
    now,
    bootstrapError,
  }
}