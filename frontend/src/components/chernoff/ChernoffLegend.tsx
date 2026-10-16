import { Info } from 'lucide-react'
import type { ReactNode } from 'react'

import { valueKeyForVariable } from '../../lib/chernoff'
import type { ChernoffSource } from '../../api'

/** Props for {@link ChernoffLegend}. */
export interface ChernoffLegendProps {
  readonly source: ChernoffSource
  /** How many faces are on screen, for the wording of the notes. */
  readonly faces: number
}

/**
 * Feature-mapping legend plus the table of reported values.
 *
 * Kept separate from the grid so it can be rendered on its own, and so the
 * encoding is never a black box: the drawings are always accompanied by the
 * exact numbers behind them.
 */
export function ChernoffLegend({ source, faces }: ChernoffLegendProps): ReactNode {
  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
      <div className="surface-card p-4">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-ink">
          <Info className="h-4 w-4 text-accent" aria-hidden="true" />
          How to read a face
        </h3>
        <ul className="mt-3 space-y-2 text-sm text-muted">
          {source.features.map((feature) => (
            <li key={feature.variable} className="flex flex-wrap items-baseline gap-x-2">
              <span className="font-medium text-ink">{feature.feature}</span>
              <span>
                = {feature.label} ({feature.unit}) · higher looks {feature.direction}
              </span>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-xs text-muted">
          A variable that did not vary across these {faces} faces, or that was not reported, is
          drawn neutrally (0.5). Read the numbers below the faces before drawing conclusions.
        </p>
      </div>

      <div className="surface-card overflow-x-auto p-4">
        <h3 className="text-sm font-semibold text-ink">Reported values behind the faces</h3>
        <p className="mt-0.5 text-xs text-muted">
          Exactly what the provider returned for each record - the drawings above are only an
          encoding of these numbers.
        </p>
        <table className="mt-3 w-full text-left text-xs">
          <thead>
            <tr className="text-muted">
              <th scope="col" className="py-1 pr-3 font-medium">
                Period
              </th>
              {source.features.map((feature) => (
                <th key={feature.variable} scope="col" className="py-1 pr-3 font-medium">
                  {feature.label} ({feature.unit})
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-line tabular-nums">
            {source.faces.map((face, index) => (
              <tr key={`${face.label}-row-${index}`}>
                <th scope="row" className="py-1.5 pr-3 font-medium text-ink">
                  {face.label}
                </th>
                {source.features.map((feature) => (
                  <td key={feature.variable} className="py-1.5 pr-3 text-muted">
                    {face.values[valueKeyForVariable(feature.variable)] ?? '—'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}