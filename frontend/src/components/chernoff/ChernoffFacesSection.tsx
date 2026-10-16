import { HelpCircle, Shapes } from 'lucide-react'
import { useMemo, useState } from 'react'
import type { ReactNode } from 'react'

import type { ChernoffSource, ChernoffSourceKey, WeatherResponse } from '../../api'
import {
  DEFAULT_FACE_COUNT,
  FACE_COUNT_CHOICES,
  resolveSpec,
  valueKeyForVariable,
} from '../../lib/chernoff'
import { cn } from '../../lib/cn'
import { useChernoffFaces } from '../../hooks/useChernoffFaces'
import type { ChernoffQuery } from '../../hooks/useChernoffFaces'
import { EmptyState } from '../states/DashboardStates'
import { ChernoffLegend } from './ChernoffLegend'
import { FaceSvg } from './FaceSvg'

/** Grid columns per face count; cells stay roughly square on every breakpoint. */
const GRID_CLASSES: Readonly<Record<number, string>> = {
  1: 'grid-cols-1',
  2: 'grid-cols-2',
  3: 'grid-cols-2 sm:grid-cols-3',
  4: 'grid-cols-2 sm:grid-cols-4',
}

/** Columns for a given number of faces. */
function columnsFor(faceCount: number): number {
  if (faceCount <= 2) {
    return faceCount
  }
  return faceCount <= 4 ? 2 : 4
}

/** A segmented glass radio control, reused for the source and count pickers. */
function SegmentedControl<T extends string | number>({
  label,
  value,
  options,
  disabledValues,
  onChange,
}: {
  readonly label: string
  readonly value: T
  readonly options: readonly T[]
  readonly disabledValues?: ReadonlySet<T>
  readonly onChange: (next: T) => void
}): ReactNode {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
        {label}
      </span>
      <div
        role="radiogroup"
        aria-label={label}
        className="inline-flex rounded-xl border border-slate-200/80 bg-white/70 p-1 backdrop-blur-md dark:border-white/10 dark:bg-white/5"
      >
        {options.map((option) => {
          const active = option === value
          const disabled = disabledValues?.has(option) ?? false
          return (
            <button
              key={String(option)}
              type="button"
              role="radio"
              aria-checked={active}
              disabled={disabled}
              title={disabled ? 'Not enough forecast records for this many faces' : undefined}
              onClick={() => onChange(option)}
              className={cn(
                'rounded-lg px-2.5 py-1 text-xs font-semibold transition-all',
                active
                  ? 'bg-gradient-to-r from-sky-400 to-cyan-400 text-slate-950 shadow-md shadow-cyan-500/20'
                  : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white',
                disabled && 'cursor-not-allowed opacity-40',
              )}
            >
              {String(option)}
            </button>
          )
        })}
      </div>
    </div>
  )
}

/** Props for {@link ChernoffFacesSection}. */
export interface ChernoffFacesSectionProps {
  readonly weather: WeatherResponse
  readonly latitude: number
  readonly longitude: number
}

/**
 * Chernoff Faces: each face wrapped in a glass card with hover scale(1.05) transition,
 * and section header with tooltip explaining the feature encoding.
 */
export function ChernoffFacesSection({
  weather,
  latitude,
  longitude,
}: ChernoffFacesSectionProps): ReactNode {
  const availableSources = Object.keys(weather.chernoff.sources)
  const [source, setSource] = useState<ChernoffSourceKey>('hourly')
  const [count, setCount] = useState<number>(DEFAULT_FACE_COUNT)
  const [showTooltip, setShowTooltip] = useState(false)

  const effectiveSource: ChernoffSourceKey = availableSources.includes(source) ? source : 'hourly'
  const seed: ChernoffSource | null = weather.chernoff.sources[effectiveSource] ?? null

  const query: ChernoffQuery = { latitude, longitude, source: effectiveSource, count }
  const { data, isBusy, error } = useChernoffFaces(query, seed)

  const faces = useMemo(
    () => (data?.faces ?? []).map((face) => ({ face, spec: resolveSpec(face.spec) })),
    [data],
  )

  const disabledCounts = useMemo(() => {
    const disabled = new Set<number>()
    const available = Math.max(faces.length, 2)
    for (const choice of FACE_COUNT_CHOICES) {
      if (choice > available) {
        disabled.add(choice)
      }
    }
    return disabled
  }, [faces.length])

  const columns = columnsFor(Math.max(faces.length, 1))

  return (
    <section aria-labelledby="chernoff-heading" className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h2
              id="chernoff-heading"
              className="text-base sm:text-lg font-bold tracking-tight text-slate-900 dark:text-white"
            >
              Chernoff Faces
            </h2>

            {/* Section header tooltip explaining the encoding */}
            <div className="relative inline-block">
              <button
                type="button"
                aria-label="Explain Chernoff face encoding"
                onMouseEnter={() => setShowTooltip(true)}
                onMouseLeave={() => setShowTooltip(false)}
                onFocus={() => setShowTooltip(true)}
                onBlur={() => setShowTooltip(false)}
                onClick={() => setShowTooltip((prev) => !prev)}
                className="rounded-full p-1 text-slate-400 hover:text-sky-500 dark:hover:text-cyan-400 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
              >
                <HelpCircle className="h-4 w-4" aria-hidden="true" />
              </button>

              {showTooltip && (
                <div
                  role="tooltip"
                  className="surface-card absolute left-0 top-full z-40 mt-2 w-72 p-3.5 text-xs shadow-2xl backdrop-blur-xl border border-slate-200/90 dark:border-white/15 bg-white/95 dark:bg-slate-900/95"
                >
                  <p className="font-bold text-slate-900 dark:text-white mb-1.5">
                    Multivariate Facial Encoding
                  </p>
                  <ul className="space-y-1 text-slate-600 dark:text-slate-300">
                    <li>
                      <span className="font-semibold text-sky-500 dark:text-cyan-400">
                        Face width:
                      </span>{' '}
                      Temperature (wider = warmer)
                    </li>
                    <li>
                      <span className="font-semibold text-sky-500 dark:text-cyan-400">
                        Eye size:
                      </span>{' '}
                      Relative humidity (larger = more humid)
                    </li>
                    <li>
                      <span className="font-semibold text-sky-500 dark:text-cyan-400">
                        Eyebrow angle:
                      </span>{' '}
                      Wind speed (steeper = windier)
                    </li>
                    <li>
                      <span className="font-semibold text-sky-500 dark:text-cyan-400">
                        Mouth curve:
                      </span>{' '}
                      Precipitation (deeper = higher chance)
                    </li>
                    <li>
                      <span className="font-semibold text-sky-500 dark:text-cyan-400">
                        Nose length:
                      </span>{' '}
                      Apparent temperature (longer = feels warmer)
                    </li>
                  </ul>
                  <p className="mt-2 text-[0.65rem] text-slate-400 italic">
                    Values are normalized across the visible records.
                  </p>
                </div>
              )}
            </div>
          </div>

          <p className="mt-0.5 max-w-2xl text-xs text-slate-500 dark:text-slate-400">
            Each face represents one forecast record, encoding 5 variables at once. Hover over any
            face to view exact values.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {availableSources.length > 1 && (
            <SegmentedControl<ChernoffSourceKey>
              label="Source"
              value={effectiveSource}
              options={availableSources as ChernoffSourceKey[]}
              onChange={setSource}
            />
          )}
          <SegmentedControl<number>
            label="Faces"
            value={count}
            options={FACE_COUNT_CHOICES}
            disabledValues={disabledCounts}
            onChange={setCount}
          />
        </div>
      </div>

      {error !== null && (
        <p role="alert" className="text-sm text-rose-500 dark:text-rose-400">
          {error.message}
        </p>
      )}

      {faces.length === 0 && !isBusy ? (
        <EmptyState
          icon={Shapes}
          title="No faces to draw"
          message="The weather service did not return usable data for this source, so there are no records to encode."
        />
      ) : (
        <>
          {/* Each face in a glass card with subtle hover scale(1.05) transition */}
          <ul
            className={cn(
              'grid gap-3 sm:gap-4',
              GRID_CLASSES[columns] ?? GRID_CLASSES[4],
            )}
            aria-busy={isBusy}
          >
            {faces.map(({ face, spec }, index) => (
              <li
                key={`${face.label}-${index}`}
                className="surface-card group relative flex flex-col items-center justify-between p-4 rounded-2xl border border-slate-200/80 bg-white/75 backdrop-blur-md transition-all duration-300 hover:scale-[1.05] hover:bg-white/95 hover:border-sky-400/40 dark:border-white/10 dark:bg-white/5 dark:hover:bg-white/10 dark:hover:border-cyan-400/40 hover:shadow-xl hover:shadow-cyan-500/10 cursor-default"
                tabIndex={0}
                aria-label={`${face.label}. ${face.summary}`}
              >
                <div className="flex-1 flex items-center justify-center py-1">
                  <FaceSvg spec={spec} title={`${face.label}: ${face.summary}`} />
                </div>
                <div className="mt-2 text-center">
                  <p className="text-xs font-semibold text-slate-900 dark:text-white">
                    {face.label}
                  </p>
                  <p className="mt-0.5 text-[0.7rem] leading-snug text-slate-500 dark:text-slate-400">
                    {face.summary}
                  </p>
                </div>

                {/* Detail tooltip on hover and keyboard focus */}
                <div
                  role="tooltip"
                  className={cn(
                    'surface-card pointer-events-none absolute bottom-full left-1/2 z-30 mb-2 w-max max-w-[16rem]',
                    '-translate-x-1/2 rounded-xl border border-slate-200/90 dark:border-white/15 bg-white/95 dark:bg-slate-900/95 px-3.5 py-2.5',
                    'text-xs text-slate-900 dark:text-white opacity-0 shadow-2xl backdrop-blur-xl transition-all duration-200',
                    'group-hover:opacity-100 group-focus-within:opacity-100 scale-95 group-hover:scale-100',
                  )}
                >
                  <p className="font-bold border-b border-slate-200 dark:border-white/10 pb-1 mb-1.5">
                    {face.label}
                  </p>
                  {data !== null &&
                    data.features.map((feature) => (
                      <p
                        key={feature.variable}
                        className="mt-0.5 flex justify-between gap-3 text-slate-500 dark:text-slate-400"
                      >
                        <span>{feature.label}:</span>
                        <span className="font-semibold text-slate-900 dark:text-cyan-300">
                          {face.values[valueKeyForVariable(feature.variable)] ?? '—'}{' '}
                          <span className="text-[0.65rem] font-normal">{feature.unit}</span>
                        </span>
                      </p>
                    ))}
                </div>
              </li>
            ))}
          </ul>

          {isBusy && (
            <p className="text-xs text-cyan-400 animate-pulse font-medium" role="status">
              Preparing faces…
            </p>
          )}
        </>
      )}

      {data !== null && <ChernoffLegend source={data} faces={faces.length} />}
    </section>
  )
}