/**
 * Typed wrappers for every backend endpoint.
 *
 * Each function maps 1:1 to a route in `app/api/routers/` and returns the
 * response model declared in `app/api/schemas.py`. Validation limits mirror the
 * backend's own rules (`config.HOURLY_PERIOD_CHOICES`, the 1-16 day forecast
 * range, the 4/6/8/12 face counts) so invalid requests fail locally instead of
 * costing a round trip.
 */

import { ApiError, post, request } from './client'
import { API_PATHS } from './config'
import type {
  AppConfigResponse,
  CacheRefreshResponse,
  CacheScope,
  Chernoff,
  ChernoffSourceKey,
  HealthResponse,
  Location,
  LocationSearchResponse,
  WeatherResponse,
} from './types'

/** Hourly windows the backend accepts. */
export const HOURS_CHOICES: readonly number[] = [12, 24, 48]
/** Face counts the backend accepts. */
export const FACE_COUNT_CHOICES: readonly number[] = [4, 6, 8, 12]
/** Forecast-day range accepted by the Open-Meteo API. */
export const FORECAST_DAYS_MIN = 1
export const FORECAST_DAYS_MAX = 16

/** Options shared by every weather request. */
export interface Coordinates {
  readonly latitude: number
  readonly longitude: number
}

/** Options for {@link getWeather}. */
export interface GetWeatherOptions extends Coordinates {
  /** Hourly window size: 12, 24 or 48. */
  readonly hours?: number | undefined
  /** Number of forecast days, 1-16. */
  readonly forecastDays?: number | undefined
  /** Chernoff faces per source: 4, 6, 8 or 12. */
  readonly chernoffCount?: number | undefined
  readonly signal?: AbortSignal | undefined
}

/** Options for {@link searchLocations}. */
export interface SearchLocationsOptions {
  /** Maximum number of matches, 1-10. */
  readonly count?: number | undefined
  readonly signal?: AbortSignal | undefined
}

/** Options for {@link getChernoffFaces}. */
export interface GetChernoffOptions extends Coordinates {
  readonly source: ChernoffSourceKey
  /** Face count: 4, 6, 8 or 12. Capped by the available records. */
  readonly count?: number | undefined
  readonly forecastDays?: number | undefined
  readonly signal?: AbortSignal | undefined
}

/** Liveness, cache state and upstream configuration. */
export function getHealth(
  options: { readonly signal?: AbortSignal | undefined } = {},
): Promise<HealthResponse> {
  return request<HealthResponse>(API_PATHS.health, { signal: options.signal })
}

/**
 * The built-in default location (Abbottabad, Pakistan).
 *
 * The coordinates live in `app/config.py`, so the client never hardcodes a
 * place of its own and the first render costs no geocoding request.
 */
export function getDefaultLocation(
  options: { readonly signal?: AbortSignal | undefined } = {},
): Promise<Location> {
  return request<Location>(API_PATHS.locationDefault, { signal: options.signal })
}

/** Static description of the API contract, used to configure the UI. */
export function getAppConfig(
  options: { readonly signal?: AbortSignal | undefined } = {},
): Promise<AppConfigResponse> {
  return request<AppConfigResponse>(API_PATHS.config, { signal: options.signal })
}

/**
 * Search for a place by name.
 *
 * @throws {ApiError} `invalid_request` for a blank query, `location_not_found`
 * when nothing matched.
 */
export function searchLocations(
  query: string,
  options: SearchLocationsOptions = {},
): Promise<LocationSearchResponse> {
  const trimmed = query.trim()
  if (trimmed.length === 0) {
    throw new ApiError('Enter a city name to search for.', {
      status: 0,
      code: 'invalid_request',
      requestId: '',
    })
  }
  return request<LocationSearchResponse>(API_PATHS.locationSearch, {
    params: { q: trimmed, count: options.count },
    signal: options.signal,
  })
}

/**
 * Current conditions, the hourly window and the seven-day outlook, including
 * the Chernoff Faces for every available source.
 *
 * @throws {ApiError} `invalid_request` when `hours` or `chernoffCount` is
 * outside the accepted values.
 */
export function getWeather(options: GetWeatherOptions): Promise<WeatherResponse> {
  const hours = options.hours ?? 24
  const forecastDays = options.forecastDays ?? 7
  const chernoffCount = options.chernoffCount ?? 6

  if (!HOURS_CHOICES.includes(hours)) {
    throw new ApiError(`hours must be one of ${HOURS_CHOICES.join(', ')}.`, {
      status: 0,
      code: 'invalid_request',
      requestId: '',
      details: [{ field: 'hours', message: `unsupported window: ${hours}` }],
    })
  }
  if (!FACE_COUNT_CHOICES.includes(chernoffCount)) {
    throw new ApiError(`chernoffCount must be one of ${FACE_COUNT_CHOICES.join(', ')}.`, {
      status: 0,
      code: 'invalid_request',
      requestId: '',
      details: [{ field: 'chernoffCount', message: `unsupported count: ${chernoffCount}` }],
    })
  }
  if (forecastDays < FORECAST_DAYS_MIN || forecastDays > FORECAST_DAYS_MAX) {
    throw new ApiError(
      `forecastDays must be between ${FORECAST_DAYS_MIN} and ${FORECAST_DAYS_MAX}.`,
      {
        status: 0,
        code: 'invalid_request',
        requestId: '',
        details: [{ field: 'forecastDays', message: `out of range: ${forecastDays}` }],
      },
    )
  }

  return request<WeatherResponse>(API_PATHS.weather, {
    params: {
      latitude: options.latitude,
      longitude: options.longitude,
      hours,
      forecast_days: forecastDays,
      chernoff_count: chernoffCount,
    },
    signal: options.signal,
  })
}

/**
 * Chernoff Faces for one forecast source only.
 *
 * @throws {ApiError} `not_found` when the provider returned no data for that
 * source.
 */
export function getChernoffFaces(options: GetChernoffOptions): Promise<Chernoff> {
  const count = options.count ?? 6
  if (!FACE_COUNT_CHOICES.includes(count)) {
    throw new ApiError(`count must be one of ${FACE_COUNT_CHOICES.join(', ')}.`, {
      status: 0,
      code: 'invalid_request',
      requestId: '',
      details: [{ field: 'count', message: `unsupported count: ${count}` }],
    })
  }

  return request<Chernoff>(API_PATHS.chernoff, {
    params: {
      latitude: options.latitude,
      longitude: options.longitude,
      source: options.source,
      count,
      forecast_days: options.forecastDays ?? 7,
    },
    signal: options.signal,
  })
}

/**
 * Drop cached data so the next request refetches - the equivalent of the
 * Streamlit dashboard's "Refresh weather data" button.
 *
 * Clearing the cache does not guarantee newer numbers: the provider may not have
 * published a newer model run.
 */
export function refreshCache(
  scope: CacheScope = 'weather',
  options: { readonly signal?: AbortSignal | undefined } = {},
): Promise<CacheRefreshResponse> {
  return post<CacheRefreshResponse>(API_PATHS.cacheRefresh, {
    params: { scope },
    signal: options.signal,
  })
}