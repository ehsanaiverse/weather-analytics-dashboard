/**
 * Copy shared by the shell.
 *
 * `ATTRIBUTION_TEXT` is the CC BY 4.0 attribution required by Open-Meteo and is
 * rendered unconditionally in the footer. Keep it.
 */

export const APP_TITLE = 'Real-Time Weather Analytics Dashboard'

export const APP_SUBTITLE = 'Current conditions and short-range forecasts from the Open-Meteo API'

export const ATTRIBUTION_TEXT =
  'Weather data by Open-Meteo (CC BY 4.0). Geocoding by Open-Meteo.'

export const DATA_FRESHNESS_NOTE =
  "Values come from Open-Meteo's forecast model blend. 'Current' is the nearest 15-minute " +
  'interval, not a live station reading, and cached responses are reused until the cache ' +
  'expires or you refresh.'