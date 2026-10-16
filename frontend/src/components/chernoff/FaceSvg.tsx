import type { ReactNode } from 'react'

import { cn } from '../../lib/cn'
import {
  CELL_PX,
  CENTRE_OFFSET_Y,
  faceGeometry,
  mouthPath,
  nosePath,
  toSvg,
} from '../../lib/chernoff'
import type { FaceSpec } from '../../lib/chernoff'

/** Props for {@link FaceSvg}. */
export interface FaceSvgProps {
  /** Normalised encodings; every value is clamped to `[0, 1]` internally. */
  readonly spec: FaceSpec
  /** Accessible description, usually the period plus the reported values. */
  readonly title: string
  readonly className?: string
  /** Stroke widths match the Plotly rendering of the Streamlit dashboard. */
  readonly headStrokeWidth?: number
  readonly featureStrokeWidth?: number
}

/**
 * One Chernoff face, drawn as inline SVG.
 *
 * Reusable and presentational: it knows the geometry rules but nothing about
 * weather, API shapes or layout. Every element inherits its colour from the
 * active theme through Tailwind utilities, so light and dark mode need no
 * branching here.
 *
 * The viewBox is one cell in SVG user units (`CELL_PX`), which keeps stroke
 * widths constant while the face scales with its container.
 */
export function FaceSvg({
  spec,
  title,
  className,
  headStrokeWidth = 1.6,
  featureStrokeWidth = 1.8,
}: FaceSvgProps): ReactNode {
  const geometry = faceGeometry(spec, 0.5, CENTRE_OFFSET_Y)
  const { cx, cy, headRx, headRy, eyeRadius, eyeDx, eyeY, browHalfWidth, browRise, browY } =
    geometry

  return (
    <svg
      viewBox={`0 0 ${CELL_PX} ${CELL_PX}`}
      className={cn('h-auto w-full', className)}
      role="img"
      aria-label={title}
      focusable="false"
    >
      {/* Head */}
      <ellipse
        cx={toSvg(cx)}
        cy={toSvg(cy)}
        rx={toSvg(headRx)}
        ry={toSvg(headRy)}
        className="fill-elevated stroke-ink"
        strokeWidth={headStrokeWidth}
      />

      {/* Eyes: relative humidity drives the radius */}
      <circle
        cx={toSvg(cx - eyeDx)}
        cy={toSvg(eyeY)}
        r={toSvg(eyeRadius)}
        className="fill-ink stroke-ink"
        strokeWidth={headStrokeWidth - 0.6}
      />
      <circle
        cx={toSvg(cx + eyeDx)}
        cy={toSvg(eyeY)}
        r={toSvg(eyeRadius)}
        className="fill-ink stroke-ink"
        strokeWidth={headStrokeWidth - 0.6}
      />

      {/* Eyebrows: the inner end sits lower as the wind angle grows */}
      <line
        x1={toSvg(cx - eyeDx - browHalfWidth)}
        y1={toSvg(browY + browRise)}
        x2={toSvg(cx - eyeDx + browHalfWidth)}
        y2={toSvg(browY - browRise)}
        className="stroke-ink"
        strokeWidth={featureStrokeWidth}
        strokeLinecap="round"
      />
      <line
        x1={toSvg(cx + eyeDx - browHalfWidth)}
        y1={toSvg(browY - browRise)}
        x2={toSvg(cx + eyeDx + browHalfWidth)}
        y2={toSvg(browY + browRise)}
        className="stroke-ink"
        strokeWidth={featureStrokeWidth}
        strokeLinecap="round"
      />

      {/* Nose: apparent temperature drives the length */}
      <path
        d={nosePath(geometry)}
        className="fill-none stroke-ink"
        strokeWidth={headStrokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Mouth: precipitation probability drives the curvature */}
      <path
        d={mouthPath(geometry)}
        className="fill-none stroke-ink"
        strokeWidth={featureStrokeWidth}
        strokeLinecap="round"
      />
    </svg>
  )
}