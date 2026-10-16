import { CheckCircle2, Loader2, RotateCw, ServerOff } from 'lucide-react'
import type { ReactNode } from 'react'

import { API_BASE_URL } from '../../api'
import type { ApiHealthState } from '../../hooks/useApiHealth'
import { cn } from '../../lib/cn'

/** Props for {@link ApiStatusBadge}. */
export interface ApiStatusBadgeProps {
  readonly state: ApiHealthState
}

/**
 * Compact glass indicator for the backend connection in the sticky header.
 *
 * Shows online/offline status with a glowing indicator dot, version details on hover,
 * and an on-demand re-check action.
 */
export function ApiStatusBadge({ state }: ApiStatusBadgeProps): ReactNode {
  const { status, health, error } = state

  const tone = (() => {
    if (status === 'online') {
      return {
        icon: CheckCircle2,
        pillClass:
          'border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 shadow-[0_0_12px_rgba(16,185,129,0.15)]',
        dotClass: 'bg-emerald-500 dark:bg-emerald-400',
        label: 'API online',
      }
    }
    if (status === 'offline') {
      return {
        icon: ServerOff,
        pillClass:
          'border-rose-500/30 bg-rose-500/10 text-rose-600 dark:text-rose-400 shadow-[0_0_12px_rgba(244,63,94,0.15)]',
        dotClass: 'bg-rose-500 dark:bg-rose-400',
        label: 'API offline',
      }
    }
    return {
      icon: Loader2,
      pillClass:
        'border-sky-500/30 bg-sky-500/10 text-sky-600 dark:text-sky-400 shadow-[0_0_12px_rgba(56,189,248,0.15)]',
      dotClass: 'bg-sky-500 dark:bg-sky-400',
      label: status === 'checking' ? 'Checking…' : 'API unknown',
    }
  })()

  const tooltipText = [
    error?.message ?? `Base URL: ${API_BASE_URL}`,
    health !== null
      ? `v${health.version} · Python ${health.pythonVersion} · TTL: ${health.cacheTtlSeconds.weather ?? 0}s`
      : null,
  ]
    .filter(Boolean)
    .join(' — ')

  return (
    <div className="flex items-center gap-1.5 sm:gap-2">
      <div
        className={cn(
          'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium backdrop-blur-md transition-all',
          tone.pillClass,
        )}
        title={tooltipText}
      >
        {status === 'online' ? (
          <span className="relative flex h-2 w-2 shrink-0">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            <span className={cn('relative inline-flex h-2 w-2 rounded-full', tone.dotClass)} />
          </span>
        ) : (
          <span className={cn('h-2 w-2 shrink-0 rounded-full', tone.dotClass)} />
        )}
        <span className="hidden xs:inline sm:inline">{tone.label}</span>
      </div>

      <button
        type="button"
        onClick={state.check}
        disabled={status === 'checking'}
        aria-label="Re-check API connection"
        title="Re-check API connection"
        className="inline-flex h-7 w-7 items-center justify-center rounded-lg border border-slate-200/80 bg-white/60 text-slate-500 backdrop-blur-md transition-all hover:bg-slate-200/60 hover:text-slate-900 active:scale-95 disabled:opacity-50 dark:border-white/10 dark:bg-white/5 dark:text-slate-400 dark:hover:bg-white/10 dark:hover:text-white"
      >
        <RotateCw
          className={cn('h-3.5 w-3.5', status === 'checking' && 'animate-spin')}
          aria-hidden="true"
        />
      </button>
    </div>
  )
}
