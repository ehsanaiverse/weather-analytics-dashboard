import { CalendarDays, Droplets } from 'lucide-react'
import type { ReactNode } from 'react'

import { formatMeasurement } from '../../lib/format'
import type { WeatherResponse } from '../../api'
import { EmptyState } from '../states/DashboardStates'

/** Props for {@link DailyForecastSection}. */
export interface DailyForecastSectionProps {
  readonly weather: WeatherResponse
}

/**
 * Seven-day daily forecast with dark-first glassmorphism design:
 * - 7 rows, each a glass card with: day label, condition emoji, min/max temp gradient bar (blue=min, orange=max), precip % chip
 * - Replaces the raw data table with this polished visual row layout
 */
export function DailyForecastSection({ weather }: DailyForecastSectionProps): ReactNode {
  const { daily, summary } = weather

  if (daily.length === 0) {
    return (
      <section aria-labelledby="daily-heading">
        <h2
          id="daily-heading"
          className="mb-3 text-base sm:text-lg font-bold tracking-tight text-slate-900 dark:text-white"
        >
          Daily Forecast
        </h2>
        <EmptyState
          icon={CalendarDays}
          title="No daily data"
          message="The weather service did not return daily forecast data for this location. Try refreshing, or pick another location."
        />
      </section>
    )
  }

  // Calculate week-wide min and max for proportional temperature bars
  const validMins = daily.map((d) => d.temperatureMinC).filter((t): t is number => t !== null)
  const validMaxs = daily.map((d) => d.temperatureMaxC).filter((t): t is number => t !== null)
  const weekMin = validMins.length > 0 ? Math.min(...validMins) : 0
  const weekMax = validMaxs.length > 0 ? Math.max(...validMaxs) : 30
  const tempRange = Math.max(weekMax - weekMin, 1)

  return (
    <section aria-labelledby="daily-heading" className="space-y-4">
      <div>
        <h2
          id="daily-heading"
          className="text-base sm:text-lg font-bold tracking-tight text-slate-900 dark:text-white"
        >
          7-Day Outlook
        </h2>
        <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
          Daily forecast model blend. Temperature range bars show low-to-high spread from blue to
          orange.
        </p>
      </div>

      {/* 7 rows, each a glass card */}
      <div className="space-y-2.5">
        {daily.slice(0, 7).map((day) => {
          const minTemp = day.temperatureMinC
          const maxTemp = day.temperatureMaxC
          const pop = day.precipitationProbabilityMaxPct

          // Position of the bar relative to the week's min/max
          const minPct =
            minTemp !== null ? Math.max(0, Math.min(90, ((minTemp - weekMin) / tempRange) * 100)) : 0
          const maxPct =
            maxTemp !== null ? Math.max(10, Math.min(100, ((maxTemp - weekMin) / tempRange) * 100)) : 100
          const barWidth = Math.max(12, maxPct - minPct)

          return (
            <div
              key={day.date ?? day.label}
              className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-6 p-3.5 sm:p-4 rounded-2xl border border-slate-200/80 bg-white/75 backdrop-blur-md transition-all duration-200 hover:bg-white/95 hover:border-sky-400/30 dark:border-white/10 dark:bg-white/5 dark:hover:bg-white/10 dark:hover:border-cyan-400/30 hover:shadow-lg hover:shadow-cyan-500/5"
            >
              {/* Day label + emoji + condition */}
              <div className="flex items-center gap-3 sm:w-48 shrink-0 min-w-0">
                <span
                  className="text-2xl sm:text-3xl filter drop-shadow shrink-0"
                  aria-hidden="true"
                >
                  {day.condition.icon}
                </span>
                <div className="min-w-0">
                  <p className="truncate font-semibold text-sm sm:text-base text-slate-900 dark:text-white">
                    {day.label}
                  </p>
                  <p className="truncate text-xs text-slate-500 dark:text-slate-400">
                    {day.condition.label}
                  </p>
                </div>
              </div>

              {/* Min/max temperature bar (gradient low=blue high=orange) */}
              <div className="flex items-center gap-2.5 sm:gap-3 flex-1 min-w-[120px]">
                <span className="text-xs sm:text-sm font-semibold text-blue-500 dark:text-blue-400 tabular-nums w-8 text-right shrink-0">
                  {formatMeasurement(minTemp, 0)}°
                </span>

                <div className="h-2.5 flex-1 relative rounded-full bg-slate-200/80 dark:bg-white/10 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-blue-400 via-sky-300 to-orange-400 shadow-[0_0_10px_rgba(56,189,248,0.25)] transition-all duration-500"
                    style={{
                      marginLeft: `${minPct}%`,
                      width: `${barWidth}%`,
                    }}
                    role="progressbar"
                    aria-label={`${day.label} temperature range ${minTemp !== null ? Math.round(minTemp) : '?'}° to ${maxTemp !== null ? Math.round(maxTemp) : '?'}°`}
                    aria-valuemin={weekMin}
                    aria-valuemax={weekMax}
                    aria-valuenow={maxTemp ?? undefined}
                  />
                </div>

                <span className="text-xs sm:text-sm font-semibold text-orange-500 dark:text-orange-400 tabular-nums w-8 text-left shrink-0">
                  {formatMeasurement(maxTemp, 0)}°
                </span>
              </div>

              {/* Precip probability chip */}
              <div className="flex items-center justify-end sm:w-24 shrink-0">
                <div
                  className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold backdrop-blur-md border border-cyan-400/20 bg-cyan-400/10 text-cyan-600 dark:text-cyan-300 shrink-0"
                  title={`Max precipitation chance: ${pop === null ? 'not reported' : `${Math.round(pop)}%`}`}
                  aria-label={`Precipitation probability ${pop === null ? 'unknown' : `${Math.round(pop)}%`}`}
                >
                  <Droplets className="h-3.5 w-3.5 text-cyan-500 dark:text-cyan-400" aria-hidden="true" />
                  <span>{pop === null ? '—' : `${Math.round(pop)}%`}</span>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {summary.missingDailyCount > 0 && (
        <p className="text-xs text-slate-500 dark:text-slate-400">
          The provider did not report {summary.missingDailyCount} daily value(s). Those points are
          shown as gaps, not as zero.
        </p>
      )}
    </section>
  )
}