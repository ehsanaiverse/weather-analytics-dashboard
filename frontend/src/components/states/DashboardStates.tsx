import { AlertTriangle, CloudOff, Inbox, RotateCcw } from 'lucide-react'
import type { ComponentType, ReactNode } from 'react'

import { type ApiError } from '../../api'
import { cn } from '../../lib/cn'
import { Button } from '../ui/Button'

/** Props for {@link LoadingSkeleton}. */
export interface LoadingSkeletonProps {
  readonly className?: string
}

/** A single shimmering placeholder block. */
export function LoadingSkeleton({ className }: LoadingSkeletonProps): ReactNode {
  return (
    <div
      className={cn(
        'animate-pulse rounded-xl bg-slate-200/80 dark:bg-white/10 transition-colors',
        className,
      )}
      aria-hidden="true"
    />
  )
}

/** Placeholder matching the Current weather card glass outline. */
export function HeroSkeleton(): ReactNode {
  return (
    <div
      className="surface-card p-6 sm:p-8 backdrop-blur-xl"
      role="status"
      aria-label="Loading current weather"
    >
      {/* Top row */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200/80 dark:border-white/10 pb-4">
        <div className="space-y-2">
          <LoadingSkeleton className="h-6 w-44" />
          <LoadingSkeleton className="h-3 w-32" />
        </div>
        <LoadingSkeleton className="h-7 w-28 rounded-full" />
      </div>

      {/* Hero center */}
      <div className="flex flex-col items-center justify-center py-6">
        <LoadingSkeleton className="h-16 w-16 rounded-full mb-3" />
        <LoadingSkeleton className="h-12 w-36 mb-2" />
        <LoadingSkeleton className="h-4 w-24" />
      </div>

      {/* 2x2 metric pills placeholder */}
      <div className="grid grid-cols-2 gap-3 sm:gap-4 mt-2">
        {Array.from({ length: 4 }, (_, i) => (
          <div
            key={i}
            className="flex items-center gap-3 rounded-2xl border border-slate-200/80 dark:border-white/10 bg-white/40 dark:bg-white/5 p-3.5 sm:p-4 backdrop-blur-md"
          >
            <LoadingSkeleton className="h-10 w-10 rounded-xl shrink-0" />
            <div className="space-y-2 flex-1">
              <LoadingSkeleton className="h-3 w-16" />
              <LoadingSkeleton className="h-5 w-20" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

/** Placeholder for the 2x2 KPI pills. */
export function MetricSkeletons({ count = 4 }: { readonly count?: number }): ReactNode {
  return (
    <div
      className="grid grid-cols-2 gap-3 sm:gap-4"
      role="status"
      aria-label="Loading measurements"
    >
      {Array.from({ length: count }, (_, index) => (
        <div
          key={index}
          className="surface-card flex items-center gap-3 p-3.5 sm:p-4 rounded-2xl backdrop-blur-md"
        >
          <LoadingSkeleton className="h-10 w-10 rounded-xl shrink-0" />
          <div className="space-y-2 flex-1">
            <LoadingSkeleton className="h-3 w-16" />
            <LoadingSkeleton className="h-5 w-24" />
          </div>
        </div>
      ))}
    </div>
  )
}

/** Placeholder for a chart or section card. */
export function ChartSkeleton({ height = 240 }: { readonly height?: number }): ReactNode {
  return (
    <div className="surface-card p-5 sm:p-6 backdrop-blur-xl" role="status" aria-label="Loading forecast">
      <div className="mb-4 flex justify-between items-center">
        <div className="space-y-2">
          <LoadingSkeleton className="h-5 w-40" />
          <LoadingSkeleton className="h-3 w-56" />
        </div>
        <LoadingSkeleton className="h-8 w-24 rounded-xl" />
      </div>
      <div
        className="animate-pulse w-full rounded-2xl bg-slate-200/80 dark:bg-white/10"
        style={{ height }}
        aria-hidden="true"
      />
    </div>
  )
}

/** Props for {@link EmptyState}. */
export interface EmptyStateProps {
  readonly title: string
  readonly message: string
  readonly icon?: ComponentType<{ className?: string }>
  readonly children?: ReactNode
}

/** Shown when a request succeeded but returned nothing to draw. */
export function EmptyState({
  title,
  message,
  icon: Icon = Inbox,
  children,
}: EmptyStateProps): ReactNode {
  return (
    <div className="surface-card flex flex-col items-center gap-3.5 px-6 py-10 text-center backdrop-blur-xl">
      <span className="flex h-12 w-12 items-center justify-center rounded-2xl border border-slate-200/80 dark:border-white/10 bg-slate-100 dark:bg-white/5 text-slate-400">
        <Icon className="h-6 w-6" aria-hidden="true" />
      </span>
      <div>
        <p className="text-sm font-bold text-slate-900 dark:text-white">{title}</p>
        <p className="mt-1 max-w-md text-xs sm:text-sm text-slate-500 dark:text-slate-400">
          {message}
        </p>
      </div>
      {children}
    </div>
  )
}

/** Props for {@link ErrorState}. */
export interface ErrorStateProps {
  readonly error: ApiError
  readonly onRetry?: () => void
  readonly title?: string
}

/**
 * Inline error banner inside the relevant section (styled in orange/red glass card).
 *
 * Displays an icon + error message + status/request details + retry button.
 */
export function ErrorState({
  error,
  onRetry,
  title = 'Could not load weather data',
}: ErrorStateProps): ReactNode {
  return (
    <div
      role="alert"
      className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-5 sm:p-6 backdrop-blur-xl text-rose-950 dark:text-rose-100 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-xl shadow-rose-950/10"
    >
      <div className="flex items-start gap-3.5 min-w-0">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-rose-500/30 bg-rose-500/20 text-rose-600 dark:text-rose-400 shadow-[0_0_15px_rgba(244,63,94,0.2)]">
          <CloudOff className="h-5 w-5" aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <p className="text-sm font-bold text-rose-900 dark:text-rose-200">{title}</p>
          <p className="mt-0.5 text-xs sm:text-sm text-rose-800 dark:text-rose-300">
            {error.message}
          </p>
          <p className="mt-1.5 text-[0.7rem] text-rose-700/80 dark:text-rose-400/80">
            {error.status > 0 ? `HTTP ${error.status}` : 'Server connection failed'}
            {error.code !== null && ` · ${error.code}`}
            {error.requestId !== '' && ` · req ${error.requestId}`}
          </p>
        </div>
      </div>

      {onRetry !== undefined && (
        <Button
          variant="primary"
          onClick={onRetry}
          className="shrink-0 bg-gradient-to-r from-orange-400 to-rose-400 text-slate-950 shadow-md shadow-rose-500/20"
        >
          <RotateCcw className="h-3.5 w-3.5 mr-1" aria-hidden="true" />
          Try again
        </Button>
      )}
    </div>
  )
}

/** Props for {@link WarningBanner}. */
export interface WarningBannerProps {
  readonly messages: readonly string[]
}

/** Non-blocking notice for data-quality warnings reported by the backend. */
export function WarningBanner({ messages }: WarningBannerProps): ReactNode {
  if (messages.length === 0) {
    return null
  }
  return (
    <div
      role="status"
      className="flex items-start gap-3 rounded-2xl border border-amber-500/30 bg-amber-500/10 px-4 py-3.5 text-xs sm:text-sm text-amber-900 backdrop-blur-xl dark:border-amber-400/20 dark:bg-amber-500/10 dark:text-amber-200"
    >
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500 dark:text-amber-400" aria-hidden="true" />
      <div className="min-w-0 space-y-1">
        {messages.map((message) => (
          <p key={message}>{message}</p>
        ))}
      </div>
    </div>
  )
}