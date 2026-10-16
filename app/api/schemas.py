"""Pydantic response models for the HTTP API.

Design rules for every model in this module:

* **JSON keys are camelCase.** ``to_camel`` generates the wire names so the
  TypeScript frontend reads naturally, while the Python attributes stay
  ``snake_case`` and match the existing service layer.
* **Missing means ``null``, never ``0``.** The processing layer represents an
  unreported measurement as ``NaN``; :func:`optional_float` converts that to
  ``None`` so the wire format stays valid JSON and a gap is never mistaken for
  a real reading. (A bare ``NaN`` token is invalid JSON and would make
  ``JSON.parse`` throw in the browser.)
* **Timestamps are naive local strings.** Open-Meteo returns times already
  expressed in the queried location's local time because the request uses
  ``timezone=auto``. The instant a response was *retrieved* is the only value
  converted to UTC, and it carries an explicit offset.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    """Base model shared by every API response.

    Attributes:
        model_config: camelCase aliases on the wire, snake_case in Python.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ErrorCode(StrEnum):
    """Stable, machine-readable error identifiers for the frontend."""

    INVALID_REQUEST = "invalid_request"
    LOCATION_NOT_FOUND = "location_not_found"
    UPSTREAM_RATE_LIMITED = "upstream_rate_limited"
    UPSTREAM_TIMEOUT = "upstream_timeout"
    UPSTREAM_UNREACHABLE = "upstream_unreachable"
    UPSTREAM_BAD_RESPONSE = "upstream_bad_response"
    PROCESSING_ERROR = "processing_error"
    NOT_FOUND = "not_found"
    METHOD_NOT_ALLOWED = "method_not_allowed"
    INTERNAL_ERROR = "internal_error"


class ErrorDetail(ApiModel):
    """One machine-readable detail attached to an error response."""

    field: str | None = None
    message: str


class ErrorBody(ApiModel):
    """The ``error`` member of every failure response."""

    code: ErrorCode
    message: str
    details: list[ErrorDetail] = []


class ErrorResponse(ApiModel):
    """Envelope returned for every non-2xx response."""

    error: ErrorBody
    request_id: str
    path: str
    timestamp: datetime


class Units(ApiModel):
    """Units of the numeric fields, echoed so a client never has to guess."""

    temperature: str = "°C"
    wind_speed: str = "km/h"
    precipitation: str = "mm"


class ProviderInfo(ApiModel):
    """Attribution for the upstream data source (CC BY 4.0)."""

    name: str
    url: str
    license: str


class LocationOut(ApiModel):
    """A resolved place, ready to be used as a forecast request."""

    name: str
    latitude: float
    longitude: float
    country: str | None = None
    admin1: str | None = None
    country_code: str | None = None
    timezone: str | None = None
    population: int | None = None
    display_name: str
    short_label: str


class LocationSearchResponse(ApiModel):
    """Response of ``GET /api/locations/search``."""

    query: str
    count: int
    results: list[LocationOut]
    cached: bool
    cache_age_seconds: float
    provider: ProviderInfo


class WeatherConditionOut(ApiModel):
    """A WMO 4677 code resolved to text and an icon."""

    label: str
    icon: str
    is_known: bool


class CurrentConditionsOut(ApiModel):
    """Current conditions, the equivalent of the dashboard's KPI row."""

    observed_at: datetime | None = None
    temperature_c: float | None = None
    feels_like_c: float | None = None
    humidity_pct: float | None = None
    wind_speed_kmh: float | None = None
    precipitation_mm: float | None = None
    weather_code: int | None = None
    condition: WeatherConditionOut
    has_measurements: bool


class HourlyPointOut(ApiModel):
    """One hour of the forecast window.

    ``time`` is a naive local timestamp exactly as the provider returned it and
    ``label`` is its pre-rendered display form, so a client never has to redo
    timezone arithmetic (or accidentally apply the browser's own zone).
    """

    time: datetime | None = None
    label: str
    temperature_c: float | None = None
    humidity_pct: float | None = None
    precipitation_probability_pct: float | None = None
    wind_speed_kmh: float | None = None
    apparent_temperature_c: float | None = None


class DailyPointOut(ApiModel):
    """One day of the seven-day forecast."""

    date: datetime | None = None
    label: str
    condition: WeatherConditionOut
    temperature_max_c: float | None = None
    temperature_min_c: float | None = None
    precipitation_probability_max_pct: float | None = None
    precipitation_total_mm: float | None = None
    wind_speed_max_kmh: float | None = None
    apparent_temperature_max_c: float | None = None
    humidity_mean_pct: float | None = None


class ForecastSummaryOut(ApiModel):
    """Window metadata and data-quality counters for the response."""

    hours: int
    hours_count: int
    days_count: int
    window_start: datetime | None = None
    window_end: datetime | None = None
    missing_hourly_count: int
    missing_daily_count: int


class FaceSpecOut(ApiModel):
    """Normalised ``0-1`` encodings driving one face.

    Every value is scaled across the faces included in the same response, which
    is what makes a face comparable with its neighbours.
    """

    temperature: float
    humidity: float
    wind: float
    precipitation: float
    apparent_temperature: float


class FaceOut(ApiModel):
    """One real forecast record prepared for Chernoff Faces rendering."""

    label: str
    summary: str
    tooltip: str
    values: dict[str, str]
    spec: FaceSpecOut


class FaceFeatureOut(ApiModel):
    """How one weather variable maps onto one facial feature."""

    variable: str
    label: str
    unit: str
    feature: str
    direction: str


class ChernoffSourceOut(ApiModel):
    """Prepared faces for one forecast block, plus the mapping legend."""

    source: str
    label: str
    requested_count: int
    faces: list[FaceOut]
    features: list[FaceFeatureOut]
    neutral_value: float


class ChernoffOut(ApiModel):
    """Chernoff payload for every available source in one response."""

    sources: dict[str, ChernoffSourceOut]
    note: str


class WeatherMetaOut(ApiModel):
    """Everything about the forecast response itself, not the weather."""

    latitude: float
    longitude: float
    timezone: str
    timezone_abbreviation: str
    utc_offset_seconds: int
    elevation_m: float | None = None
    retrieved_at: datetime
    forecast_days: int
    cached: bool
    cache_age_seconds: float
    cache_ttl_seconds: int
    units: Units
    provider: ProviderInfo


class WeatherResponse(ApiModel):
    """Response of ``GET /api/weather`` and ``GET /api/chernoff``'s sibling."""

    meta: WeatherMetaOut
    current: CurrentConditionsOut
    hourly: list[HourlyPointOut]
    daily: list[DailyPointOut]
    summary: ForecastSummaryOut
    chernoff: ChernoffOut
    warnings: list[str]


class CacheRefreshResponse(ApiModel):
    """Response of ``POST /api/cache/refresh``."""

    scope: str
    cleared_caches: list[str]
    cleared_entries: int
    timestamp: datetime


class CacheStatsOut(ApiModel):
    """Entry counts for one cache."""

    entries: int
    live_entries: int
    in_flight: int


class HealthResponse(ApiModel):
    """Response of ``GET /api/health``."""

    status: str
    service: str
    version: str
    api_prefix: str
    docs_url: str
    timestamp: datetime
    python_version: str
    cache_ttl_seconds: dict[str, int]
    cache: dict[str, CacheStatsOut]
    upstream: dict[str, str]
    provider: ProviderInfo
    frontend_dist_served: bool
    authentication: str = "none"


class AppConfigResponse(ApiModel):
    """Static description of the API contract, used to configure the frontend."""

    app_title: str
    app_subtitle: str
    version: str
    hours_choices: list[int]
    default_hours: int
    forecast_days: int
    min_forecast_days: int
    max_forecast_days: int
    face_count_choices: list[int]
    default_face_count: int
    units: Units
    provider: ProviderInfo
    attribution: str
    freshness_note: str
