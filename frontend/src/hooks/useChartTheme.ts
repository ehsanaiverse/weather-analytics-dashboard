import { useEffect, useState } from 'react'

import { useTheme } from './useTheme'

/** Resolved colours handed to Recharts. */
export interface ChartTheme {
  readonly text: string
  readonly muted: string
  readonly grid: string
  readonly axis: string
  readonly temperature: string
  readonly humidity: string
  readonly precipitation: string
  readonly temperatureMin: string
  readonly surface: string
}

/**
 * CSS custom properties the charts read.
 *
 * Recharts writes `stroke`/`fill` as SVG attributes, where `var(--x)` is not
 * resolved, so the tokens have to be read as concrete colour values.
 */
const TOKENS = {
  text: '--color-ink',
  muted: '--color-muted',
  grid: '--color-line',
  axis: '--color-line',
  temperature: '--color-temperature',
  humidity: '--color-humidity',
  precipitation: '--color-precipitation',
  temperatureMin: '--color-temperature-min',
  surface: '--color-surface',
} as const satisfies Record<keyof ChartTheme, string>

/** Fallback palette used before the stylesheet has been parsed. */
const FALLBACK: ChartTheme = {
  text: '#111827',
  muted: '#6B7280',
  grid: '#E4E7EB',
  axis: '#E4E7EB',
  temperature: '#E4572E',
  humidity: '#3E8FB0',
  precipitation: '#3B7DD8',
  temperatureMin: '#4C78A8',
  surface: '#FFFFFF',
}

function readTokens(): ChartTheme {
  if (typeof window === 'undefined') {
    return FALLBACK
  }
  const styles = window.getComputedStyle(document.documentElement)
  const resolved = {} as Record<keyof ChartTheme, string>
  for (const [key, variable] of Object.entries(TOKENS)) {
    const value = styles.getPropertyValue(variable).trim()
    if (value.length > 0) {
      resolved[key as keyof ChartTheme] = `rgb(${value})`
    }
  }
  return { ...FALLBACK, ...resolved }
}

/**
 * Chart colours that follow the active theme.
 *
 * The token values are read in a passive effect, which runs after every layout
 * effect - so by then `ThemeProvider` has already toggled the `dark` class and
 * the fresh values are picked up.
 */
export function useChartTheme(): ChartTheme {
  const { theme } = useTheme()
  const [colors, setColors] = useState<ChartTheme>(FALLBACK)

  useEffect(() => {
    setColors(readTokens())
  }, [theme])

  return colors
}