"""Shared fixtures for the HTTP API tests.

Every test in this package runs fully offline: the ``fake_get`` fixture from
``tests/conftest.py`` stubs ``requests.get`` and the autouse guard there blocks
real socket connections, so a missing mock fails loudly.

The API caches live in a process-wide registry (the equivalent of
``st.cache_data`` for the HTTP layer), so each test starts from empty caches.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.cache import ALL_CACHES
from app.api.deps import get_registry
from app.api.settings import ApiSettings
from app.main import create_application
from tests.conftest import (
    REFERENCE_TIME,
    daily_times,
    hourly_times,
    make_forecast_payload,
    make_geocoding_payload,
)

#: Coordinates used throughout the API tests (Abbottabad, Pakistan).
LATITUDE = 34.1463
LONGITUDE = 73.2117


@pytest.fixture(autouse=True)
def clear_api_caches() -> Iterator[None]:
    """Give every test empty caches, so cache assertions are deterministic."""
    get_registry().clear(ALL_CACHES)
    yield
    get_registry().clear(ALL_CACHES)


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Return a test client for a freshly built application."""
    with TestClient(create_application(ApiSettings())) as test_client:
        yield test_client


@pytest.fixture
def coordinates() -> dict[str, float]:
    """Return valid query parameters for the default test location."""
    return {"latitude": LATITUDE, "longitude": LONGITUDE}


def full_forecast_payload(
    *,
    start: str = REFERENCE_TIME,
    hours: int = 168,
    days: int = 7,
    current: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a forecast payload with every variable the dashboard uses.

    The shared builder in ``tests/conftest.py`` omits the Chernoff-specific
    fields, so this helper fills them in to exercise the full response contract.

    Args:
        start: ISO timestamp of the current block.
        hours: Number of hourly points.
        days: Number of daily points.
        current: Replacement current-conditions block.

    Returns:
        A complete Forecast API payload.
    """
    timestamps = hourly_times(hours, start)
    dates = daily_times(days, start)
    return make_forecast_payload(
        start=start,
        hours=hours,
        days=days,
        current=current,
        hourly={
            "time": timestamps,
            "temperature_2m": [18.0 + (index % 9) for index in range(len(timestamps))],
            "relative_humidity_2m": [35 + (index % 45) for index in range(len(timestamps))],
            "precipitation_probability": [index % 5 * 20 for index in range(len(timestamps))],
            "wind_speed_10m": [2.0 + (index % 12) for index in range(len(timestamps))],
            "apparent_temperature": [16.0 + (index % 11) for index in range(len(timestamps))],
        },
        daily={
            "time": dates,
            "weather_code": [0, 1, 2, 3, 61, 95, 45],
            "temperature_2m_max": [26.6, 27.1, 27.4, 26.4, 24.3, 23.4, 22.8],
            "temperature_2m_min": [19.1, 19.8, 19.8, 18.7, 17.9, 15.9, 15.7],
            "precipitation_probability_max": [0, 0, 10, 20, 60, 98, 73],
            "precipitation_sum": [0.0, 0.0, 0.2, 0.5, 3.1, 8.4, 2.2],
            "wind_speed_10m_max": [9.0, 11.0, 14.5, 12.0, 22.0, 31.0, 18.0],
            "apparent_temperature_max": [28.0, 29.5, 30.0, 28.5, 25.0, 21.0, 20.5],
            "relative_humidity_2m_mean": [48, 52, 55, 61, 74, 88, 79],
        },
    )


def geocoding_payload(results: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Build a Geocoding API payload, defaulting to two Abbottabad matches."""
    return make_geocoding_payload(results)


def params_with_coordinates(**extra: Any) -> dict[str, Any]:
    """Return query parameters for the default location plus ``extra``."""
    return {"latitude": LATITUDE, "longitude": LONGITUDE, **extra}
