import { useContext } from 'react'

import { ThemeContext } from '../providers/theme-context'
import type { ThemeContextValue } from '../providers/theme-context'

/**
 * Access the current theme.
 *
 * @throws {Error} when called outside a `ThemeProvider`.
 */
export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext)
  if (context === null) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}