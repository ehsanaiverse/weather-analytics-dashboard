"""Conversion from the service and processing layers to API response models.

This module is the only place that knows both pandas and Pydantic. It exists
to keep two promises:

* the existing, working data-processing code stays untouched, and
* ``NaN`` never reaches the wire, because bare ``NaN`` is not valid JSON.
"""

from __future__ import annotations

import math
import platform
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, Final

import pandas as pd

from app import config
from app.api.schemas import (
    AppConfigResponse,
    CacheStatsOut,
    ChernoffOut,
    ChernoffSourceOut,
    CurrentConditionsOut,
    DailyPointOut,
    FaceFeatureOut,
    FaceOut,
    FaceSpecOut,
    ForecastSummaryOut,
    HealthResponse,
    HourlyPointOut,
    LocationOut,
    LocationSearchResponse,
    ProviderInfo,
    Units,
    WeatherConditionOut,
    WeatherMetaOut,
    WeatherResponse,
)
from app.services.geocoding_service import Location
from app.services.weather_service import WeatherBundle
from app.utils.chernoff import (
    DEFAULT_FACE_COUNT,
    FACE_COUNT_CHOICES,
    FACE_SOURCES,
    NEUTRAL,
    FaceSource,
    build_face_rows,
)
from app.utils.data_processing import CurrentConditions
from app.utils.weather_codes import MISSING_CONDITION, describe_weather_code

#: Prefix ``describe_weather_code`` uses for a code outside the WMO table.
_UNKNOWN_LABEL_PREFIX: Final[str] = "Unknown weather code ("

#: Explanation shipped with every Chernoff payload, so the encoding is never a
#: black box on the client side either.
CHERNOFF_NOTE: str = (
    "Each face is one real forecast record. Values are min-max normalised to "
    "0-1 across the faces in this response only, so the same temperature can "
    "look warm in one response and cool in another. A constant or entirely "
    "missing variable normalises to the neutral value, and missing values are "
    "drawn with the median of the available ones for geometry only - the "
    "reported values in 'values' are exactly what the provider returned."
)

#: Warning shown when the provider returned no usable hourly block.
_NO_HOURLY_WARNING: str = (
    "The weather service did not return hourly data for this location and time "
    "range. The hourly charts and hourly faces will be empty."
)
_NO_DAILY_WARNING: str = (
    "The weather service did not return daily forecast data for this location. "
    "The daily chart and daily faces will be empty."
)
_MISSING_VALUES_WARNING: str = (
    "Some measurements were not reported. They appear as null in this response "
    "and as gaps in the charts - never as zero."
)


def provider_info() -> ProviderInfo:
    """Return the upstream attribution required by the CC BY 4.0 licence."""
    return ProviderInfo(
        name=config.PROVIDER_NAME,
        url=config.PROVIDER_URL,
        license=config.PROVIDER_LICENSE,
    )


# --------------------------------------------------------------------------- #
# Scalar helpers
# --------------------------------------------------------------------------- #


def optional_float(value: Any) -> float | None:
    """Convert a raw measurement to ``float``, mapping every unusable value to ``None``.

    Args:
        value: Raw value from an API payload or a DataFrame cell.

    Returns:
        A finite float, or ``None`` when the provider did not report a usable
        measurement. ``NaN``, ``None``, booleans, blanks and non-numeric text
        all become ``None`` so the value is serialised as JSON ``null``.
    """
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def optional_int(value: Any) -> int | None:
    """Convert a raw integer-like value, mapping every unusable value to ``None``."""
    number = optional_float(value)
    if number is None or not number.is_integer():
        return None
    return int(number)


def optional_datetime(value: Any) -> datetime | None:
    """Convert a timestamp cell to a naive ``datetime``, or ``None``.

    The values come from ``timezone=auto`` requests, so they are already
    expressed in the location's local time and carry no offset. Keeping them
    offset-free is what lets a client label the hour correctly.
    """
    if value is None:
        return None
    try:
        stamp = pd.Timestamp(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(stamp):
        return None
    return stamp.to_pydatetime()


def _text(value: Any) -> str:
    """Return a stripped string, or an empty string for missing markers."""
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "nat", "none"} else text


# --------------------------------------------------------------------------- #
# Geocoding
# --------------------------------------------------------------------------- #


def location_to_out(location: Location) -> LocationOut:
    """Convert a :class:`Location` into its API representation."""
    return LocationOut(
        name=location.name,
        latitude=location.latitude,
        longitude=location.longitude,
        country=location.country,
        admin1=location.admin1,
        country_code=location.country_code,
        timezone=location.timezone,
        population=location.population,
        display_name=location.display_name,
        short_label=location.short_label,
    )


def build_location_search(
    query: str,
    locations: Sequence[Location],
    *,
    cached: bool,
    cache_age_seconds: float,
) -> LocationSearchResponse:
    """Build the response of the location search endpoint."""
    return LocationSearchResponse(
        query=query,
        count=len(locations),
        results=[location_to_out(location) for location in locations],
        cached=cached,
        cache_age_seconds=round(cache_age_seconds, 3),
        provider=provider_info(),
    )


# --------------------------------------------------------------------------- #
# Weather
# --------------------------------------------------------------------------- #


def build_units(bundle: WeatherBundle) -> Units:
    """Read the units the provider echoed back, with the pinned defaults."""
    hourly = bundle.hourly_units or {}
    daily = bundle.daily_units or {}
    return Units(
        temperature=hourly.get("temperature_2m", "°C"),
        wind_speed=hourly.get("wind_speed_10m", "km/h"),
        precipitation=daily.get("precipitation_sum", "mm"),
    )


def condition_to_out(code: Any) -> WeatherConditionOut:
    """Resolve a raw WMO code into a label, icon and known/unknown flag."""
    condition = describe_weather_code(code)
    return WeatherConditionOut(
        label=condition.label,
        icon=condition.icon,
        is_known=condition.is_known,
    )


def daily_condition_to_out(row: Any) -> WeatherConditionOut:
    """Build a daily condition from a prepared daily frame row.

    The processing layer resolves each daily WMO code into ``condition`` and
    ``icon`` before the frame is handed to the presentation layer, so the
    prepared columns are the source of truth here. A raw ``weather_code``
    column, when a caller supplies one, takes precedence.
    """
    code = getattr(row, "weather_code", None)
    if code is not None:
        return condition_to_out(code)

    label = _text(getattr(row, "condition", "")) or MISSING_CONDITION.label
    icon = _text(getattr(row, "icon", "")) or MISSING_CONDITION.icon
    is_known = label != MISSING_CONDITION.label and not label.startswith(_UNKNOWN_LABEL_PREFIX)
    return WeatherConditionOut(label=label, icon=icon, is_known=is_known)


def current_to_out(conditions: CurrentConditions) -> CurrentConditionsOut:
    """Convert current conditions into their API representation."""
    return CurrentConditionsOut(
        observed_at=optional_datetime(conditions.observed_at),
        temperature_c=optional_float(conditions.temperature_c),
        feels_like_c=optional_float(conditions.feels_like_c),
        humidity_pct=optional_float(conditions.humidity_pct),
        wind_speed_kmh=optional_float(conditions.wind_speed_kmh),
        precipitation_mm=optional_float(conditions.precipitation_mm),
        weather_code=conditions.weather_code,
        condition=condition_to_out(conditions.weather_code),
        has_measurements=conditions.has_measurements,
    )


def hourly_to_out(frame: pd.DataFrame) -> list[HourlyPointOut]:
    """Convert the hourly window frame into API points, preserving gaps."""
    if frame is None or frame.empty:
        return []
    return [
        HourlyPointOut(
            time=optional_datetime(row.time),
            label=_text(row.label),
            temperature_c=optional_float(row.temperature),
            humidity_pct=optional_float(row.humidity),
            precipitation_probability_pct=optional_float(row.precipitation_probability),
            wind_speed_kmh=optional_float(row.wind_speed),
            apparent_temperature_c=optional_float(row.apparent_temperature),
        )
        for row in frame.itertuples(index=False)
    ]


def daily_to_out(frame: pd.DataFrame) -> list[DailyPointOut]:
    """Convert the daily forecast frame into API points."""
    if frame is None or frame.empty:
        return []
    points: list[DailyPointOut] = []
    for row in frame.itertuples(index=False):
        points.append(
            DailyPointOut(
                date=optional_datetime(row.date),
                label=_text(row.label),
                condition=daily_condition_to_out(row),
                temperature_max_c=optional_float(row.temperature_max),
                temperature_min_c=optional_float(row.temperature_min),
                precipitation_probability_max_pct=optional_float(
                    row.precipitation_probability_max
                ),
                precipitation_total_mm=optional_float(row.precipitation_total),
                wind_speed_max_kmh=optional_float(row.wind_speed_max),
                apparent_temperature_max_c=optional_float(row.apparent_temperature_max),
                humidity_mean_pct=optional_float(row.humidity_mean),
            )
        )
    return points


def _missing_count(frame: pd.DataFrame, column: str) -> int:
    """Count unreported values in ``column``, tolerating a missing frame."""
    if frame is None or frame.empty or column not in frame.columns:
        return 0
    return int(frame[column].isna().sum())


def build_summary(
    hourly: pd.DataFrame,
    daily: pd.DataFrame,
    *,
    hours: int,
) -> ForecastSummaryOut:
    """Summarise the returned window and its data quality.

    Args:
        hourly: Prepared hourly window frame.
        daily: Prepared daily frame.
        hours: Requested window size in hours.

    Returns:
        Window boundaries and the number of unreported values per block.
    """
    window_start = optional_datetime(hourly["time"].min()) if not hourly.empty else None
    window_end = optional_datetime(hourly["time"].max()) if not hourly.empty else None
    return ForecastSummaryOut(
        hours=hours,
        hours_count=0 if hourly is None else int(len(hourly)),
        days_count=0 if daily is None else int(len(daily)),
        window_start=window_start,
        window_end=window_end,
        missing_hourly_count=_missing_count(hourly, "temperature"),
        missing_daily_count=_missing_count(daily, "temperature_max"),
    )


def build_warnings(
    hourly: pd.DataFrame,
    daily: pd.DataFrame,
    conditions: CurrentConditions,
) -> list[str]:
    """Explain every degradation the client should surface to the user."""
    warnings: list[str] = []
    if hourly is None or hourly.empty:
        warnings.append(_NO_HOURLY_WARNING)
    if daily is None or daily.empty:
        warnings.append(_NO_DAILY_WARNING)
    if _missing_count(hourly, "temperature") or _missing_count(daily, "temperature_max"):
        warnings.append(_MISSING_VALUES_WARNING)
    if not conditions.has_measurements:
        warnings.append(
            "The weather service did not return any current measurements for this location."
        )
    return warnings


# --------------------------------------------------------------------------- #
# Chernoff faces
# --------------------------------------------------------------------------- #


def features_to_out(source: FaceSource) -> list[FaceFeatureOut]:
    """Describe the variable-to-feature mapping of one source."""
    return [
        FaceFeatureOut(
            variable=variable.key,
            label=variable.label,
            unit=variable.unit,
            feature=variable.feature,
            direction=variable.direction,
        )
        for variable in source.variables
    ]


def faces_to_out(frame: pd.DataFrame | None, source: FaceSource, count: int) -> ChernoffSourceOut:
    """Prepare the Chernoff faces for one forecast block.

    Normalisation happens across exactly the records returned, so the client
    only has to draw the faces.

    Args:
        frame: Hourly or daily frame from the processing layer.
        source: Which feature mapping to apply.
        count: Number of faces to prepare.

    Returns:
        The faces, their normalised encodings and the mapping legend.
    """
    rows = build_face_rows(frame, source, count)
    return ChernoffSourceOut(
        source=source.key,
        label=source.label,
        requested_count=count,
        faces=[
            FaceOut(
                label=row.label,
                summary=row.summary,
                tooltip=row.tooltip,
                values=row.values,
                spec=FaceSpecOut(
                    temperature=round(row.spec.temperature, 6),
                    humidity=round(row.spec.humidity, 6),
                    wind=round(row.spec.wind, 6),
                    precipitation=round(row.spec.precipitation, 6),
                    apparent_temperature=round(row.spec.apparent_temperature, 6),
                ),
            )
            for row in rows
        ],
        features=features_to_out(source),
        neutral_value=NEUTRAL,
    )


def build_chernoff(
    hourly: pd.DataFrame,
    daily: pd.DataFrame,
    *,
    count: int = DEFAULT_FACE_COUNT,
    sources: Sequence[str] | None = None,
) -> ChernoffOut:
    """Build the Chernoff payload for every requested source.

    Args:
        hourly: Hourly forecast frame.
        daily: Daily forecast frame.
        count: Faces to prepare per source.
        sources: Source keys to include. Defaults to every source that has
            usable data.

    Returns:
        A mapping of source key to its prepared faces.
    """
    frames: Mapping[str, pd.DataFrame] = {
        "hourly": hourly,
        "daily": daily,
    }
    selected = sources or tuple(key for key, frame in frames.items() if not frame.empty)
    return ChernoffOut(
        sources={key: faces_to_out(frames[key], FACE_SOURCES[key], count) for key in selected},
        note=CHERNOFF_NOTE,
    )


# --------------------------------------------------------------------------- #
# Whole responses
# --------------------------------------------------------------------------- #


def build_weather_response(
    bundle: WeatherBundle,
    conditions: CurrentConditions,
    hourly: pd.DataFrame,
    daily: pd.DataFrame,
    *,
    hours: int,
    forecast_days: int,
    cached: bool,
    cache_age_seconds: float,
    cache_ttl_seconds: int,
    chernoff_count: int = DEFAULT_FACE_COUNT,
) -> WeatherResponse:
    """Assemble the full forecast response returned by ``GET /api/weather``.

    Args:
        bundle: Validated forecast response.
        conditions: Processed current conditions.
        hourly: Prepared hourly window frame.
        daily: Prepared daily frame.
        hours: Requested window size in hours.
        forecast_days: Number of forecast days requested.
        cached: Whether the underlying response came from the cache.
        cache_age_seconds: Age of the cached response, when it was cached.
        cache_ttl_seconds: Configured TTL, echoed for the UI's freshness note.
        chernoff_count: Faces to prepare per Chernoff source.

    Returns:
        The complete weather payload.
    """
    return WeatherResponse(
        meta=WeatherMetaOut(
            latitude=bundle.latitude,
            longitude=bundle.longitude,
            timezone=bundle.timezone,
            timezone_abbreviation=bundle.timezone_abbreviation,
            utc_offset_seconds=bundle.utc_offset_seconds,
            elevation_m=optional_float(bundle.elevation),
            retrieved_at=bundle.retrieved_at,
            forecast_days=forecast_days,
            cached=cached,
            cache_age_seconds=round(cache_age_seconds, 3),
            cache_ttl_seconds=cache_ttl_seconds,
            units=build_units(bundle),
            provider=provider_info(),
        ),
        current=current_to_out(conditions),
        hourly=hourly_to_out(hourly),
        daily=daily_to_out(daily),
        summary=build_summary(hourly, daily, hours=hours),
        chernoff=build_chernoff(hourly, daily, count=chernoff_count),
        warnings=build_warnings(hourly, daily, conditions),
    )


def build_health(
    *,
    version: str,
    api_prefix: str,
    docs_url: str,
    cache_ttl_seconds: dict[str, int],
    cache_stats: Mapping[str, Mapping[str, int]],
    upstream: Mapping[str, str],
    frontend_served: bool,
) -> HealthResponse:
    """Build the health payload, including cache and upstream details."""
    return HealthResponse(
        status="ok",
        service=config.APP_TITLE,
        version=version,
        api_prefix=api_prefix,
        docs_url=docs_url,
        timestamp=datetime.now(UTC),
        python_version=platform.python_version(),
        cache_ttl_seconds=cache_ttl_seconds,
        cache={
            name: CacheStatsOut(
                entries=int(values.get("entries", 0)),
                live_entries=int(values.get("liveEntries", 0)),
                in_flight=int(values.get("inFlight", 0)),
            )
            for name, values in cache_stats.items()
        },
        upstream=dict(upstream),
        provider=provider_info(),
        frontend_dist_served=frontend_served,
    )


def build_app_config() -> AppConfigResponse:
    """Describe the static parts of the contract so a client can configure itself."""
    return AppConfigResponse(
        app_title=config.APP_TITLE,
        app_subtitle=config.APP_SUBTITLE,
        version=config.APP_VERSION,
        hours_choices=list(config.HOURLY_PERIOD_CHOICES),
        default_hours=config.DEFAULT_HOURLY_PERIOD,
        forecast_days=config.FORECAST_DAYS,
        min_forecast_days=config.MIN_FORECAST_DAYS,
        max_forecast_days=config.MAX_FORECAST_DAYS,
        face_count_choices=list(FACE_COUNT_CHOICES),
        default_face_count=DEFAULT_FACE_COUNT,
        units=Units(),
        provider=provider_info(),
        attribution=config.ATTRIBUTION,
        freshness_note=config.DATA_FRESHNESS_NOTE,
    )
