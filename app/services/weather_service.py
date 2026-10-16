"""Forecast service backed by the Open-Meteo Forecast API.

Exposes a single entry point, :func:`fetch_weather`, that returns a validated
:class:`WeatherBundle`. Timestamp parsing and reshaping are intentionally left
to :mod:`app.utils.data_processing` so this module stays a thin, testable API
adapter.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app import config
from app.services.exceptions import APIResponseError
from app.services.http_client import get_json

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class WeatherBundle:
    """A validated Forecast API response.

    Attributes:
        latitude: Latitude echoed by the provider (grid cell centre).
        longitude: Longitude echoed by the provider.
        timezone: IANA timezone the timestamps are expressed in.
        timezone_abbreviation: Short zone label, e.g. ``"GMT+5"``.
        utc_offset_seconds: Offset from UTC for the requested location.
        elevation: Terrain elevation in metres, when supplied.
        current: Current-conditions block, keyed by variable name.
        hourly: Hourly block containing parallel arrays.
        daily: Daily block containing parallel arrays.
        current_units: Unit metadata for the current block.
        hourly_units: Unit metadata for the hourly block.
        daily_units: Unit metadata for the daily block.
        retrieved_at: UTC instant at which this response was fetched.
    """

    latitude: float
    longitude: float
    timezone: str
    timezone_abbreviation: str
    utc_offset_seconds: int
    elevation: float | None
    current: Mapping[str, Any] = field(default_factory=dict)
    hourly: Mapping[str, Any] = field(default_factory=dict)
    daily: Mapping[str, Any] = field(default_factory=dict)
    current_units: Mapping[str, str] = field(default_factory=dict)
    hourly_units: Mapping[str, str] = field(default_factory=dict)
    daily_units: Mapping[str, str] = field(default_factory=dict)
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(UTC))


def fetch_weather(
    latitude: float,
    longitude: float,
    *,
    forecast_days: int = config.FORECAST_DAYS,
) -> WeatherBundle:
    """Fetch current conditions plus hourly and daily forecasts.

    Args:
        latitude: Latitude in decimal degrees (required by the API).
        longitude: Longitude in decimal degrees (required by the API).
        forecast_days: Number of days to request, clamped to 1-16 by the API.

    Returns:
        A validated :class:`WeatherBundle`.

    Raises:
        ValueError: ``forecast_days`` is outside the supported range.
        APIRateLimitError: The provider is rate limiting requests.
        APIResponseError: The payload is malformed or the request failed.
        NetworkRequestError: The provider could not be reached.
        APITimeoutError: The provider did not respond in time.
    """
    days = int(forecast_days)
    if not config.MIN_FORECAST_DAYS <= days <= config.MAX_FORECAST_DAYS:
        raise ValueError("forecast_days must be between 1 and 16 (Open-Meteo limit).")

    payload = get_json(
        config.FORECAST_API_URL,
        {
            "latitude": float(latitude),
            "longitude": float(longitude),
            "current": ",".join(config.CURRENT_VARIABLES),
            "hourly": ",".join(config.HOURLY_VARIABLES),
            "daily": ",".join(config.DAILY_VARIABLES),
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
            "precipitation_unit": "mm",
            "timezone": "auto",  # timestamps are returned in local time
            "forecast_days": days,
        },
    )

    bundle = _parse_forecast(payload)
    LOGGER.info(
        "Fetched forecast for (%.4f, %.4f) tz=%s days=%d",
        bundle.latitude,
        bundle.longitude,
        bundle.timezone,
        days,
    )
    return bundle


def _parse_forecast(payload: Mapping[str, Any]) -> WeatherBundle:
    """Validate the envelope of a Forecast API response.

    The provider always returns the three top-level blocks; treating a missing
    block as fatal keeps downstream processing simple and predictable.
    """
    for key in ("latitude", "longitude", "current", "hourly", "daily"):
        if payload.get(key) is None:
            LOGGER.error("Forecast payload missing required key: %s", key)
            raise APIResponseError(
                "The weather service returned an incomplete response. Please refresh."
            )

    for block_name in ("current", "hourly", "daily"):
        if not isinstance(payload[block_name], Mapping):
            LOGGER.error("Forecast block %r is not an object", block_name)
            raise APIResponseError("The weather service returned an unexpected response format.")

    return WeatherBundle(
        latitude=_as_float(payload.get("latitude"), default=0.0),
        longitude=_as_float(payload.get("longitude"), default=0.0),
        timezone=str(payload.get("timezone") or "UTC"),
        timezone_abbreviation=str(payload.get("timezone_abbreviation") or ""),
        utc_offset_seconds=int(_as_float(payload.get("utc_offset_seconds"), default=0.0)),
        elevation=_as_optional_float(payload.get("elevation")),
        current=dict(payload["current"]),
        hourly=dict(payload["hourly"]),
        daily=dict(payload["daily"]),
        current_units=_as_unit_map(payload.get("current_units")),
        hourly_units=_as_unit_map(payload.get("hourly_units")),
        daily_units=_as_unit_map(payload.get("daily_units")),
        retrieved_at=datetime.now(UTC),
    )


def _as_float(value: Any, *, default: float) -> float:
    """Coerce to ``float``, falling back to ``default`` when impossible."""
    try:
        return float(value)
    except (TypeError, ValueError):
        LOGGER.warning("Non-numeric value %r; using default %s", value, default)
        return default


def _as_optional_float(value: Any) -> float | None:
    """Coerce to ``float``, returning ``None`` for missing or invalid values."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_unit_map(value: Any) -> dict[str, str]:
    """Return the unit metadata mapping, or an empty dict when absent."""
    if isinstance(value, Mapping):
        return {str(key): str(item) for key, item in value.items()}
    return {}
