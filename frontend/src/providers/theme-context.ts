import { createContext } from 'react'

/**
 * Theme primitives shared by the provider, the hook and the toggle.
 *
 * They live in a `.ts` module so that files exporting React components export
 * *only* components, which keeps React Fast Refresh working during development.
 */

/** The two supported colour schemes. */
export type Theme = 'light' | 'dark'

/** localStorage key, also read by the inline script in `index.html`. */
export const THEME_STORAGE_KEY = 'weather-dashboard.theme'

/** Value exposed by `useTheme`. */
export interface ThemeContextValue {
  readonly theme: Theme
  readonly setTheme: (theme: Theme) => void
  readonly toggleTheme: () => void
}

export const ThemeContext = createContext<ThemeContextValue | null>(null)

/** Read the stored preference, falling back to the operating system setting. */
export function readInitialTheme(): Theme {
  if (typeof window === 'undefined') {
    return 'light'
  }
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY)
    if (stored === 'light' || stored === 'dark') {
      return stored
    }
  } catch {
    // Private browsing modes can block storage; fall through to the OS setting.
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

/** Whether the user has made an explicit choice, rather than following the OS. */
export function hasExplicitThemePreference(): boolean {
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY)
    return stored === 'light' || stored === 'dark'
  } catch {
    return false
  }
}

/** Persist a preference; best-effort, since storage can be unavailable. */
export function storeThemePreference(theme: Theme | 'system'): void {
  try {
    if (theme === 'system') {
      window.localStorage.removeItem(THEME_STORAGE_KEY)
    } else {
      window.localStorage.setItem(THEME_STORAGE_KEY, theme)
    }
  } catch {
    // Persisting is best-effort only.
  }
}