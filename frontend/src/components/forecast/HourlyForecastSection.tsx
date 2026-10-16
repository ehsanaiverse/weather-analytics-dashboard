import { Clock, LayoutGrid, LineChart } from 'lucide-react'
import { useState } from 'react'
import type { ReactNode } from 'react'

import { HOURS_CHOICES } from '../../api'
import { cn } from '../../lib/cn'
import { formatLocalTime, formatMeasurement } from '../../lib/format'
import type { HourlyPoint, WeatherResponse } from '../../api'
import { TemperatureChart } from '../charts/WeatherCharts'
import { EmptyState } from '../states/DashboardStates'

/** Derive an intuitive weather emoji for an hourly forecast step. */
function getHourEmoji(point: HourlyPoint): string {
  const timeStr = point.time ?? ''
  const hourPart = timeStr.includes('T')
    ? parseInt(timeStr.split('T')[1]?.split(':')[0] ?? '12', 10)
    : 12
  const isNight = hourPart < 6 || hourPart >= 20
  const pop = point.precipitationProbabilityPct ?? 0
  const humidity = point.humidityPct ?? 0
  const temp = point.temperatureC ?? 15

  if (pop >= 60) {
    return temp <= 0 ? '❄️' : '🌧️'
  }
  if (pop >= 30) {
    return temp <= 0 ? '🌨️' : '🌦️'
  }
  if (humidity >= 85) {
    return '☁️'
  }
  if (humidity >= 60) {
    return '⛅'
  }
  return isNight ? '🌙' : '☀️'
}

/** Props for {@link HourlyWindowSelector}. */
export interface HourlyWindowSelectorProps {
  readonly value: number
  readonly onChange: (hours: number) => void
  readonly disabled?: boolean
}

/** Segmented glass 12 / 24 / 48 hour control. */
export function HourlyWindowSelector({
  value,
  onChange,
  disabled = false,
}: HourlyWindowSelectorProps): ReactNode {
  return (
    <div
      role="radiogroup"
      aria-label="Hourly forecast window"
      className="inline-flex rounded-xl border border-slate-200/80 bg-white/70 p-1 backdrop-blur-md dark:border-white/10 dark:bg-white/5"
    >
      {HOURS_CHOICES.map((hours) => {
        const active = hours === value
        return (
          <button
            key={hours}
            type="button"
            role="radio"
            aria-checked={active}
            disabled={disabled}
            onClick={() => onChange(hours)}
            className={cn(
              'rounded-lg px-2.5 py-1 text-xs font-semibold transition-all',
              active
                ? 'bg-gradient-to-r from-sky-400 to-cyan-400 text-slate-950 shadow-md shadow-cyan-500/20'
                : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white',
              disabled && 'cursor-not-allowed opacity-40',
            )}
          >
            {hours}h
          </button>
        )
      })}
    </div>
  )
}

/** Props for {@link HourlyForecastSection}. */
export interface HourlyForecastSectionProps {
  readonly weather: WeatherResponse
  readonly hours: number
  readonly onHoursChange: (hours: number) => void
  readonly isBusy: boolean
}

/**
 * Hourly forecast with dark-first glassmorphism design:
 * - Horizontal scrollable row of hour cards (default view)
 * - Each card: time label, small condition emoji, temp, precip bar at bottom
 * - Toggle between card row and line chart (existing Recharts line chart, restyled)
 */
export function HourlyForecastSection({
  weather,
  hours,
  onHoursChange,
  isBusy,
}: HourlyForecastSectionProps): ReactNode {
  const { hourly, summary } = weather
  const [viewMode, setViewMode] = useState<'cards' | 'chart'>('cards')

  return (
    <section aria-labelledby="hourly-heading" className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2
            id="hourly-heading"
            className="text-base sm:text-lg font-bold tracking-tight text-slate-900 dark:text-white"
          >
            Hourly Forecast · next {hours} hours
          </h2>
          <p className="mt-0.5 flex flex-wrap items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
            <Clock className="h-3.5 w-3.5 text-sky-500 dark:text-cyan-400" aria-hidden="true" />
            {summary.windowStart === null || summary.windowEnd === null ? (
              <span>Window unavailable</span>
            ) : (
              <span>
                {formatLocalTime(summary.windowStart)} – {formatLocalTime(summary.windowEnd)}{' '}
                local time · {summary.hoursCount} hourly steps
              </span>
            )}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          {/* Toggle between Card row and Line chart */}
          <div
            className="inline-flex rounded-xl border border-slate-200/80 bg-white/70 p-1 backdrop-blur-md dark:border-white/10 dark:bg-white/5"
            role="group"
            aria-label="View mode toggle"
          >
            <button
              type="button"
              onClick={() => setViewMode('cards')}
              aria-pressed={viewMode === 'cards'}
              title="Cards view"
              className={cn(
                'inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold transition-all',
                viewMode === 'cards'
                  ? 'bg-gradient-to-r from-sky-400 to-cyan-400 text-slate-950 shadow-md shadow-cyan-500/20'
                  : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white',
              )}
            >
              <LayoutGrid className="h-3.5 w-3.5" aria-hidden="true" />
              <span>Cards</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode('chart')}
              aria-pressed={viewMode === 'chart'}
              title="Chart view"
              className={cn(
                'inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold transition-all',
                viewMode === 'chart'
                  ? 'bg-gradient-to-r from-sky-400 to-cyan-400 text-slate-950 shadow-md shadow-cyan-500/20'
                  : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white',
              )}
            >
              <LineChart className="h-3.5 w-3.5" aria-hidden="true" />
              <span>Chart</span>
            </button>
          </div>

          <HourlyWindowSelector value={hours} onChange={onHoursChange} disabled={isBusy} />
        </div>
      </div>

      {hourly.length === 0 ? (
        <EmptyState
          icon={Clock}
          title="No hourly data"
          message="The weather service did not return hourly data for this location and time range. Try refreshing, or pick another location."
        />
      ) : viewMode === 'cards' ? (
        /* Horizontal scrollable row of hour cards */
        <div className="relative">
          <div className="flex gap-3 overflow-x-auto pb-3 pt-1 scrollbar-thin scrollbar-thumb-slate-300 dark:scrollbar-thumb-white/10 hover:dark:scrollbar-thumb-white/20 snap-x">
            {hourly.map((point) => {
              const pop = point.precipitationProbabilityPct ?? 0
              const emoji = getHourEmoji(point)

              return (
                <div
                  key={point.time ?? point.label}
                  className="min-w-[5.75rem] flex-shrink-0 flex flex-col items-center justify-between p-3.5 rounded-2xl border border-slate-200/80 bg-white/75 backdrop-blur-md transition-all duration-200 hover:bg-white/95 hover:border-sky-400/40 dark:border-white/10 dark:bg-white/5 dark:hover:bg-white/10 dark:hover:border-cyan-400/40 hover:shadow-lg hover:shadow-cyan-500/10 snap-start"
                >
                  <p className="text-xs font-semibold text-slate-700 dark:text-slate-300 truncate max-w-full">
                    {point.label}
                  </p>

                  <span
                    className="text-2xl my-2 filter drop-shadow transition-transform duration-200 hover:scale-125"
                    aria-hidden="true"
                  >
                    {emoji}
                  </span>

                  <p className="text-base font-bold text-slate-900 dark:text-white">
                    {formatMeasurement(point.temperatureC, 0)}°C
                  </p>

                  {/* Precip bar at bottom */}
                  <div className="w-full mt-2.5 space-y-1">
                    <div
                      className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-white/10"
                      role="progressbar"
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-valuenow={pop}
                      aria-label={`Precipitation probability ${pop}%`}
                    >
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-sky-400 to-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.3)] transition-all duration-500"
                        style={{ width: `${Math.max(0, Math.min(100, pop))}%` }}
                      />
                    </div>
                    <p className="text-[0.65rem] font-medium text-cyan-600 dark:text-cyan-300 text-center">
                      {pop}%
                    </p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      ) : (
        /* Chart view (existing Recharts chart, restyled) */
        <div className="space-y-3">
          <TemperatureChart data={hourly} height={280} />
        </div>
      )}

      {summary.missingHourlyCount > 0 && (
        <p className="text-xs text-slate-500 dark:text-slate-400">
          The provider did not report {summary.missingHourlyCount} hourly value(s). Those points are
          shown as gaps, not as zero.
        </p>
      )}
    </section>
  )
}
