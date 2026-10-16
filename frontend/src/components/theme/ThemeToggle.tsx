import { Monitor, Moon, Sun } from 'lucide-react'
import type { ComponentType, ReactNode } from 'react'

import { useTheme } from '../../hooks/useTheme'
import { hasExplicitThemePreference, storeThemePreference } from '../../providers/theme-context'
import type { Theme } from '../../providers/theme-context'
import { cn } from '../../lib/cn'

/** Props for {@link ThemeToggle}. */
export interface ThemeToggleProps {
  readonly className?: string
}

interface ThemeOption {
  readonly value: Theme
  readonly label: string
  readonly Icon: ComponentType<{ className?: string }>
}

const OPTIONS: readonly ThemeOption[] = [
  { value: 'light', label: 'Light', Icon: Sun },
  { value: 'dark', label: 'Dark', Icon: Moon },
]

/**
 * Three-way frosted glass theme control: light, dark and system.
 */
export function ThemeToggle({ className }: ThemeToggleProps): ReactNode {
  const { theme, setTheme } = useTheme()
  const systemActive = !hasExplicitThemePreference()

  const selectSystem = (): void => {
    storeThemePreference('system')
    setTheme(window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
  }

  const controlClass = (active: boolean): string =>
    cn(
      'inline-flex h-7 w-7 items-center justify-center rounded-lg transition-all text-xs font-medium',
      active
        ? 'bg-gradient-to-r from-sky-400 to-cyan-400 text-slate-950 shadow-md shadow-cyan-500/20 font-semibold'
        : 'text-slate-500 hover:bg-slate-200/60 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-white/10 dark:hover:text-white',
    )

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1 rounded-xl border border-slate-200/80 bg-white/60 p-1 backdrop-blur-md transition-colors dark:border-white/10 dark:bg-white/5',
        className,
      )}
      role="group"
      aria-label="Colour theme"
    >
      {OPTIONS.map(({ value, label, Icon }) => {
        const active = !systemActive && theme === value
        return (
          <button
            key={value}
            type="button"
            onClick={() => setTheme(value)}
            aria-pressed={active}
            aria-label={`${label} theme`}
            title={`${label} theme`}
            className={controlClass(active)}
          >
            <Icon className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        )
      })}
      <button
        type="button"
        onClick={selectSystem}
        aria-pressed={systemActive}
        aria-label="Match system theme"
        title="Match system theme"
        className={controlClass(systemActive)}
      >
        <Monitor className="h-3.5 w-3.5" aria-hidden="true" />
      </button>
    </div>
  )
}