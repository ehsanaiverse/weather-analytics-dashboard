import type { ReactNode } from 'react'

import { cn } from '../../lib/cn'

/** Props for {@link ChartCard}. */
export interface ChartCardProps {
  readonly title: string
  /** The question the chart answers, shown under the title. */
  readonly description: string
  /** Rendered on the right of the header, e.g. a legend or a toggle. */
  readonly actions?: ReactNode
  readonly children: ReactNode
  readonly className?: string
}

/** Header + body frame shared by every chart, so spacing stays consistent. */
export function ChartCard({
  title,
  description,
  actions,
  children,
  className,
}: ChartCardProps): ReactNode {
  return (
    <section className={cn('surface-card p-4 sm:p-5', className)}>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-ink">{title}</h3>
          <p className="mt-0.5 text-xs text-muted">{description}</p>
        </div>
        {actions !== undefined && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </div>
      {children}
    </section>
  )
}