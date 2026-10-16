import { describe, expect, it } from 'vitest'

import {
  BROW_ANGLE_RANGE,
  CELL_PX,
  DEFAULT_FACE_COUNT,
  EYE_RADIUS_RANGE,
  FACE_COUNT_CHOICES,
  HEAD_BASE_RADIUS,
  HEAD_WIDTH_RANGE,
  MOUTH_DEPTH_RANGE,
  NEUTRAL,
  NEUTRAL_SPEC,
  NOSE_LENGTH_RANGE,
  clampUnit,
  coerceNumber,
  faceGeometry,
  lerp,
  median,
  mouthPath,
  normaliseSeries,
  nosePath,
  resolveSpec,
  toSvg,
} from './chernoff'
import type { FaceGeometry, FaceSpec } from './chernoff'

/**
 * These expectations were produced by `app/utils/chernoff.py`, so a change on
 * either side of the port shows up here as a failure rather than as two
 * dashboards quietly disagreeing.
 */
const PYTHON_GEOMETRY: ReadonlyArray<readonly [string, FaceSpec, Record<string, number>]> = [
  [
    'neutral spec',
    NEUTRAL_SPEC,
    {
      headRx: 0.3072,
      headRy: 0.32,
      eyeRadius: 0.053,
      eyeDx: 0.12288,
      eyeY: 0.388,
      browHalfWidth: 0.052224,
      browRise: 0.000912,
      browY: 0.255,
      mouthHalfWidth: 0.104448,
      mouthDepth: 0.0425,
      mouthY: 0.625,
      noseTop: 0.455,
      noseLength: 0.085,
    },
  ],
  [
    'cold, dry, calm, dry-mouth, short nose',
    { temperature: 0, humidity: 0, wind: 0, precipitation: 0, apparentTemperature: 0 },
    {
      headRx: 0.2304,
      headRy: 0.32,
      eyeRadius: 0.028,
      eyeDx: 0.09216,
      eyeY: 0.388,
      browHalfWidth: 0.039168,
      browRise: -0.022614,
      browY: 0.255,
      mouthHalfWidth: 0.078336,
      mouthDepth: -0.015,
      mouthY: 0.625,
      noseTop: 0.455,
      noseLength: 0.045,
    },
  ],
  [
    'warm, humid, windy, deep mouth, long nose',
    { temperature: 1, humidity: 1, wind: 1, precipitation: 1, apparentTemperature: 1 },
    {
      headRx: 0.384,
      headRy: 0.32,
      eyeRadius: 0.078,
      eyeDx: 0.1536,
      eyeY: 0.388,
      browHalfWidth: 0.06528,
      browRise: 0.040791,
      browY: 0.255,
      mouthHalfWidth: 0.13056,
      mouthDepth: 0.1,
      mouthY: 0.625,
      noseTop: 0.455,
      noseLength: 0.125,
    },
  ],
  [
    'mixed values',
    { temperature: 0.1, humidity: 1, wind: 0.85, precipitation: 0.5, apparentTemperature: 0.17 },
    {
      headRx: 0.24576,
      headRy: 0.32,
      eyeRadius: 0.078,
      eyeDx: 0.098304,
      eyeY: 0.388,
      browHalfWidth: 0.041779,
      browRise: 0.017477,
      browY: 0.255,
      mouthHalfWidth: 0.083558,
      mouthDepth: 0.0425,
      mouthY: 0.625,
      noseTop: 0.455,
      noseLength: 0.0586,
    },
  ],
]

describe('normalisation', () => {
  it('scales a series into [0, 1]', () => {
    expect(normaliseSeries([10, 20, 30])).toEqual([0, 0.5, 1])
  })

  it('fills missing values with the median of the available ones', () => {
    expect(normaliseSeries([10, 20, 30, null, 20])).toEqual([0, 0.5, 1, 0.5, 0.5])
  })

  it('returns the neutral value for a constant series', () => {
    expect(normaliseSeries([5, 5, 5])).toEqual([NEUTRAL, NEUTRAL, NEUTRAL])
  })

  it('returns the neutral value when nothing is usable', () => {
    expect(normaliseSeries([null, undefined, Number.NaN])).toEqual([NEUTRAL, NEUTRAL, NEUTRAL])
  })

  it('handles negative values', () => {
    expect(normaliseSeries([-10, 0, 10])).toEqual([0, 0.5, 1])
  })

  it('parses numeric strings like the Python implementation', () => {
    expect(normaliseSeries(['12', '8', '4'])).toEqual([1, 0.5, 0])
  })

  it('ignores booleans and unusable text', () => {
    expect(normaliseSeries([true, 'abc', 10, 20])).toEqual([NEUTRAL, NEUTRAL, 0, 1])
  })

  it('always stays within [0, 1]', () => {
    for (const series of [[1], [1, 2, 3], [-5, 5], [Number.MAX_SAFE_INTEGER, 0]]) {
      for (const value of normaliseSeries(series)) {
        expect(value).toBeGreaterThanOrEqual(0)
        expect(value).toBeLessThanOrEqual(1)
      }
    }
  })

  it('preserves the input order and length', () => {
    const series = [3, 1, 2]
    expect(normaliseSeries(series)).toHaveLength(series.length)
    expect(normaliseSeries(series)[0]).toBe(1)
  })
})

describe('scalar helpers', () => {
  it('clamps into [0, 1] and treats NaN as neutral', () => {
    expect(clampUnit(-1)).toBe(0)
    expect(clampUnit(2)).toBe(1)
    expect(clampUnit(0.25)).toBe(0.25)
    expect(clampUnit(Number.NaN)).toBe(NEUTRAL)
  })

  it('coerces usable values and rejects the rest', () => {
    expect(coerceNumber(12)).toBe(12)
    expect(coerceNumber('12.5')).toBe(12.5)
    expect(coerceNumber(null)).toBeNull()
    expect(coerceNumber(undefined)).toBeNull()
    expect(coerceNumber(true)).toBeNull()
    expect(coerceNumber('abc')).toBeNull()
    expect(coerceNumber(Number.POSITIVE_INFINITY)).toBeNull()
  })

  it('computes the median for odd and even lengths', () => {
    expect(median([1, 3, 5])).toBe(3)
    expect(median([1, 2, 3, 4])).toBe(2.5)
  })

  it('interpolates inside a bounded range and clamps outside it', () => {
    expect(lerp(0, [2, 4])).toBe(2)
    expect(lerp(1, [2, 4])).toBe(4)
    expect(lerp(0.5, [2, 4])).toBe(3)
    expect(lerp(5, [2, 4])).toBe(4)
    expect(lerp(-5, [2, 4])).toBe(2)
  })
})

describe('resolveSpec', () => {
  it('passes valid values through', () => {
    const spec = { temperature: 0.1, humidity: 1, wind: 0.5, precipitation: 0, apparentTemperature: 0.75 }
    expect(resolveSpec(spec)).toEqual(spec)
  })

  it('clamps values that are outside [0, 1]', () => {
    expect(resolveSpec({ temperature: 1.7, humidity: -0.4 }).temperature).toBe(1)
    expect(resolveSpec({ temperature: 1.7, humidity: -0.4 }).humidity).toBe(0)
  })

  it('falls back to neutral for missing, non-numeric or absent specs', () => {
    expect(resolveSpec(null)).toEqual(NEUTRAL_SPEC)
    expect(resolveSpec(undefined)).toEqual(NEUTRAL_SPEC)
    expect(resolveSpec('nonsense')).toEqual(NEUTRAL_SPEC)
    expect(resolveSpec({ temperature: 'warm' }).temperature).toBe(NEUTRAL)
    expect(resolveSpec({}).wind).toBe(NEUTRAL)
  })
})

describe('feature mapping', () => {
  const specWith = (key: keyof FaceSpec, value: number): FaceSpec => ({
    ...NEUTRAL_SPEC,
    [key]: value,
  })

  it('maps temperature to face width', () => {
    const narrow = faceGeometry(specWith('temperature', 0), 0.5, 0.45)
    const wide = faceGeometry(specWith('temperature', 1), 0.5, 0.45)

    expect(narrow.headRx).toBeCloseTo(HEAD_BASE_RADIUS * HEAD_WIDTH_RANGE[0], 10)
    expect(wide.headRx).toBeCloseTo(HEAD_BASE_RADIUS * HEAD_WIDTH_RANGE[1], 10)
    expect(wide.headRx).toBeGreaterThan(narrow.headRx)
    expect(narrow.headRy).toBe(wide.headRy)
  })

  it('maps humidity to eye size', () => {
    const dry = faceGeometry(specWith('humidity', 0), 0.5, 0.45)
    const wet = faceGeometry(specWith('humidity', 1), 0.5, 0.45)

    expect(dry.eyeRadius).toBeCloseTo(EYE_RADIUS_RANGE[0], 10)
    expect(wet.eyeRadius).toBeCloseTo(EYE_RADIUS_RANGE[1], 10)
    expect(wet.eyeRadius).toBeGreaterThan(dry.eyeRadius)
  })

  it('maps wind speed to eyebrow angle', () => {
    const calm = faceGeometry(specWith('wind', 0), 0.5, 0.45)
    const windy = faceGeometry(specWith('wind', 1), 0.5, 0.45)

    // A calm brow tilts down (negative rise), a windy one tilts up.
    expect(calm.browRise).toBeLessThan(0)
    expect(windy.browRise).toBeGreaterThan(0)
    expect(BROW_ANGLE_RANGE[0]).toBeLessThan(0)
    expect(BROW_ANGLE_RANGE[1]).toBeGreaterThan(0)
  })

  it('maps precipitation probability to mouth curvature', () => {
    const dry = faceGeometry(specWith('precipitation', 0), 0.5, 0.45)
    const wet = faceGeometry(specWith('precipitation', 1), 0.5, 0.45)

    expect(dry.mouthDepth).toBeCloseTo(MOUTH_DEPTH_RANGE[0], 10)
    expect(wet.mouthDepth).toBeCloseTo(MOUTH_DEPTH_RANGE[1], 10)
    expect(wet.mouthDepth).toBeGreaterThan(dry.mouthDepth)
  })

  it('maps apparent temperature to nose length', () => {
    const cold = faceGeometry(specWith('apparentTemperature', 0), 0.5, 0.45)
    const warm = faceGeometry(specWith('apparentTemperature', 1), 0.5, 0.45)

    expect(cold.noseLength).toBeCloseTo(NOSE_LENGTH_RANGE[0], 10)
    expect(warm.noseLength).toBeCloseTo(NOSE_LENGTH_RANGE[1], 10)
    expect(warm.noseLength).toBeGreaterThan(cold.noseLength)
  })

  it('is monotonic across the whole range for every feature', () => {
    const samples = [0, 0.25, 0.5, 0.75, 1].map((value) =>
      faceGeometry(
        {
          temperature: value,
          humidity: value,
          wind: value,
          precipitation: value,
          apparentTemperature: value,
        },
        0.5,
        0.45,
      ),
    )

    const increasing = (pick: (geometry: FaceGeometry) => number): void => {
      for (let index = 1; index < samples.length; index += 1) {
        const previous = pick(samples[index - 1] as FaceGeometry)
        const current = pick(samples[index] as FaceGeometry)
        expect(current).toBeGreaterThan(previous)
      }
    }

    increasing((geometry) => geometry.headRx)
    increasing((geometry) => geometry.eyeRadius)
    increasing((geometry) => geometry.browRise)
    increasing((geometry) => geometry.mouthDepth)
    increasing((geometry) => geometry.noseLength)
  })

  it('keeps every feature inside the head outline', () => {
    const extremes: readonly FaceSpec[] = [
      { temperature: 0, humidity: 0, wind: 0, precipitation: 0, apparentTemperature: 0 },
      { temperature: 1, humidity: 1, wind: 1, precipitation: 1, apparentTemperature: 1 },
      NEUTRAL_SPEC,
    ]

    for (const spec of extremes) {
      const geometry = faceGeometry(spec, 0.5, 0.45)
      const left = geometry.cx - geometry.headRx
      const right = geometry.cx + geometry.headRx
      const top = geometry.cy - geometry.headRy
      const bottom = geometry.cy + geometry.headRy

      // Eyes: outer edge of each eye.
      expect(geometry.cx - geometry.eyeDx - geometry.eyeRadius).toBeGreaterThan(left)
      expect(geometry.cx + geometry.eyeDx + geometry.eyeRadius).toBeLessThan(right)
      expect(geometry.eyeY - geometry.eyeRadius).toBeGreaterThan(top)
      expect(geometry.eyeY + geometry.eyeRadius).toBeLessThan(bottom)

      // Eyebrows: outer end plus the rise.
      expect(geometry.cx - geometry.eyeDx - geometry.browHalfWidth).toBeGreaterThan(left)
      expect(geometry.cx + geometry.eyeDx + geometry.browHalfWidth).toBeLessThan(right)
      expect(geometry.browY - geometry.browRise).toBeGreaterThan(top)
      expect(geometry.browY + geometry.browRise).toBeLessThan(bottom)

      // Mouth: endpoints, plus the curve's own extreme. The Bezier control
      // point sits twice as far away but is never drawn, so it is not checked.
      expect(geometry.cx - geometry.mouthHalfWidth).toBeGreaterThan(left)
      expect(geometry.cx + geometry.mouthHalfWidth).toBeLessThan(right)
      expect(geometry.mouthY + geometry.mouthDepth).toBeLessThan(bottom)
      expect(geometry.mouthY + geometry.mouthDepth).toBeGreaterThan(top)

      // Nose: tip and hook.
      expect(geometry.noseTop).toBeGreaterThan(top)
      expect(geometry.noseTop + geometry.noseLength).toBeLessThan(bottom)
      expect(geometry.noseTop + geometry.noseLength).toBeGreaterThan(geometry.eyeY)
    }
  })

  it('produces positive radii and lengths for any spec', () => {
    for (const spec of [NEUTRAL_SPEC, { ...NEUTRAL_SPEC, temperature: 0 }]) {
      const geometry = faceGeometry(spec, 0.5, 0.45)
      expect(geometry.headRx).toBeGreaterThan(0)
      expect(geometry.eyeRadius).toBeGreaterThan(0)
      expect(geometry.noseLength).toBeGreaterThan(0)
      expect(geometry.mouthHalfWidth).toBeGreaterThan(0)
    }
  })
})

describe('parity with the Python implementation', () => {
  it.each(PYTHON_GEOMETRY)('matches app/utils/chernoff.py for %s', (_name, spec, expected) => {
    const geometry = faceGeometry(spec, 0.5, 0.45)

    for (const [key, value] of Object.entries(expected)) {
      expect(geometry[key as keyof FaceGeometry]).toBeCloseTo(value, 5)
    }
  })

  it('emits SVG paths matching the Python path strings', () => {
    const geometry = faceGeometry(
      { temperature: 0.1, humidity: 1, wind: 0.85, precipitation: 0.5, apparentTemperature: 0.17 },
      0.5,
      0.45,
    )

    // Python emits these in cell units (rounded to 4 dp by `_n()`); Plotly then
    // scales them into pixels. `toSvg` scales first and rounds once, so the two
    // agree to within the rounding of 4 decimal places in cell units.
    const pythonCellUnits = [
      'M 0.5000,0.4550 L 0.5000,0.5136 L 0.5350,0.5136',
      'M 0.4164,0.6250 Q 0.5000,0.7100 0.5836,0.6250',
    ]
    const emitted = [nosePath(geometry), mouthPath(geometry)]

    const numbers = (path: string): number[] =>
      (path.match(/-?\d+\.\d+/g) ?? []).map(Number)

    emitted.forEach((path, index) => {
      const expected = pythonCellUnits[index]
      expect(expected).toBeDefined()
      if (expected === undefined) {
        return
      }
      expect(path.replace(/,/g, ' ').split(' ').filter((token) => token !== '')).toHaveLength(
        expected.replace(/,/g, ' ').split(' ').filter((token) => token !== '').length,
      )
      const actualNumbers = numbers(path)
      const expectedNumbers = numbers(expected).map((value) => value * CELL_PX)
      expect(actualNumbers).toHaveLength(expectedNumbers.length)
      actualNumbers.forEach((value, position) => {
        expect(value).toBeCloseTo(expectedNumbers[position] ?? 0, 1)
      })
    })
  })
})

describe('svg conversion', () => {
  it('scales cell units into SVG units', () => {
    expect(toSvg(0.5)).toBe((0.5 * CELL_PX).toFixed(4))
  })

  it('never emits scientific notation', () => {
    expect(toSvg(0.0000001)).toMatch(/^0\.0000$|^\d+\.\d{4}$/)
  })

  it('always emits four decimals', () => {
    expect(toSvg(0.455)).toBe((0.455 * CELL_PX).toFixed(4))
    expect(toSvg(0.455)).toMatch(/^\d+\.\d{4}$/)
  })
})

describe('face count choices', () => {
  it('offers 4, 6, 8 and 12 faces with a default of 6', () => {
    expect(FACE_COUNT_CHOICES).toEqual([4, 6, 8, 12])
    expect(DEFAULT_FACE_COUNT).toBe(6)
    expect(FACE_COUNT_CHOICES).toContain(DEFAULT_FACE_COUNT)
  })
})