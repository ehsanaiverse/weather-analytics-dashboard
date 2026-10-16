"""Shared pytest fixtures and payload builders.

Every test in this suite runs fully offline: ``requests.get`` is replaced with a
recording stub, and an autouse fixture blocks real socket connections so a
missing mock fails loudly instead of silently hitting the network.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd
import pytest

from app.services import http_client
from app.services.weather_service import WeatherBundle

#: Fixed reference point so all timestamp assertions are deterministic.
REFERENCE_TIME = "2026-10-02T09:15"


class FakeResponse:
    """Minimal stand-in for :class:`requests.Response`."""

    def __init__(
        self,
        payload: Any = None,
        status_code: int = 200,
        text: str | None = None,
        invalid_json: bool = False,
    ) -> None:
        """Store a canned response.

        Args:
            payload: Object returned by :meth:`json`.
            status_code: HTTP status code to report.
            text: Body text returned by the ``text`` property.
            invalid_json: When true, :meth:`json` raises ``ValueError``.
        """
        self._payload = payload
        self.status_code = status_code
        self._invalid_json = invalid_json
        self._text = text if text is not None else ""

    def json(self) -> Any:
        if self._invalid_json:
            raise ValueError("Expecting value: line 1 column 1 (char 0)")
        return self._payload

    @property
    def text(self) -> str:
        return self._text


@pytest.fixture(autouse=True)
def block_real_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent any test from opening a real network connection."""

    def _blocked(*args: Any, **kwargs: Any) -> None:
        raise AssertionError(
            "Unit tests must not perform real network requests. "
            "Install the fake_get fixture to stub requests.get."
        )

    monkeypatch.setattr(http_client.requests.Session, "send", _blocked)


@pytest.fixture
def fake_get(monkeypatch: pytest.MonkeyPatch):
    """Return a factory that stubs ``requests.get`` and records the calls.

    Usage::

        calls = fake_get(FakeResponse({"ok": True}))
        ...
        assert calls[0]["params"]["latitude"] == 34.1
    """
    recorded: list[dict[str, Any]] = []

    def _install(response: Any = None, error: Exception | None = None) -> list[dict[str, Any]]:
        def _stub(url: str, params=None, timeout=None, headers=None) -> Any:
            recorded.append(
                {"url": url, "params": params, "timeout": timeout, "headers": headers}
            )
            if error is not None:
                raise error
            return response

        monkeypatch.setattr(http_client.requests, "get", _stub)
        return recorded

    return _install


# --------------------------------------------------------------------------- #
# Payload builders
# --------------------------------------------------------------------------- #


def hourly_times(count: int, start: str = REFERENCE_TIME) -> list[str]:
    """``count`` consecutive hourly timestamps in Open-Meteo ISO format."""
    base = pd.Timestamp(start).floor("h")
    return [
        (base + pd.Timedelta(hours=index)).strftime("%Y-%m-%dT%H:%M")
        for index in range(count)
    ]


def daily_times(count: int, start: str = REFERENCE_TIME) -> list[str]:
    """``count`` consecutive daily dates in Open-Meteo ISO format."""
    base = pd.Timestamp(start).floor("D")
    return [
        (base + pd.Timedelta(days=index)).strftime("%Y-%m-%d")
        for index in range(count)
    ]


def make_forecast_payload(
    *,
    start: str = REFERENCE_TIME,
    hours: int = 168,
    days: int = 7,
    current: dict[str, Any] | None = None,
    hourly: dict[str, Any] | None = None,
    daily: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a realistic Forecast API payload, overridable block by block."""
    timestamps = hourly_times(hours, start)
    default_current = {
        "time": start,
        "interval": 900,
        "temperature_2m": 25.4,
        "relative_humidity_2m": 45,
        "apparent_temperature": 25.6,
        "precipitation": 0.0,
        "weather_code": 2,
        "wind_speed_10m": 3.9,
    }
    dates = daily_times(days, start)
    default_hourly = {
        "time": timestamps,
        "temperature_2m": [20.0 + (index % 8) for index in range(len(timestamps))],
        "relative_humidity_2m": [40 + (index % 30) for index in range(len(timestamps))],
        "precipitation_probability": [index % 4 * 25 for index in range(len(timestamps))],
    }
    default_daily = {
        "time": dates,
        "weather_code": [0, 1, 2, 3, 61, 95, 45],
        "temperature_2m_max": [26.6, 27.1, 27.4, 26.4, 24.3, 23.4, 22.8],
        "temperature_2m_min": [19.1, 19.8, 19.8, 18.7, 17.9, 15.9, 15.7],
        "precipitation_probability_max": [0, 0, 10, 20, 60, 98, 73],
        "precipitation_sum": [0.0, 0.0, 0.2, 0.5, 3.1, 8.4, 2.2],
    }

    payload: dict[str, Any] = {
        "latitude": 34.1463,
        "longitude": 73.21168,
        "generationtime_ms": 0.4,
        "utc_offset_seconds": 18000,
        "timezone": "Asia/Karachi",
        "timezone_abbreviation": "GMT+5",
        "elevation": 1241.0,
        "current_units": {
            "time": "iso8601",
            "interval": "seconds",
            "temperature_2m": "°C",
            "relative_humidity_2m": "%",
            "apparent_temperature": "°C",
            "precipitation": "mm",
            "weather_code": "wmo code",
            "wind_speed_10m": "km/h",
        },
        "hourly_units": {
            "time": "iso8601",
            "temperature_2m": "°C",
            "relative_humidity_2m": "%",
            "precipitation_probability": "%",
        },
        "daily_units": {
            "time": "iso8601",
            "weather_code": "wmo code",
            "temperature_2m_max": "°C",
            "temperature_2m_min": "°C",
            "precipitation_probability_max": "%",
            "precipitation_sum": "mm",
        },
        "current": default_current if current is None else current,
        "hourly": default_hourly if hourly is None else hourly,
        "daily": default_daily if daily is None else daily,
    }
    return payload


def make_bundle(
    *,
    start: str = REFERENCE_TIME,
    hours: int = 168,
    days: int = 7,
    current: dict[str, Any] | None = None,
    hourly: dict[str, Any] | None = None,
    daily: dict[str, Any] | None = None,
) -> WeatherBundle:
    """Build a :class:`WeatherBundle` directly, bypassing HTTP entirely."""
    payload = make_forecast_payload(
        start=start, hours=hours, days=days, current=current, hourly=hourly, daily=daily
    )
    return WeatherBundle(
        latitude=payload["latitude"],
        longitude=payload["longitude"],
        timezone=payload["timezone"],
        timezone_abbreviation=payload["timezone_abbreviation"],
        utc_offset_seconds=payload["utc_offset_seconds"],
        elevation=payload["elevation"],
        current=payload["current"],
        hourly=payload["hourly"],
        daily=payload["daily"],
        current_units=payload["current_units"],
        hourly_units=payload["hourly_units"],
        daily_units=payload["daily_units"],
        retrieved_at=datetime(2026, 10, 2, 9, 20, tzinfo=UTC),
    )


def make_geocoding_payload(results: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Build a Geocoding API payload, defaulting to two Abbottabad matches."""
    if results is None:
        results = [
            {
                "id": 1185056,
                "name": "Abbottabad",
                "latitude": 34.1463,
                "longitude": 73.21168,
                "elevation": 1241.0,
                "feature_code": "PPLA2",
                "country_code": "PK",
                "admin1": "Khyber Pakhtunkhwa",
                "timezone": "Asia/Karachi",
                "population": 275890,
                "country": "Pakistan",
            },
            {
                "id": 1185054,
                "name": "Abbottabad Lines",
                "latitude": 24.9509,
                "longitude": 67.2029,
                "elevation": 52.0,
                "feature_code": "PPLX",
                "country_code": "PK",
                "admin1": "Sindh",
                "timezone": "Asia/Karachi",
                "population": 21000,
                "country": "Pakistan",
            },
        ]
    return {"results": results, "generationtime_ms": 0.39}
