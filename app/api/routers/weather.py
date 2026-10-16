"""Forecast endpoints.

Current conditions, hourly window, daily outlook and the Chernoff Faces
payloads. All of them reuse the existing service and processing layer, so the
numbers are produced by exactly the same code paths as the Streamlit
dashboard.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.deps import (
    DEFAULT_FORECAST_DAYS,
    DEFAULT_HOURS,
    ChernoffCountQuery,
    ForecastDaysQuery,
    HoursQuery,
    LatitudeQuery,
    LongitudeQuery,
    RegistryDependency,
    SourceQuery,
    load_forecast,
    parse_face_count,
    parse_hours,
    parse_source,
)
from app.api.schemas import ChernoffOut, WeatherResponse
from app.api.transformers import (
    CHERNOFF_NOTE,
    build_weather_response,
    faces_to_out,
)
from app.utils.chernoff import DEFAULT_FACE_COUNT, FACE_SOURCES

router = APIRouter(tags=["weather"])

_UPSTREAM_ERRORS = {
    429: {"description": "The upstream provider is rate limiting requests."},
    502: {"description": "The upstream provider could not be reached."},
    504: {"description": "The upstream provider did not respond in time."},
}


@router.get(
    "/weather",
    response_model=WeatherResponse,
    responses={
        400: {"description": "A query parameter is invalid."},
        **_UPSTREAM_ERRORS,
    },
    summary="Current conditions, hourly window and seven-day forecast",
)
def get_weather(
    latitude: LatitudeQuery,
    longitude: LongitudeQuery,
    registry: RegistryDependency,
    hours: HoursQuery = DEFAULT_HOURS,
    forecast_days: ForecastDaysQuery = DEFAULT_FORECAST_DAYS,
    chernoff_count: ChernoffCountQuery = DEFAULT_FACE_COUNT,
) -> WeatherResponse:
    """Return everything a dashboard needs for one location.

    Args:
        latitude: Latitude in decimal degrees.
        longitude: Longitude in decimal degrees.
        registry: Cache registry holding the forecast cache.
        hours: Size of the hourly window (12, 24 or 48).
        forecast_days: Number of forecast days to request.
        chernoff_count: Chernoff faces to prepare per source.

    Returns:
        Metadata, current conditions, the hourly window, the daily outlook, the
        Chernoff Faces for both sources, and any warnings describing missing
        data. Missing measurements are ``null``, never ``0``.

    Raises:
        HTTPException: 400 when a query parameter is out of range.
        NetworkRequestError: The provider could not be reached.
        APITimeoutError: The provider did not respond in time.
        APIRateLimitError: The provider is rate limiting requests.
        APIResponseError: The payload was malformed.
    """
    window = parse_hours(hours)
    faces = parse_face_count(chernoff_count)
    data = load_forecast(latitude, longitude, window, forecast_days, registry)
    return build_weather_response(
        data.bundle,
        data.conditions,
        data.hourly,
        data.daily,
        hours=window,
        forecast_days=forecast_days,
        cached=data.cached,
        cache_age_seconds=data.cache_age_seconds,
        cache_ttl_seconds=int(data.cache_ttl_seconds),
        chernoff_count=faces,
    )


@router.get(
    "/chernoff",
    response_model=ChernoffOut,
    responses={
        400: {"description": "A query parameter is invalid."},
        404: {"description": "The requested forecast source is unavailable."},
        **_UPSTREAM_ERRORS,
    },
    summary="Chernoff Faces for one forecast source",
)
def get_chernoff_faces(
    latitude: LatitudeQuery,
    longitude: LongitudeQuery,
    registry: RegistryDependency,
    source: SourceQuery,
    count: ChernoffCountQuery = DEFAULT_FACE_COUNT,
    forecast_days: ForecastDaysQuery = DEFAULT_FORECAST_DAYS,
) -> ChernoffOut:
    """Return normalised Chernoff Faces for the hourly or daily forecast.

    Each face is one real forecast record. Values are min-max normalised to
    ``0-1`` across the faces returned here, and each source ships the legend
    describing which variable drives which feature.

    Args:
        latitude: Latitude in decimal degrees.
        longitude: Longitude in decimal degrees.
        registry: Cache registry holding the forecast cache.
        source: ``"hourly"`` or ``"daily"``.
        count: Number of faces to prepare.
        forecast_days: Number of forecast days to request.

    Returns:
        The prepared faces for the requested source.

    Raises:
        HTTPException: 400 for an invalid parameter, 404 when the source has no
            usable data.
    """
    requested = parse_source(source)
    faces = parse_face_count(count)
    data = load_forecast(latitude, longitude, 24, forecast_days, registry)
    frame = data.hourly if requested == "hourly" else data.daily
    if frame.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"The weather service did not return {requested} data for this "
                "location, so there are no faces to draw."
            ),
        )
    return ChernoffOut(
        sources={requested: faces_to_out(frame, FACE_SOURCES[requested], faces)},
        note=CHERNOFF_NOTE,
    )
