import { CloudRain, CloudSun, Droplets, Wind } from 'lucide-react'
import type { ComponentType, ReactNode } from 'react'

import { cn } from '../../lib/cn'
import { EM_DASH } from '../../lib/format'
import type { CurrentConditions } from '../../api'

interface MetricPillProps {
  readonly label: string
  readonly value: string | null
  readonly unit?: string
  readonly icon: ComponentType<{ className?: string }>
  readonly iconColorClass: string
  readonly isWarm?: boolean
  readonly isCool?: boolean
}

function MetricPill({
  label,
  value,
  unit,
  icon: Icon,
  iconColorClass,
  isWarm = false,
  isCool = false,
}: MetricPillProps): ReactNode {
  const missing = value === null

  return (
    <div
      className={cn(
        'group flex items-center gap-3.5 rounded-2xl border p-3.5 sm:p-4 backdrop-blur-md transition-all duration-200',
        'border-slate-200/80 bg-white/70 hover:bg-white/90 dark:border-white/10 dark:bg-white/5 dark:hover:bg-white/10 dark:hover:border-white/20',
        isWarm &&
          'border-orange-500/30 bg-orange-500/10 dark:border-orange-400/30 dark:bg-orange-500/10 shadow-[0_0_15px_rgba(251,146,60,0.1)]',
        isCool &&
          'border-blue-500/30 bg-blue-500/10 dark:border-blue-400/30 dark:bg-blue-500/10 shadow-[0_0_15px_rgba(96,165,250,0.1)]',
      )}
    >
      <span
        className={cn(
          'flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-slate-200/80 bg-white/80 backdrop-blur-md transition-transform duration-200 group-hover:scale-105 dark:border-white/10 dark:bg-white/5',
          iconColorClass,
        )}
      >
        <Icon className="h-5 w-5" aria-hidden="true" />
      </span>
      <div className="min-w-0">
        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{label}</p>
        <p className="truncate text-base sm:text-lg font-bold text-slate-900 dark:text-white">
          {missing ? (
            <span className="text-slate-400">{EM_DASH}</span>
          ) : (
            <>
              {value}
              {unit && (
                <span className="ml-1 text-xs font-medium text-slate-500 dark:text-slate-400">
                  {unit}
                </span>
              )}
            </>
          )}
        </p>
      </div>
    </div>
  )
}

/** Props for {@link MetricGrid}. */
export interface MetricGridProps {
  readonly current: CurrentConditions
}

/**
 * Four metric pills in a 2x2 grid: humidity, wind, precipitation, condition label.
 *
 * Each pill is styled as a glass card with blue tint for high humidity and orange tint for high temperature.
 */
export function MetricGrid({ current }: MetricGridProps): ReactNode {
  const isHighTemp = current.temperatureC !== null && current.temperatureC >= 25
  const isHighHumidity = current.humidityPct !== null && current.humidityPct >= 70

  const humidityVal =
    current.humidityPct !== null ? `${Math.round(current.humidityPct)}` : null
  const windVal =
    current.windSpeedKmh !== null ? current.windSpeedKmh.toFixed(1) : null
  const precipVal =
    current.precipitationMm !== null ? current.precipitationMm.toFixed(1) : null

  return (
    <div
      role="group"
      aria-label="Current conditions metrics"
      className="grid grid-cols-2 gap-3 sm:gap-4"
    >
      {/* Humidity */}
      <MetricPill
        label="Humidity"
        value={humidityVal}
        unit="%"
        icon={Droplets}
        iconColorClass="text-blue-500 dark:text-blue-400 shadow-[0_0_12px_rgba(96,165,250,0.2)]"
        isCool={isHighHumidity}
      />

      {/* Wind */}
      <MetricPill
        label="Wind Speed"
        value={windVal}
        unit="km/h"
        icon={Wind}
        iconColorClass="text-sky-500 dark:text-sky-400 shadow-[0_0_12px_rgba(56,189,248,0.2)]"
      />

      {/* Precipitation */}
      <MetricPill
        label="Precipitation"
        value={precipVal}
        unit="mm"
        icon={CloudRain}
        iconColorClass="text-cyan-500 dark:text-cyan-400 shadow-[0_0_12px_rgba(34,211,238,0.2)]"
      />

      {/* Condition Label */}
      <MetricPill
        label="Condition"
        value={current.condition.label}
        icon={CloudSun}
        iconColorClass="text-amber-500 dark:text-amber-400 shadow-[0_0_12px_rgba(251,191,36,0.2)]"
        isWarm={isHighTemp}
      />
    </div>
  )
}