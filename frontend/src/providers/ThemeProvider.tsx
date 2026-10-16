import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

import {
  ThemeContext,
  hasExplicitThemePreference,
  readInitialTheme,
  storeThemePreference,
} from './theme-context'
import type { Theme, ThemeContextValue } from './theme-context'

/**
 * Provide the current theme and the functions that change it.
 *
 * Tailwind is configured with `darkMode: 'class'`, so switching themes means
 * toggling the `dark` class on `<html>`; `color-scheme` is updated alongside it
 * so native form controls and scrollbars match. Until the user picks a theme
 * explicitly, the operating system preference is tracked live.
 */
export function ThemeProvider({ children }: { readonly children: ReactNode }): ReactNode {
  const [theme, setThemeState] = useState<Theme>(readInitialTheme)

  // A layout effect runs before any passive effect, so consumers that read the
  // CSS variables (the charts) always see the palette for the new theme.
  useLayoutEffect(() => {
    const root = document.documentElement
    root.classList.toggle('dark', theme === 'dark')
    root.style.colorScheme = theme
  }, [theme])

  // Follow the operating system while no explicit preference is stored.
  useEffect(() => {
    if (hasExplicitThemePreference()) {
      return
    }
    const query = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = (event: MediaQueryListEvent): void => {
      setThemeState(event.matches ? 'dark' : 'light')
    }
    query.addEventListener('change', onChange)
    return () => query.removeEventListener('change', onChange)
  }, [])

  const setTheme = useCallback((next: Theme) => {
    storeThemePreference(next)
    setThemeState(next)
  }, [])

  const toggleTheme = useCallback(() => {
    setThemeState((current) => (current === 'dark' ? 'light' : 'dark'))
  }, [])

  const value = useMemo<ThemeContextValue>(
    () => ({ theme, setTheme, toggleTheme }),
    [theme, setTheme, toggleTheme],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}