import { describe, expect, it } from 'vitest'

import {
  EM_DASH,
  formatAge,
  formatCoordinates,
  formatLocalDate,
  formatLocalDateTime,
  formatLocalTime,
  formatLocationClock,
  formatMeasurement,
  formatUtcInstant,
  formatUtcOffset,
  parseNaiveLocal,
} from './format'

const KARACHI = 5 * 3600
const LONDON = 1 * 3600
const REYKJAVIK = 0

describe('naive local timestamps', () => {
  it('keeps the location wall clock instead of converting it', () => {
    // The backend already sends 22:00 local for Abbottabad (UTC+5); parsing must
    // not shift it to 17:00 UTC.
    expect(parseNaiveLocal('2026-10-02T22:00:00')?.toISOString()).toBe(
      '2026-10-02T22:00:00.000Z',
    )
  })

  it('accepts a bare date as midnight', () => {
    expect(parseNaiveLocal('2026-10-03')?.toISOString()).toBe('2026-10-03T00:00:00.000Z')
  })

  it('returns null for missing or unparseable values', () => {
    expect(parseNaiveLocal(null)).toBeNull()
    expect(parseNaiveLocal(undefined)).toBeNull()
    expect(parseNaiveLocal('')).toBeNull()
    expect(parseNaiveLocal('not-a-date')).toBeNull()
  })
})

describe('local formatting', () => {
  it('renders the wall clock the backend sent, unchanged', () => {
    // The same formatter serves three locations whose wall clocks differ; it must
    // apply no further conversion, only render what it was given.
    expect(formatLocalTime('2026-10-02T22:00:00')).toBe('22:00')
    expect(formatLocalTime('2026-10-02T17:00:00')).toBe('17:00')
    expect(formatLocalTime('2026-10-03T00:00:00')).toBe('00:00')
  })

  it('renders the local date and weekday', () => {
    expect(formatLocalDate('2026-10-03T01:00:00')).toContain('03 Oct')
  })

  it('renders a full local date-time for the observation time', () => {
    expect(formatLocalDateTime('2026-10-02T22:30:00')).toContain('22:30')
    expect(formatLocalDateTime('2026-10-02T22:30:00')).toContain('02/10/2026')
  })

  it('falls back to an em dash when the provider reported no time', () => {
    expect(formatLocalTime(null)).toBe(EM_DASH)
    expect(formatLocalDate(undefined)).toBe(EM_DASH)
    expect(formatLocalDateTime(null)).toBe(EM_DASH)
  })
})

describe('location clock for a real instant', () => {
  it('shifts a true instant by the location offset', () => {
    const instant = new Date('2026-10-02T17:00:00.000Z')
    expect(formatLocationClock(KARACHI, instant)).toBe('22:00')
    expect(formatLocationClock(LONDON, instant)).toBe('18:00')
    expect(formatLocationClock(REYKJAVIK, instant)).toBe('17:00')
  })

  it('rolls the date over when the offset pushes past midnight', () => {
    const instant = new Date('2026-10-02T20:00:00.000Z')
    // 20:00 UTC is already the next day in UTC+5.
    expect(formatLocationClock(KARACHI, instant)).toBe('01:00')
  })
})

describe('utc offsets', () => {
  it('formats whole and half-hour offsets', () => {
    expect(formatUtcOffset(5 * 3600)).toBe('GMT+5')
    expect(formatUtcOffset(0)).toBe('GMT+0')
    expect(formatUtcOffset(-3 * 3600 - 1800)).toBe('GMT-3:30')
    expect(formatUtcOffset(5.5 * 3600)).toBe('GMT+5:30')
  })
})

describe('measurements', () => {
  it('formats numbers with the requested precision', () => {
    expect(formatMeasurement(19.34, 1)).toBe('19.3')
    expect(formatMeasurement(19.34, 0)).toBe('19')
  })

  it('uses an em dash for missing values, never zero', () => {
    expect(formatMeasurement(null)).toBe(EM_DASH)
    expect(formatMeasurement(undefined)).toBe(EM_DASH)
    expect(formatMeasurement(Number.NaN)).toBe(EM_DASH)
  })

  it('keeps a real zero visible', () => {
    expect(formatMeasurement(0, 1)).toBe('0.0')
    expect(formatMeasurement(0, 1)).toBe('0.0')
  })

  it('formats coordinates and ages', () => {
    expect(formatCoordinates(34.14631, 73.21168)).toBe('34.146, 73.212')
    expect(formatAge(20)).toBe('20s ago')
    expect(formatAge(120)).toBe('2 min ago')
    expect(formatAge(7200)).toBe('2 h ago')
    expect(formatAge(null)).toBe(EM_DASH)
  })
})

describe('utc instants', () => {
  it('labels the retrieval time as UTC', () => {
    const rendered = formatUtcInstant('2026-10-02T17:42:10.416706Z')
    expect(rendered).toContain('UTC')
    expect(rendered).toContain('17:42')
  })

  it('falls back to an em dash', () => {
    expect(formatUtcInstant(null)).toBe(EM_DASH)
    expect(formatUtcInstant('nonsense')).toBe(EM_DASH)
  })
})