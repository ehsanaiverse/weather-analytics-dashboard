import type { ReactNode } from 'react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { TooltipContentProps } from 'recharts'

import { EM_DASH } from '../../lib/format'
import { useChartTheme } from '../../hooks/useChartTheme'
import type { DailyPoint, HourlyPoint } from '../../api'
import type { ChartTheme } from '../../hooks/useChartTheme'

const AXIS_FONT_SIZE = 11

/** Shared glass tooltip surface. */
function TooltipSurface({ children }: { readonly children: ReactNode }): ReactNode {
  return (
    <div className="rounded-xl border border-slate-200/90 bg-white/95 px-3.5 py-2.5 text-xs shadow-2xl backdrop-blur-xl dark:border-white/15 dark:bg-slate-900/90 dark:text-slate-100">
      {children}
    </div>
  )
}

/** Custom glass tooltip. */
type WeatherTooltipProps = Partial<TooltipContentProps<number, string>> & {
  readonly unit: string
}

function WeatherTooltip({
  active,
  payload,
  label,
  unit,
}: WeatherTooltipProps): ReactNode {
  if (active !== true || payload === undefined || payload.length === 0) {
    return null
  }
  return (
    <TooltipSurface>
      <p className="font-bold text-slate-900 dark:text-white">{String(label ?? '')}</p>
      <ul className="mt-1.5 space-y-1 text-slate-500 dark:text-slate-400">
        {payload.map((entry) => {
          const value = typeof entry.value === 'number' ? entry.value : null
          return (
            <li key={String(entry.dataKey)} className="flex items-center gap-2">
              <span
                className="inline-block h-2 w-2 shrink-0 rounded-full"
                style={{ backgroundColor: entry.color }}
                aria-hidden="true"
              />
              <span>{String(entry.name)}</span>
              <span className="ml-auto font-semibold text-slate-900 dark:text-cyan-300">
                {value === null ? EM_DASH : `${value.toFixed(unit === '%' ? 0 : 1)}${unit}`}
              </span>
            </li>
          )
        })}
      </ul>
    </TooltipSurface>
  )
}

/** Axis and grid styling derived from the active theme. */
function useAxisProps(theme: ChartTheme, unit: string) {
  return {
    stroke: theme.axis,
    tick: { fill: theme.muted, fontSize: AXIS_FONT_SIZE },
    tickLine: false,
    axisLine: false,
    tickFormatter: (value: number) => `${value}${unit}`,
  }
}

/** Props shared by the hourly charts. */
export interface HourlyChartProps {
  readonly data: readonly HourlyPoint[]
  readonly height?: number
}

/**
 * Hourly temperature line chart restyled:
 * - Dark background
 * - Cyan line
 * - No gridlines except faint horizontal
 * - Custom glass tooltip
 */
export function TemperatureChart({ data, height = 280 }: HourlyChartProps): ReactNode {
  const theme = useChartTheme()
  const axis = useAxisProps(theme, '°')

  return (
    <div
      style={{ height }}
      role="img"
      aria-label="Hourly temperature forecast"
      className="rounded-2xl border border-slate-200/80 bg-white/70 p-3 sm:p-4 backdrop-blur-md dark:border-white/10 dark:bg-slate-950/40"
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={[...data]} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          {/* Only faint horizontal gridlines */}
          <CartesianGrid stroke={theme.grid} strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="label" interval="preserveStartEnd" minTickGap={24} {...axis} />
          <YAxis width={44} {...axis} />
          <Tooltip content={<WeatherTooltip unit="°C" />} cursor={{ stroke: theme.muted }} />
          <Line
            type="monotone"
            dataKey="temperatureC"
            name="Temperature"
            stroke="#22d3ee" // Cyan line
            strokeWidth={3}
            dot={false}
            activeDot={{ r: 5, fill: '#22d3ee', stroke: '#0f172a', strokeWidth: 2 }}
            connectNulls={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Hourly relative humidity as a filled area. */
export function HumidityChart({ data, height = 280 }: HourlyChartProps): ReactNode {
  const theme = useChartTheme()
  const axis = useAxisProps(theme, '%')

  return (
    <div
      style={{ height }}
      role="img"
      aria-label="Hourly relative humidity forecast"
      className="rounded-2xl border border-slate-200/80 bg-white/70 p-3 sm:p-4 backdrop-blur-md dark:border-white/10 dark:bg-slate-950/40"
    >
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={[...data]} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={theme.grid} strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="label" interval="preserveStartEnd" minTickGap={24} {...axis} />
          <YAxis width={44} domain={[0, 100]} {...axis} />
          <Tooltip content={<WeatherTooltip unit="%" />} cursor={{ stroke: theme.muted }} />
          <Area
            type="monotone"
            dataKey="humidityPct"
            name="Relative humidity"
            stroke="#38bdf8"
            strokeWidth={2.5}
            fill="#38bdf8"
            fillOpacity={0.2}
            connectNulls={false}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Hourly probability of precipitation as bars. */
export function PrecipitationChart({ data, height = 280 }: HourlyChartProps): ReactNode {
  const theme = useChartTheme()
  const axis = useAxisProps(theme, '%')

  return (
    <div
      style={{ height }}
      role="img"
      aria-label="Chance of precipitation by hour"
      className="rounded-2xl border border-slate-200/80 bg-white/70 p-3 sm:p-4 backdrop-blur-md dark:border-white/10 dark:bg-slate-950/40"
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={[...data]} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={theme.grid} strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="label" interval="preserveStartEnd" minTickGap={24} {...axis} />
          <YAxis width={44} domain={[0, 100]} {...axis} />
          <Tooltip
            content={<WeatherTooltip unit="%" />}
            cursor={{ fill: theme.grid, fillOpacity: 0.3 }}
          />
          <Bar
            dataKey="precipitationProbabilityPct"
            name="Chance of precipitation"
            fill="#60a5fa"
            fillOpacity={0.85}
            radius={[4, 4, 0, 0]}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Props for {@link DailyRangeChart}. */
export interface DailyRangeChartProps {
  readonly data: readonly DailyPoint[]
  readonly height?: number
}

/** Grouped minimum and maximum temperature bars for the seven-day outlook. */
export function DailyRangeChart({ data, height = 300 }: DailyRangeChartProps): ReactNode {
  const theme = useChartTheme()
  const axis = useAxisProps(theme, '°')

  return (
    <div
      style={{ height }}
      role="img"
      aria-label="Daily minimum and maximum temperature"
      className="rounded-2xl border border-slate-200/80 bg-white/70 p-3 sm:p-4 backdrop-blur-md dark:border-white/10 dark:bg-slate-950/40"
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={[...data]} margin={{ top: 8, right: 12, bottom: 0, left: 0 }} barGap={2}>
          <CartesianGrid stroke={theme.grid} strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="label" interval={0} minTickGap={8} {...axis} />
          <YAxis width={44} {...axis} />
          <Tooltip
            content={<WeatherTooltip unit="°C" />}
            cursor={{ fill: theme.grid, fillOpacity: 0.3 }}
          />
          <Bar
            dataKey="temperatureMaxC"
            name="Daily maximum"
            fill="#fb923c"
            radius={[4, 4, 0, 0]}
            isAnimationActive={false}
          />
          <Bar
            dataKey="temperatureMinC"
            name="Daily minimum"
            fill="#60a5fa"
            radius={[4, 4, 0, 0]}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}