import { CloudSun } from 'lucide-react'
import type { ReactNode } from 'react'

import { ThemeToggle } from '../theme/ThemeToggle'

/** Props for {@link AppHeader}. */
export interface AppHeaderProps {
  readonly title: string
  readonly subtitle: string
  /** Controls rendered on the right (e.g. ApiStatusBadge), left of the theme toggle. */
  readonly actions?: ReactNode
}

/**
 * Application header: product identity on the left, controls on the right.
 *
 * Sticky header with frosted glass blur, app identity left, health badge + theme toggle right.
 */
export function AppHeader({ title, subtitle, actions }: AppHeaderProps): ReactNode {
  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/75 backdrop-blur-xl transition-colors dark:border-white/10 dark:bg-slate-950/40">
      <div className="mx-auto flex max-w-content items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-sky-400/20 bg-gradient-to-br from-sky-400/20 to-cyan-400/10 text-sky-500 shadow-[0_0_15px_rgba(56,189,248,0.15)] dark:border-cyan-400/30 dark:text-cyan-400 dark:shadow-[0_0_18px_rgba(34,211,238,0.2)] sm:h-11 sm:w-11">
            <CloudSun className="h-5 w-5" aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <h1 className="truncate text-sm font-bold tracking-tight text-slate-900 dark:text-white sm:text-base lg:text-lg">
              {title}
            </h1>
            <p className="hidden truncate text-xs text-slate-500 dark:text-slate-400 sm:block">
              {subtitle}
            </p>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2.5 sm:gap-3">
          {actions}
          <ThemeToggle />
        </div>
      </div>
    </header>
  )
}