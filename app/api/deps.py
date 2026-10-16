"""Request-scoped dependencies: validation, caching and data preparation.

Two patterns are worth knowing about:

* **Endpoints are declared ``def``, not ``async def``.** The services use
  ``requests``, which blocks. FastAPI runs synchronous endpoints in a worker
  thread pool, so those blocking calls never stall the event loop.
* **Only the upstream fetch is cached.** The cache stores the validated
  ``WeatherBundle`` / ``list[Location]``, keyed by coordinates or query.
  Windowing (12/24/48 hours), reshaping and Chernoff normalisation are cheap
  pure functions and run per request, so a different window does not need its
  own cache entry.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Annotated, Final

import pandas as pd
from fastapi import Depends, Query

from app import config
from app.api.cache import GEOCODING_CACHE, WEATHER_CACHE, CacheRegistry, build_registry
from app.api.errors import invalid_request
from app.api.settings import ApiSettings, load_settings
from app.services.geocoding_service import Location, search_locations
from app.services.weather_service import WeatherBundle, fetch_weather
from app.utils.chernoff import FACE_COUNT_CHOICES
from app.utils.data_processing import (
    CurrentConditions,
    build_current_conditions,
    build_daily_forecast,
    build_hourly_forecast,
)

LOGGER = logging.getLogger(__name__)

#: Defaults applied when a query parameter is omitted.
DEFAULT_HOURS: Final[int] = config.DEFAULT_HOURLY_PERIOD
DEFAULT_FORECAST_DAYS: Final[int] = config.FORECAST_DAYS
DEFAULT_SEARCH_COUNT: Final[int] = config.GEOCODING_RESULT_LIMIT
CHERNOFF_SOURCES: Final[tuple[str, ...]] = ("hourly", "daily")

#: Coordinate bounds reused from :mod:`app.config`, so nonsense coordinates are
#: rejected before a request ever leaves the process.
LatitudeQuery = Annotated[
    float,
    Query(
        ge=config.MIN_LATITUDE,
        le=config.MAX_LATITUDE,
        description="Latitude in decimal degrees.",
        examples=[34.1463],
    ),
]
LongitudeQuery = Annotated[
    float,
    Query(
        ge=config.MIN_LONGITUDE,
        le=config.MAX_LONGITUDE,
        description="Longitude in decimal degrees.",
        examples=[73.2117],
    ),
]
HoursQuery = Annotated[
    int,
    Query(ge=1, le=24 * config.MAX_FORECAST_DAYS, description="Hourly window size in hours."),
]
ForecastDaysQuery = Annotated[
    int,
    Query(
        ge=config.MIN_FORECAST_DAYS,
        le=config.MAX_FORECAST_DAYS,
        description="Number of forecast days to request (Open-Meteo limit: 16).",
    ),
]
ChernoffCountQuery = Annotated[
    int,
    Query(ge=1, description="Chernoff faces to prepare per forecast source."),
]
CountQuery = Annotated[
    int,
    Query(
        ge=1,
        le=config.GEOCODING_RESULT_LIMIT,
        description="Maximum number of matching locations to return.",
    ),
]
QueryText = Annotated[
    str,
    Query(
        min_length=1,
        max_length=config.MAX_LOCATION_QUERY_LENGTH,
        description="Place name to search for.",
    ),
]
SourceQuery = Annotated[
    str,
    Query(
        description="Forecast block to draw faces from: 'hourly' or 'daily'.",
        examples=["hourly"],
    ),
]


@dataclass(frozen=True, slots=True)
class ForecastData:
    """Everything the weather endpoint needs, already reshaped.

    Attributes:
        bundle: Validated forecast response from the service layer.
        conditions: Current conditions extracted from the bundle.
        hourly: Hourly window frame for the requested number of hours.
        daily: Daily forecast frame.
        cached: Whether the forecast response came from the cache.
        cache_age_seconds: Age of the cached response, when it was cached.
        cache_ttl_seconds: Configured TTL of the forecast cache.
    """

    bundle: WeatherBundle
    conditions: CurrentConditions
    hourly: pd.DataFrame
    daily: pd.DataFrame
    cached: bool
    cache_age_seconds: float
    cache_ttl_seconds: float


# --------------------------------------------------------------------------- #
# Process-wide singletons
# --------------------------------------------------------------------------- #


def get_settings() -> ApiSettings:
    """Return the API settings resolved from the environment."""
    return load_settings()


_SETTINGS: Final[ApiSettings] = get_settings()
_REGISTRY: Final[CacheRegistry] = build_registry(_SETTINGS)


def get_registry() -> CacheRegistry:
    """Return the process-wide cache registry."""
    return _REGISTRY


RegistryDependency = Annotated[CacheRegistry, Depends(get_registry)]
SettingsDependency = Annotated[ApiSettings, Depends(get_settings)]


# --------------------------------------------------------------------------- #
# Validation helpers
# --------------------------------------------------------------------------- #


def parse_hours(value: int) -> int:
    """Validate the hourly window size.

    Args:
        value: Requested window in hours.

    Returns:
        The validated window size.

    Raises:
        HTTPException: 400 when the value is not one of the supported windows.
    """
    if value not in config.HOURLY_PERIOD_CHOICES:
        raise invalid_request(
            f"hours must be one of {sorted(config.HOURLY_PERIOD_CHOICES)}; got {value}.",
            field="hours",
        )
    return value


def parse_face_count(value: int) -> int:
    """Validate the requested number of Chernoff faces."""
    if value not in FACE_COUNT_CHOICES:
        raise invalid_request(
            f"chernoff_count must be one of {sorted(FACE_COUNT_CHOICES)}; got {value}.",
            field="chernoffCount",
        )
    return value


def parse_source(value: str) -> str:
    """Validate the requested Chernoff source key."""
    normalised = value.strip().lower()
    if normalised not in CHERNOFF_SOURCES:
        raise invalid_request(
            f"source must be one of {list(CHERNOFF_SOURCES)}; got {value!r}.", field="source"
        )
    return normalised


def weather_cache_key(latitude: float, longitude: float, forecast_days: int) -> str:
    """Build the forecast cache key.

    Coordinates are rounded to four decimals (roughly 11 m) so trivially
    different spellings of the same point share an entry. The window size is
    deliberately excluded because slicing happens per request.
    """
    return f"{latitude:.4f},{longitude:.4f},{int(forecast_days)}"


def geocoding_cache_key(query: str, count: int) -> str:
    """Build the geocoding cache key, normalised for case and whitespace."""
    return f"{' '.join(query.strip().lower().split())}|{int(count)}"


# --------------------------------------------------------------------------- #
# Cached service access
# --------------------------------------------------------------------------- #


def cached_fetch_weather(
    latitude: float,
    longitude: float,
    forecast_days: int,
    registry: CacheRegistry,
) -> tuple[WeatherBundle, bool, float]:
    """Fetch a forecast, reusing the cached response while it is fresh.

    Args:
        latitude: Latitude in decimal degrees.
        longitude: Longitude in decimal degrees.
        forecast_days: Number of forecast days to request.
        registry: Cache registry holding the forecast cache.

    Returns:
        The bundle, whether it was served from the cache, and its age in
        seconds.
    """
    cache = registry[WEATHER_CACHE]
    key = weather_cache_key(latitude, longitude, forecast_days)
    lookup = cache.get_or_set(
        key,
        lambda: fetch_weather(latitude, longitude, forecast_days=forecast_days),
    )
    return lookup.value, lookup.hit, lookup.age_seconds


def cached_search_locations(
    query: str,
    count: int,
    registry: CacheRegistry,
) -> tuple[list[Location], bool, float]:
    """Search for places, reusing cached results for an hour.

    Args:
        query: Free-text place name.
        count: Maximum number of matches.
        registry: Cache registry holding the geocoding cache.

    Returns:
        The matches, whether they were served from the cache, and their age in
        seconds. Provider failures propagate to the error handlers unchanged.

    Raises:
        EmptyQueryError: ``query`` is blank.
        LocationNotFoundError: Nothing matched.
    """
    cache = registry[GEOCODING_CACHE]
    key = geocoding_cache_key(query, count)
    lookup = cache.get_or_set(key, lambda: search_locations(query, count=count))
    return lookup.value, lookup.hit, lookup.age_seconds


def load_forecast(
    latitude: float,
    longitude: float,
    hours: int,
    forecast_days: int,
    registry: CacheRegistry,
) -> ForecastData:
    """Fetch (or reuse) a forecast and reshape it for the response.

    Args:
        latitude: Latitude in decimal degrees.
        longitude: Longitude in decimal degrees.
        hours: Hourly window size in hours.
        forecast_days: Number of forecast days.
        registry: Cache registry holding the forecast cache.

    Returns:
        The bundle, its derived frames and the cache metadata.
    """
    bundle, cached, age = cached_fetch_weather(latitude, longitude, forecast_days, registry)
    data = ForecastData(
        bundle=bundle,
        conditions=build_current_conditions(bundle),
        hourly=build_hourly_forecast(bundle, hours),
        daily=build_daily_forecast(bundle),
        cached=cached,
        cache_age_seconds=age,
        cache_ttl_seconds=registry[WEATHER_CACHE].ttl_seconds,
    )
    LOGGER.debug(
        "Forecast ready for (%.4f, %.4f) hours=%d cached=%s age=%.1fs",
        latitude,
        longitude,
        hours,
        cached,
        age,
    )
    return data
