/**
 * TypeScript mirrors of the FastAPI response models.
 *
 * Every interface here corresponds 1:1 to a schema in the backend's OpenAPI
 * document (`GET /api/openapi.json`), generated from `app/api/schemas.py`:
 *
 * | Interface               | Pydantic model           |
 * | ----------------------- | ------------------------ |
 * | `ApiErrorResponse`      | `ErrorResponse`          |
 * | `ErrorBody`             | `ErrorBody`              |
 * | `ErrorDetail`           | `ErrorDetail`            |
 * | `Units`                 | `Units`                  |
 * | `ProviderInfo`          | `ProviderInfo`           |
 * | `Location`              | `LocationOut`            |
 * | `LocationSearchResponse`| `LocationSearchResponse` |
 * | `WeatherCondition`      | `WeatherConditionOut`    |
 * | `CurrentConditions`     | `CurrentConditionsOut`   |
 * | `HourlyPoint`           | `HourlyPointOut`         |
 * | `DailyPoint`            | `DailyPointOut`          |
 * | `ForecastSummary`       | `ForecastSummaryOut`     |
 * | `FaceSpec`              | `FaceSpecOut`            |
 * | `ChernoffFace`          | `FaceOut`                |
 * | `ChernoffFaceFeature`   | `FaceFeatureOut`         |
 * | `ChernoffSource`        | `ChernoffSourceOut`      |
 * | `Chernoff`              | `ChernoffOut`            |
 * | `WeatherMeta`           | `WeatherMetaOut`         |
 * | `WeatherResponse`       | `WeatherResponse`        |
 * | `CacheRefreshResponse`  | `CacheRefreshResponse`   |
 * | `CacheStats`            | `CacheStatsOut`          |
 * | `HealthResponse`        | `HealthResponse`         |
 * | `AppConfigResponse`     | `AppConfigResponse`      |
 *
 * Two conventions carry over from the backend and must not be "tidied up":
 *
 * 1. **A missing measurement is `null`, never `0`.** The provider sometimes omits
 *    values, the processing layer keeps them missing, and the API serialises
 *    them as JSON `null`. `0` is a real reading; `null` means "not reported".
 * 2. **Forecast timestamps are naive local strings** such as
 *    `2026-10-02T22:00:00`, because the upstream request uses `timezone=auto`.
 *    Only `meta.retrievedAt` carries a UTC offset. Do not feed these strings to
 *    `new Date()` and format them with the browser's zone - that silently
 *    converts them. Use the pre-rendered `label` field, or `formatLocalTime()`
 *    in `src/lib/format.ts` with `meta.utcOffsetSeconds`.
 */

/** Stable error identifiers emitted by `app/api/errors.py`. */
export type ApiErrorCode =
  | 'invalid_request'
  | 'location_not_found'
  | 'upstream_rate_limited'
  | 'upstream_timeout'
  | 'upstream_unreachable'
  | 'upstream_bad_response'
  | 'processing_error'
  | 'not_found'
  | 'method_not_allowed'
  | 'internal_error'

/** Field-level detail attached to a validation failure. */
export interface ErrorDetail {
  readonly field: string | null
  readonly message: string
}

/** The `error` member of every failure response. */
export interface ErrorBody {
  readonly code: ApiErrorCode
  readonly message: string
  readonly details: readonly ErrorDetail[]
}

/** Envelope returned for every non-2xx response. */
export interface ApiErrorResponse {
  readonly error: ErrorBody
  readonly requestId: string
  readonly path: string
  /** ISO-8601 instant in UTC. */
  readonly timestamp: string
}

/** Units of the numeric fields; the backend pins these server-side. */
export interface Units {
  readonly temperature: string
  readonly windSpeed: string
  readonly precipitation: string
}

/** Attribution for the upstream data source (Open-Meteo, CC BY 4.0). */
export interface ProviderInfo {
  readonly name: string
  readonly url: string
  readonly license: string
}

/** A resolved place. */
export interface Location {
  readonly name: string
  readonly latitude: number
  readonly longitude: number
  readonly country: string | null
  readonly admin1: string | null
  readonly countryCode: string | null
  readonly timezone: string | null
  readonly population: number | null
  readonly displayName: string
  readonly shortLabel: string
}

/** Response of `GET /api/locations/search`. */
export interface LocationSearchResponse {
  readonly query: string
  readonly count: number
  readonly results: readonly Location[]
  readonly cached: boolean
  readonly cacheAgeSeconds: number
  readonly provider: ProviderInfo
}

/** A WMO 4677 code resolved to text and an icon. */
export interface WeatherCondition {
  readonly label: string
  readonly icon: string
  readonly isKnown: boolean
}

/** Current conditions. */
export interface CurrentConditions {
  /** Naive local timestamp of the current 15-minute interval. */
  readonly observedAt: string | null
  readonly temperatureC: number | null
  readonly feelsLikeC: number | null
  readonly humidityPct: number | null
  readonly windSpeedKmh: number | null
  readonly precipitationMm: number | null
  readonly weatherCode: number | null
  readonly condition: WeatherCondition
  readonly hasMeasurements: boolean
}

/** One hour of the forecast window. */
export interface HourlyPoint {
  /** Naive local timestamp, e.g. `2026-10-02T22:00:00`. */
  readonly time: string | null
  /** Pre-rendered local label, e.g. `Fri 22:00`. */
  readonly label: string
  readonly temperatureC: number | null
  readonly humidityPct: number | null
  readonly precipitationProbabilityPct: number | null
  readonly windSpeedKmh: number | null
  readonly apparentTemperatureC: number | null
}

/** One day of the seven-day forecast. */
export interface DailyPoint {
  /** Naive local date at midnight, e.g. `2026-10-03T00:00:00`. */
  readonly date: string | null
  /** Pre-rendered local label, e.g. `Sat 03 Oct`. */
  readonly label: string
  readonly condition: WeatherCondition
  readonly temperatureMaxC: number | null
  readonly temperatureMinC: number | null
  readonly precipitationProbabilityMaxPct: number | null
  readonly precipitationTotalMm: number | null
  readonly windSpeedMaxKmh: number | null
  readonly apparentTemperatureMaxC: number | null
  readonly humidityMeanPct: number | null
}

/** Window metadata and data-quality counters. */
export interface ForecastSummary {
  readonly hours: number
  readonly hoursCount: number
  readonly daysCount: number
  readonly windowStart: string | null
  readonly windowEnd: string | null
  readonly missingHourlyCount: number
  readonly missingDailyCount: number
}

/**
 * Normalised `0-1` encodings driving one Chernoff face.
 *
 * Values are scaled across the faces of the same response, so they are only
 * meaningful when compared with each other - not against absolute weather
 * thresholds.
 */
export interface FaceSpec {
  readonly temperature: number
  readonly humidity: number
  readonly wind: number
  readonly precipitation: number
  readonly apparentTemperature: number
}

/** One real forecast record prepared for Chernoff Faces rendering. */
export interface ChernoffFace {
  readonly label: string
  readonly summary: string
  /** Multi-line plain-text tooltip; `<b>`/`<i>` markup, newlines as separators. */
  readonly tooltip: string
  /** Display-ready reported values, keyed by source column name. */
  readonly values: Readonly<Record<string, string>>
  readonly spec: FaceSpec
}

/** How one weather variable maps onto one facial feature. */
export interface ChernoffFaceFeature {
  readonly variable: string
  readonly label: string
  readonly unit: string
  readonly feature: string
  readonly direction: string
}

/** Prepared faces for one forecast block, plus the mapping legend. */
export interface ChernoffSource {
  readonly source: string
  readonly label: string
  readonly requestedCount: number
  readonly faces: readonly ChernoffFace[]
  readonly features: readonly ChernoffFaceFeature[]
  readonly neutralValue: number
}

/** Chernoff payload for every available source in one response. */
export interface Chernoff {
  /** Keyed by source key, currently `hourly` and `daily`. */
  readonly sources: Readonly<Record<string, ChernoffSource>>
  readonly note: string
}

/** Everything about the forecast response itself, not the weather. */
export interface WeatherMeta {
  /** Grid-cell coordinates echoed by the provider. */
  readonly latitude: number
  readonly longitude: number
  /** IANA zone the forecast timestamps are expressed in. */
  readonly timezone: string
  readonly timezoneAbbreviation: string
  readonly utcOffsetSeconds: number
  readonly elevationM: number | null
  /** ISO-8601 instant in UTC at which the upstream response was fetched. */
  readonly retrievedAt: string
  readonly forecastDays: number
  readonly cached: boolean
  readonly cacheAgeSeconds: number
  readonly cacheTtlSeconds: number
  readonly units: Units
  readonly provider: ProviderInfo
}

/** Response of `GET /api/weather`. */
export interface WeatherResponse {
  readonly meta: WeatherMeta
  readonly current: CurrentConditions
  readonly hourly: readonly HourlyPoint[]
  readonly daily: readonly DailyPoint[]
  readonly summary: ForecastSummary
  readonly chernoff: Chernoff
  /** Human-readable degradations the UI should surface. */
  readonly warnings: readonly string[]
}

/** Response of `POST /api/cache/refresh`. */
export interface CacheRefreshResponse {
  readonly scope: string
  readonly clearedCaches: readonly string[]
  readonly clearedEntries: number
  readonly timestamp: string
}

/** Entry counts for one cache. */
export interface CacheStats {
  readonly entries: number
  readonly liveEntries: number
  readonly inFlight: number
}

/** Response of `GET /api/health`. */
export interface HealthResponse {
  readonly status: string
  readonly service: string
  readonly version: string
  readonly apiPrefix: string
  readonly docsUrl: string
  readonly timestamp: string
  readonly pythonVersion: string
  readonly cacheTtlSeconds: Readonly<Record<string, number>>
  readonly cache: Readonly<Record<string, CacheStats>>
  readonly upstream: Readonly<Record<string, string>>
  readonly provider: ProviderInfo
  readonly frontendDistServed: boolean
  readonly authentication?: string
}

/** Response of `GET /api/config`. */
export interface AppConfigResponse {
  readonly appTitle: string
  readonly appSubtitle: string
  readonly version: string
  readonly hoursChoices: readonly number[]
  readonly defaultHours: number
  readonly forecastDays: number
  readonly minForecastDays: number
  readonly maxForecastDays: number
  readonly faceCountChoices: readonly number[]
  readonly defaultFaceCount: number
  readonly units: Units
  readonly provider: ProviderInfo
  readonly attribution: string
  readonly freshnessNote: string
}

/** Forecast source keys accepted by `GET /api/chernoff`. */
export type ChernoffSourceKey = 'hourly' | 'daily'

/** Cache scopes accepted by `POST /api/cache/refresh`. */
export type CacheScope = 'weather' | 'geocoding' | 'all'