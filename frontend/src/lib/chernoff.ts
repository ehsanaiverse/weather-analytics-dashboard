/**
 * Chernoff Faces: normalisation and geometry.
 *
 * A Chernoff face encodes several variables of one forecast record at once, so
 * faces can be compared side by side. This module is a faithful port of
 * `app/utils/chernoff.py` in the Python project; the two must agree, because the
 * Streamlit dashboard draws the same faces with Plotly and a test in the Python
 * suite (`tests/api/test_chernoff_geometry_sync.py`) parses the constants below
 * and fails if they ever drift apart.
 *
 * Feature mapping, unchanged from the original implementation:
 *
 * | Weather variable        | Facial feature  | Higher value looks like     |
 * | ----------------------- | --------------- | --------------------------- |
 * | Temperature             | face width      | wider                       |
 * | Relative humidity       | eye size        | larger eyes                 |
 * | Wind speed              | eyebrow angle   | steeper, more angled brows  |
 * | Precipitation probability| mouth curvature| flatter, then deeper curve  |
 * | Apparent temperature    | nose length     | longer nose                 |
 *
 * ## Coordinate system
 *
 * Everything is expressed in "cell units": one grid cell is `1 x 1` and a face is
 * centred inside it. The y axis runs downwards, so a *smaller* y is higher up.
 * SVG shares that convention, which is why the Python and TypeScript geometry
 * match without a flip.
 *
 * ## Where the numbers come from
 *
 * The backend already min-max normalises each variable across the faces it
 * returns, and sends the result as `spec` (always within `[0, 1]`), so this
 * module's job is `spec -> geometry`. `normaliseSeries()` is a port of the same
 * rule kept as the reference implementation: the tests assert it against the
 * Python behaviour, and `resolveSpec()` relies on the same clamping.
 */

/** Normalised encodings driving one face, each within `[0, 1]`. */
export interface FaceSpec {
  readonly temperature: number
  readonly humidity: number
  readonly wind: number
  readonly precipitation: number
  readonly apparentTemperature: number
}

/** Concrete drawing coordinates for one face, in cell units. */
export interface FaceGeometry {
  readonly cx: number
  readonly cy: number
  readonly headRx: number
  readonly headRy: number
  readonly eyeRadius: number
  readonly eyeDx: number
  readonly eyeY: number
  readonly browHalfWidth: number
  readonly browRise: number
  readonly browY: number
  readonly mouthHalfWidth: number
  readonly mouthDepth: number
  readonly mouthY: number
  readonly noseTop: number
  readonly noseLength: number
}

/* -------------------------------------------------------------------------- */
/* Constants - mirrored from app/utils/chernoff.py                             */
/* -------------------------------------------------------------------------- */

/** Half-height of the head; the head is an ellipse, so this is half its height. */
export const HEAD_BASE_RADIUS = 0.32

/** Temperature -> horizontal half-width, as a multiple of the base radius. */
export const HEAD_WIDTH_RANGE: readonly [number, number] = [0.72, 1.2]

/** Relative humidity -> eye radius. */
export const EYE_RADIUS_RANGE: readonly [number, number] = [0.028, 0.078]

/** Eye separation, as a multiple of the head half-width. */
export const EYE_SPREAD = 0.4

/** Eyebrow half-length, as a multiple of the head half-width. */
export const BROW_SPREAD = 0.17

/** Mouth half-width, as a multiple of the head half-width. */
export const MOUTH_SPREAD = 0.34

/** Wind speed -> eyebrow tilt in degrees; negative is flat, positive is steep. */
export const BROW_ANGLE_RANGE: readonly [number, number] = [-30, 32]

/** Precipitation probability -> how far the mouth deviates from its endpoints. */
export const MOUTH_DEPTH_RANGE: readonly [number, number] = [-0.015, 0.1]

/** Apparent temperature -> nose length. */
export const NOSE_LENGTH_RANGE: readonly [number, number] = [0.045, 0.125]

/** Vertical placement of the eyes, relative to the face centre. */
export const EYE_OFFSET_Y = -0.062

/** Vertical placement of the eyebrows, relative to the face centre. */
export const BROW_OFFSET_Y = -0.195

/** Vertical start of the nose, relative to the face centre. */
export const NOSE_OFFSET_Y = 0.005

/** Vertical placement of the mouth, relative to the face centre. */
export const MOUTH_OFFSET_Y = 0.175

/** Horizontal width of the little hook at the bottom of the nose. */
export const NOSE_HOOK_WIDTH = 0.035

/** SVG user units per cell, so stroke widths match the Plotly rendering. */
export const CELL_PX = 165

/** Vertical offset of the face centre inside its cell, leaving room for labels. */
export const CENTRE_OFFSET_Y = 0.45

/** Normalised value used for a constant or entirely missing variable. */
export const NEUTRAL = 0.5

/** Spans at or below this are treated as "no variation". */
export const EPSILON = 1e-9

/** Face counts the UI offers. */
export const FACE_COUNT_CHOICES: readonly number[] = [4, 6, 8, 12]

/** Number of faces requested by default. */
export const DEFAULT_FACE_COUNT = 6

/** Spec used when nothing usable is known about a record. */
export const NEUTRAL_SPEC: FaceSpec = {
  temperature: NEUTRAL,
  humidity: NEUTRAL,
  wind: NEUTRAL,
  precipitation: NEUTRAL,
  apparentTemperature: NEUTRAL,
}

/* -------------------------------------------------------------------------- */
/* Normalisation                                                              */
/* -------------------------------------------------------------------------- */

/** Clamp a value into `[0, 1]`. */
export function clampUnit(value: number): number {
  if (Number.isNaN(value)) {
    return NEUTRAL
  }
  return Math.min(1, Math.max(0, value))
}

/** Convert an unknown value to a finite number, or `null` when unusable. */
export function coerceNumber(value: unknown): number | null {
  if (value === null || value === undefined || typeof value === 'boolean') {
    return null
  }
  const number = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(number) ? number : null
}

/** Median of a non-empty list of finite numbers. */
export function median(values: readonly number[]): number {
  const ordered = [...values].sort((a, b) => a - b)
  const middle = Math.floor(ordered.length / 2)
  return ordered.length % 2 === 1
    ? (ordered[middle] ?? NEUTRAL)
    : ((ordered[middle - 1] ?? 0) + (ordered[middle] ?? 0)) / 2
}

/**
 * Min-max scale a series into `[0, 1]`.
 *
 * Port of `normalise()` in `app/utils/chernoff.py`:
 *
 *  - missing values are replaced by the median of the available ones,
 *  - a constant series (or one with nothing usable) becomes the neutral 0.5,
 *  - the result is always within `[0, 1]`.
 *
 * @param values - Raw measurements in record order.
 */
export function normaliseSeries(values: readonly unknown[]): number[] {
  const numbers = values.map(coerceNumber)
  const usable = numbers.filter((value): value is number => value !== null)
  if (usable.length === 0) {
    return numbers.map(() => NEUTRAL)
  }

  const fill = median(usable)
  const filled = numbers.map((value) => (value === null ? fill : value))

  const low = Math.min(...filled)
  const span = Math.max(...filled) - low
  if (span <= EPSILON) {
    return filled.map(() => NEUTRAL)
  }

  return filled.map((value) => clampUnit((value - low) / span))
}

/**
 * Read a normalised spec defensively.
 *
 * The backend guarantees `[0, 1]` values, but a hand-edited or cached response
 * should never produce a broken face: anything non-finite or out of range falls
 * back to the neutral midpoint.
 */
export function resolveSpec(candidate: unknown): FaceSpec {
  if (typeof candidate !== 'object' || candidate === null) {
    return NEUTRAL_SPEC
  }
  const raw = candidate as Partial<Record<keyof FaceSpec, unknown>>
  const read = (key: keyof FaceSpec): number => {
    const value = coerceNumber(raw[key])
    return value === null ? NEUTRAL : clampUnit(value)
  }

  return {
    temperature: read('temperature'),
    humidity: read('humidity'),
    wind: read('wind'),
    precipitation: read('precipitation'),
    apparentTemperature: read('apparentTemperature'),
  }
}

/* -------------------------------------------------------------------------- */
/* Reported-value keys                                                         */
/* -------------------------------------------------------------------------- */

/**
 * The key used in `ChernoffFace.values` for a legend variable.
 *
 * The backend keys the reported values by source column name while the legend
 * arrives keyed by variable name; the two only differ for the apparent
 * temperature, and the mapping lives here so the legend and the face tooltips
 * cannot disagree about a column.
 */
export function valueKeyForVariable(variable: string): string {
  return variable === 'apparent_temperature' ? 'apparent_temperature' : variable
}

/* -------------------------------------------------------------------------- */
/* Geometry                                                                   */
/* -------------------------------------------------------------------------- */

/** Map a normalised value onto a bounded geometry range. */
export function lerp(normalised: number, bounds: readonly [number, number]): number {
  const [low, high] = bounds
  return low + (high - low) * clampUnit(normalised)
}

/**
 * Turn normalised encodings into drawing coordinates.
 *
 * Every feature is derived from `headRx`, so a wider face also has wider eyes,
 * brows and mouth and nothing can escape the head outline.
 */
export function faceGeometry(spec: FaceSpec, cx: number, cy: number): FaceGeometry {
  const headRy = HEAD_BASE_RADIUS
  const headRx = headRy * lerp(spec.temperature, HEAD_WIDTH_RANGE)
  const eyeDx = EYE_SPREAD * headRx
  const browHalfWidth = BROW_SPREAD * headRx
  const browAngle = lerp(spec.wind, BROW_ANGLE_RANGE)

  return {
    cx,
    cy,
    headRx,
    headRy,
    eyeRadius: lerp(spec.humidity, EYE_RADIUS_RANGE),
    eyeDx,
    eyeY: cy + EYE_OFFSET_Y,
    browHalfWidth,
    browRise: browHalfWidth * Math.tan((browAngle * Math.PI) / 180),
    browY: cy + BROW_OFFSET_Y,
    mouthHalfWidth: MOUTH_SPREAD * headRx,
    mouthDepth: lerp(spec.precipitation, MOUTH_DEPTH_RANGE),
    mouthY: cy + MOUTH_OFFSET_Y,
    noseTop: cy + NOSE_OFFSET_Y,
    noseLength: lerp(spec.apparentTemperature, NOSE_LENGTH_RANGE),
  }
}

/** Convert a cell-unit coordinate to SVG user units, never in scientific notation. */
export function toSvg(value: number): string {
  return (value * CELL_PX).toFixed(4)
}

/** SVG `d` attribute for a straight polyline, used by the nose. */
export function nosePath(geometry: FaceGeometry): string {
  const { cx, noseTop, noseLength } = geometry
  return [
    `M ${toSvg(cx)},${toSvg(noseTop)}`,
    `L ${toSvg(cx)},${toSvg(noseTop + noseLength)}`,
    `L ${toSvg(cx + NOSE_HOOK_WIDTH)},${toSvg(noseTop + noseLength)}`,
  ].join(' ')
}

/**
 * SVG `d` attribute for the mouth.
 *
 * A quadratic Bezier whose control point sits twice the intended deviation away
 * from the endpoints, so the curve's midpoint moves by exactly `mouthDepth`.
 */
export function mouthPath(geometry: FaceGeometry): string {
  const { cx, mouthHalfWidth, mouthDepth, mouthY } = geometry
  return [
    `M ${toSvg(cx - mouthHalfWidth)},${toSvg(mouthY)}`,
    `Q ${toSvg(cx)},${toSvg(mouthY + 2 * mouthDepth)}`,
    `${toSvg(cx + mouthHalfWidth)},${toSvg(mouthY)}`,
  ].join(' ')
}