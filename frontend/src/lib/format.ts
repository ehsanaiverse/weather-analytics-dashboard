/**
 * Small formatting helpers shared across the UI.
 *
 * These exist for one reason: the backend sends **naive local timestamps** such
 * as `2026-10-02T22:00:00`, already expressed in the queried location's time
 * zone. Passing such a string to `new Date()` makes JavaScript interpret it in
 * the *browser's* zone, which shifts every label by the viewer's offset.
 *
 * The safe options are:
 *  - use the pre-rendered `label` field the API already provides, or
 *  - call {@link formatLocalTime} with the response's `utcOffsetSeconds`, which
 *    treats the string as UTC and renders it at the location's offset.
 */

const PLACEHOLDER = '—'

const TIME_FORMATTER = new Intl.DateTimeFormat('en-GB', {
  hour: '2-digit',
  minute: '2-digit',
  timeZone: 'UTC',
  hour12: false,
})

const DATE_TIME_FORMATTER = new Intl.DateTimeFormat('en-GB', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  timeZone: 'UTC',
  hour12: false,
})

const DATE_FORMATTER = new Intl.DateTimeFormat('en-GB', {
  weekday: 'short',
  day: '2-digit',
  month: 'short',
  timeZone: 'UTC',
  hour12: false,
})

/** Em dash used wherever the provider reported nothing. */
export const EM_DASH = PLACEHOLDER

/** Format a measurement, or return an em dash when the provider reported none. */
export function formatMeasurement(
  value: number | null | undefined,
  decimals = 1,
  suffix = '',
): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return PLACEHOLDER
  }
  return `${value.toFixed(decimals)}${suffix}`
}

/**
 * Parse a naive local timestamp so its UTC fields hold the local wall clock.
 *
 * The backend sends forecast timestamps that are *already* expressed in the
 * queried location's time zone (`timezone=auto`), with no offset attached. They
 * are therefore parsed as though they were UTC and rendered with a UTC
 * formatter, which round-trips the wall clock untouched and never involves the
 * browser's own zone.
 *
 * Do not use this for real instants such as `meta.retrievedAt` (which carries
 * `Z`): use {@link formatUtcInstant}, or apply a location's offset to a `Date`
 * with {@link formatLocationClock}.
 *
 * @param naiveLocal - Timestamp without an offset, e.g. `2026-10-02T22:00:00`.
 */
export function parseNaiveLocal(naiveLocal: string | null | undefined): Date | null {
  if (!naiveLocal) {
    return null
  }
  const normalised = naiveLocal.includes('T') ? naiveLocal : `${naiveLocal}T00:00:00`
  const timestamp = Date.parse(`${normalised}Z`)
  return Number.isNaN(timestamp) ? null : new Date(timestamp)
}

/** Render a naive local timestamp as `HH:MM`. */
export function formatLocalTime(naiveLocal: string | null | undefined): string {
  const date = parseNaiveLocal(naiveLocal)
  return date === null ? PLACEHOLDER : TIME_FORMATTER.format(date)
}

/** Render a naive local timestamp as `Sat 03 Oct`. */
export function formatLocalDate(naiveLocal: string | null | undefined): string {
  const date = parseNaiveLocal(naiveLocal)
  return date === null ? PLACEHOLDER : DATE_FORMATTER.format(date)
}

/** Render a naive local timestamp as `02/10/2026, 22:30`. */
export function formatLocalDateTime(naiveLocal: string | null | undefined): string {
  const date = parseNaiveLocal(naiveLocal)
  return date === null ? PLACEHOLDER : DATE_TIME_FORMATTER.format(date)
}

/** Render a UTC instant (with an offset, as sent for `retrievedAt`) for display. */
export function formatUtcInstant(instant: string | null | undefined): string {
  if (!instant) {
    return PLACEHOLDER
  }
  const timestamp = Date.parse(instant)
  if (Number.isNaN(timestamp)) {
    return PLACEHOLDER
  }
  const date = new Date(timestamp)
  const time = TIME_FORMATTER.format(date)
  return `${DATE_FORMATTER.format(date)}, ${time} UTC`
}

/** Render an age in seconds as a short human phrase. */
export function formatAge(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || Number.isNaN(seconds)) {
    return PLACEHOLDER
  }
  if (seconds < 60) {
    return `${Math.round(seconds)}s ago`
  }
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) {
    return `${minutes} min ago`
  }
  const hours = Math.floor(minutes / 60)
  return hours < 24 ? `${hours} h ago` : `${Math.floor(hours / 24)} d ago`
}

/** Format a coordinate pair the way the dashboard footer does. */
export function formatCoordinates(latitude: number, longitude: number): string {
  return `${latitude.toFixed(3)}, ${longitude.toFixed(3)}`
}

/**
 * Current wall-clock time at a location with the given UTC offset.
 *
 * The instant is shifted by the offset and then formatted in UTC, which is
 * equivalent to rendering it in the location's zone without needing the IANA
 * name - and without depending on the browser's own zone.
 */
export function formatLocationClock(utcOffsetSeconds: number, now: Date = new Date()): string {
  return TIME_FORMATTER.format(new Date(now.getTime() + utcOffsetSeconds * 1000))
}

/** Render a UTC offset as `GMT+5` / `GMT-3:30`, matching the provider's label style. */
export function formatUtcOffset(utcOffsetSeconds: number): string {
  const sign = utcOffsetSeconds < 0 ? '-' : '+'
  const total = Math.abs(utcOffsetSeconds)
  const hours = Math.floor(total / 3600)
  const minutes = Math.round((total % 3600) / 60)
  const suffix = minutes === 0 ? `${hours}` : `${hours}:${minutes.toString().padStart(2, '0')}`
  return `GMT${sign}${suffix}`
}