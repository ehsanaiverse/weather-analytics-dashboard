import { MapPin, RefreshCw } from 'lucide-react'
import type { ReactNode } from 'react'

import type { Location } from '../../api'
import { cn } from '../../lib/cn'
import { Button } from '../ui/Button'
import type { ApiHealthState } from '../../hooks/useApiHealth'
import { LocationSearch } from './LocationSearch'

/** Props for {@link DashboardSidebar}. */
export interface DashboardSidebarProps {
  readonly location: Location | null
  readonly onSelect: (location: Location) => void
  readonly onRefresh: () => void
  readonly isRefreshing: boolean
  readonly api: ApiHealthState
}

/**
 * Control column: search, selected location chip, refresh button.
 *
 * Rendered as a sticky sidebar from `lg` upwards and as a full-width block
 * above the content on smaller screens.
 */
export function DashboardSidebar({
  location,
  onSelect,
  onRefresh,
  isRefreshing,
}: DashboardSidebarProps): ReactNode {
  return (
    <aside className="space-y-4 lg:sticky lg:top-20 lg:self-start">
      <div className="surface-card space-y-4 p-5 backdrop-blur-xl">
        <LocationSearch selected={location} onSelect={onSelect} />

        <div className="border-t border-slate-200/80 dark:border-white/10 pt-3.5">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Selected Location
          </p>

          {location !== null ? (
            <div className="space-y-1.5">
              <div className="inline-flex max-w-full items-center gap-2 rounded-full border border-sky-400/30 bg-sky-400/10 px-3.5 py-1.5 text-xs font-medium text-sky-900 backdrop-blur-md shadow-sm dark:border-cyan-400/30 dark:bg-cyan-400/10 dark:text-cyan-200">
                <MapPin
                  className="h-3.5 w-3.5 shrink-0 text-sky-500 dark:text-cyan-400"
                  aria-hidden="true"
                />
                <span className="truncate font-semibold">{location.displayName}</span>
              </div>
              <p className="text-[0.7rem] text-slate-500 dark:text-slate-400 pl-1">
                {location.latitude.toFixed(3)}, {location.longitude.toFixed(3)}
                {location.timezone !== null && ` · ${location.timezone}`}
              </p>
            </div>
          ) : (
            /* Silent load for default location: clean placeholder without flashing skeleton */
            <p className="text-xs text-slate-400 dark:text-slate-500 italic">
              Loading default location…
            </p>
          )}
        </div>

        <Button
          variant="primary"
          onClick={onRefresh}
          disabled={isRefreshing}
          className="w-full shadow-lg shadow-cyan-500/15"
          aria-label="Refresh weather data"
        >
          <RefreshCw className={cn('h-4 w-4', isRefreshing && 'animate-spin')} aria-hidden="true" />
          {isRefreshing ? 'Refreshing data…' : 'Refresh weather data'}
        </Button>

        <p className="text-[0.7rem] leading-relaxed text-slate-500 dark:text-slate-400">
          Refreshes forecast model blend from Open-Meteo. Reuses cached responses when available.
        </p>
      </div>
    </aside>
  )
}