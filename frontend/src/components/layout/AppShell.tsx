import type { ReactNode } from 'react'

import { AppFooter } from './AppFooter'
import { AppHeader } from './AppHeader'

/** Props for {@link AppShell}. */
export interface AppShellProps {
  readonly title: string
  readonly subtitle: string
  readonly attribution: string
  readonly version: string
  /** Optional controls rendered in the header, left of the theme toggle. */
  readonly headerActions?: ReactNode
  /** Optional content rendered in the footer, above the attribution. */
  readonly footerExtra?: ReactNode
  readonly children: ReactNode
}

/**
 * Page frame: header, content area and footer with aurora background animation.
 *
 * The shell owns page-level layout only and holds no data fetching, so it stays
 * reusable while sections are being built.
 */
export function AppShell({
  title,
  subtitle,
  attribution,
  version,
  headerActions,
  footerExtra,
  children,
}: AppShellProps): ReactNode {
  return (
    <div className="relative flex min-h-screen flex-col bg-slate-100 text-slate-900 transition-colors selection:bg-cyan-500/30 selection:text-cyan-200 dark:bg-gradient-to-br dark:from-[#0f172a] dark:via-[#162032] dark:to-[#1e293b] dark:text-slate-100">
      {/* Subtle pure CSS drifting aurora background */}
      <div className="aurora-bg" aria-hidden="true">
        <div className="aurora-blob aurora-blob-1 opacity-20 dark:opacity-40" />
        <div className="aurora-blob aurora-blob-2 opacity-15 dark:opacity-35" />
        <div className="aurora-blob aurora-blob-3 opacity-20 dark:opacity-35" />
      </div>

      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-3 focus:z-50 focus:rounded-xl focus:bg-cyan-400 focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-slate-950 focus:shadow-lg focus:shadow-cyan-400/30"
      >
        Skip to main content
      </a>

      <AppHeader title={title} subtitle={subtitle} actions={headerActions} />

      <main
        id="main-content"
        tabIndex={-1}
        className="relative z-10 mx-auto w-full max-w-content flex-1 px-4 py-6 focus:outline-none sm:px-6 sm:py-8"
      >
        {children}
      </main>

      <AppFooter attribution={attribution} version={version}>
        {footerExtra}
      </AppFooter>
    </div>
  )
}