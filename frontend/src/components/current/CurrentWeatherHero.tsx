import { Clock, Loader2, MapPin } from 'lucide-react'
import type { ReactNode } from 'react'

import {
  formatCoordinates,
  formatLocationClock,
  formatMeasurement,
  formatUtcOffset,
} from '../../lib/format'
import type { Location, WeatherResponse } from '../../api'
import { cn } from '../../lib/cn'
import { MetricGrid } from './MetricGrid'

/** Props for {@link CurrentWeatherHero}. */
export interface CurrentWeatherHeroProps {
  readonly location: Location
  readonly weather: WeatherResponse
  /** Re-render tick, so the local clock advances. */
  readonly now: Date
  readonly isRefreshing: boolean
  readonly children?: ReactNode
}

/**
 * Current weather card with dark-first glassmorphism aesthetic:
 * - Large condition emoji centered (text-6xl)
 * - Hero temperature (text-5xl bold), feels-like smaller below
 * - Location name + local time underneath
 * - Refreshing spinner overlay when isRefreshing=true
 */
export function CurrentWeatherHero({
  location,
  weather,
  now,
  isRefreshing,
  children,
}: CurrentWeatherHeroProps): ReactNode {
  const { current, meta } = weather
  const offset = meta.utcOffsetSeconds
  const zoneLabel =
    meta.timezoneAbbreviation !== '' ? meta.timezoneAbbreviation : formatUtcOffset(offset)

  const isHighTemp = current.temperatureC !== null && current.temperatureC >= 25
  const isHighHumidity = current.humidityPct !== null && current.humidityPct >= 70

  return (
    <section
      className={cn(
        'relative overflow-hidden rounded-2xl border border-slate-200/80 bg-white/75 p-6 sm:p-8 backdrop-blur-md shadow-xl transition-all duration-200 dark:border-white/10 dark:bg-white/5',
        isHighTemp &&
          'before:pointer-events-none before:absolute before:inset-0 before:bg-gradient-to-b before:from-orange-500/10 before:via-transparent before:to-transparent',
        isHighHumidity &&
          'after:pointer-events-none after:absolute after:inset-0 after:bg-gradient-to-b after:from-cyan-500/10 after:via-transparent after:to-transparent',
      )}
      aria-labelledby="current-weather-heading"
      aria-busy={isRefreshing}
    >
      {/* Refreshing spinner overlay */}
      {isRefreshing && (
        <div
          className="absolute inset-0 z-20 flex flex-col items-center justify-center gap-2 rounded-2xl bg-slate-900/40 backdrop-blur-sm transition-opacity"
          role="status"
          aria-live="polite"
          aria-label="Refreshing weather data"
        >
          <Loader2 className="h-8 w-8 animate-spin text-cyan-400" aria-hidden="true" />
          <span className="text-xs font-semibold tracking-wide text-cyan-200">Refreshing…</span>
        </div>
      )}

      {/* Hero center: Large condition emoji centered (text-6xl) */}
      <div className="relative z-10 flex flex-col items-center justify-center pt-2 text-center">
        <div
          className="text-6xl filter drop-shadow-[0_8px_20px_rgba(0,0,0,0.3)] transition-transform duration-300 hover:scale-110"
          aria-hidden="true"
        >
          {current.condition.icon}
        </div>

        {/* Hero temperature (text-5xl bold), feels-like smaller below */}
        <div className="mt-3 flex items-baseline justify-center">
          <span className="text-5xl font-extrabold tracking-tight text-slate-900 dark:text-white">
            {formatMeasurement(current.temperatureC, 1)}
          </span>
          <span className="ml-1 text-3xl font-light text-sky-500 dark:text-cyan-400">
            °C
          </span>
        </div>

        {current.feelsLikeC !== null && (
          <p className="mt-1 text-sm font-medium text-slate-600 dark:text-slate-400">
            Feels like{' '}
            <span className="font-semibold text-slate-900 dark:text-slate-200">
              {formatMeasurement(current.feelsLikeC, 1)}°C
            </span>
          </p>
        )}

        {/* Location name + local time underneath */}
        <div className="mt-4 flex flex-wrap items-center justify-center gap-2 text-center">
          <div className="flex items-center gap-1.5 min-w-0">
            <MapPin className="h-4 w-4 shrink-0 text-sky-500 dark:text-cyan-400" aria-hidden="true" />
            <h2
              id="current-weather-heading"
              className="truncate text-lg font-bold tracking-tight text-slate-900 dark:text-white sm:text-xl"
            >
              {location.displayName}
            </h2>
          </div>

          <span className="text-slate-400 dark:text-slate-600" aria-hidden="true">·</span>

          <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
            <Clock className="h-3.5 w-3.5 text-sky-500 dark:text-cyan-400" aria-hidden="true" />
            <span className="font-semibold text-slate-800 dark:text-slate-200" aria-live="off">
              {formatLocationClock(offset, now)}
            </span>
            <span>({zoneLabel})</span>
          </div>
        </div>

        <p className="mt-1 text-center text-xs text-slate-500 dark:text-slate-400">
          {formatCoordinates(meta.latitude, meta.longitude)}
          {meta.elevationM !== null && ` · ${formatMeasurement(meta.elevationM, 0)} m elev`}
        </p>
      </div>

      {/* 2x2 Metric pills / Children */}
      <div className="relative z-10 mt-6 border-t border-slate-200/80 pt-6 dark:border-white/10">
        {children ?? <MetricGrid current={current} />}
      </div>
    </section>
  )
}