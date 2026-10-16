/**
 * Public surface of the API service layer.
 *
 * Components import from `src/api` only, never from `client.ts` or
 * `weatherApi.ts` directly, so the transport can change without touching the UI.
 */

export { ApiError } from './client'
export type { RequestOptions } from './client'
export { API_BASE_URL, API_PATHS, API_TIMEOUT_MS, apiUrl } from './config'
export {
  FACE_COUNT_CHOICES,
  FORECAST_DAYS_MAX,
  FORECAST_DAYS_MIN,
  HOURS_CHOICES,
  getAppConfig,
  getDefaultLocation,
  getChernoffFaces,
  getHealth,
  getWeather,
  refreshCache,
  searchLocations,
} from './weatherApi'
export type {
  Coordinates,
  GetChernoffOptions,
  GetWeatherOptions,
  SearchLocationsOptions,
} from './weatherApi'
export type * from './types'