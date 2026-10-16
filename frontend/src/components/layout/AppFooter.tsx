import type { ReactNode } from 'react'

/** Props for {@link AppFooter}. */
export interface AppFooterProps {
  readonly attribution: string
  readonly version: string
  /** Extra content rendered above the attribution line. */
  readonly children?: ReactNode
}

/**
 * Footer carrying the Open-Meteo attribution.
 *
 * The CC BY 4.0 licence requires the attribution to stay visible, so it is
 * rendered unconditionally rather than being folded away.
 */
export function AppFooter({ attribution, version, children }: AppFooterProps): ReactNode {
  return (
    <footer className="relative z-10 mt-auto border-t border-slate-200/80 bg-white/60 backdrop-blur-md transition-colors dark:border-white/10 dark:bg-slate-950/40">
      <div className="mx-auto max-w-content px-4 py-6 sm:px-6">
        {children !== undefined && <div className="mb-4">{children}</div>}
        <p className="text-xs font-medium text-slate-600 dark:text-slate-400">{attribution}</p>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-500">
          Forecast values are model output, not measurements. Treat them as guidance, not as
          guarantees. Version {version}.
        </p>
      </div>
    </footer>
  )
}