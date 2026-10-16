"""Tests for the forecast service and the shared HTTP client.

All HTTP is mocked, so these tests cover response parsing, schema validation,
timeouts, connection failures, rate limits and malformed payloads.
"""

from __future__ import annotations

from datetime import UTC

import pytest
import requests

from app import config
from app.services.exceptions import (
    APIRateLimitError,
    APIResponseError,
    APITimeoutError,
    NetworkRequestError,
)
from app.services.weather_service import fetch_weather
from tests.conftest import FakeResponse, make_forecast_payload

LATITUDE = 34.1463
LONGITUDE = 73.21168


class TestSuccessfulFetch:
    """A well-formed response must be validated into a WeatherBundle."""

    def test_parses_the_full_envelope(self, fake_get) -> None:
        fake_get(FakeResponse(make_forecast_payload()))

        bundle = fetch_weather(LATITUDE, LONGITUDE)

        assert bundle.latitude == pytest.approx(34.1463)
        assert bundle.longitude == pytest.approx(73.21168)
        assert bundle.timezone == "Asia/Karachi"
        assert bundle.timezone_abbreviation == "GMT+5"
        assert bundle.utc_offset_seconds == 18000
        assert bundle.elevation == pytest.approx(1241.0)
        assert bundle.current["temperature_2m"] == pytest.approx(25.4)
        assert len(bundle.hourly["time"]) == 168
        assert len(bundle.daily["time"]) == 7
        assert bundle.current_units["temperature_2m"] == "°C"
        assert bundle.hourly_units["precipitation_probability"] == "%"

    def test_records_retrieval_time_in_utc(self, fake_get) -> None:
        fake_get(FakeResponse(make_forecast_payload()))

        bundle = fetch_weather(LATITUDE, LONGITUDE)

        assert bundle.retrieved_at.tzinfo is not None
        assert bundle.retrieved_at.utcoffset() == UTC.utcoffset(None)

    def test_requests_only_the_declared_variables(self, fake_get) -> None:
        calls = fake_get(FakeResponse(make_forecast_payload()))

        fetch_weather(LATITUDE, LONGITUDE)

        params = calls[0]["params"]
        assert params["current"].split(",") == list(config.CURRENT_VARIABLES)
        assert params["hourly"].split(",") == list(config.HOURLY_VARIABLES)
        assert params["daily"].split(",") == list(config.DAILY_VARIABLES)

    def test_uses_local_timezone_and_project_units(self, fake_get) -> None:
        calls = fake_get(FakeResponse(make_forecast_payload()))

        fetch_weather(LATITUDE, LONGITUDE)

        params = calls[0]["params"]
        assert params["timezone"] == "auto"
        assert params["temperature_unit"] == "celsius"
        assert params["wind_speed_unit"] == "kmh"
        assert params["precipitation_unit"] == "mm"
        assert params["forecast_days"] == config.FORECAST_DAYS

    def test_calls_the_official_endpoint_with_a_timeout_and_user_agent(self, fake_get) -> None:
        calls = fake_get(FakeResponse(make_forecast_payload()))

        fetch_weather(LATITUDE, LONGITUDE)

        call = calls[0]
        assert call["url"] == "https://api.open-meteo.com/v1/forecast"
        assert call["timeout"] == config.REQUEST_TIMEOUT_SECONDS
        assert config.USER_AGENT in call["headers"]["User-Agent"]

    def test_accepts_a_custom_forecast_length(self, fake_get) -> None:
        calls = fake_get(FakeResponse(make_forecast_payload(days=3, hours=72)))

        fetch_weather(LATITUDE, LONGITUDE, forecast_days=3)

        assert calls[0]["params"]["forecast_days"] == 3


class TestRequestValidation:
    """Invalid arguments fail fast, before any network call."""

    @pytest.mark.parametrize("days", [0, -1, 17, 30])
    def test_forecast_days_outside_the_api_range_is_rejected(self, days: int) -> None:
        with pytest.raises(ValueError, match="forecast_days"):
            fetch_weather(LATITUDE, LONGITUDE, forecast_days=days)


class TestTransportFailures:
    """Network-level problems surface as typed, user-friendly errors."""

    def test_timeout_raises_api_timeout_error(self, fake_get) -> None:
        fake_get(error=requests.Timeout("read timed out"))

        with pytest.raises(APITimeoutError, match="did not respond"):
            fetch_weather(LATITUDE, LONGITUDE)

    def test_connection_failure_raises_network_error(self, fake_get) -> None:
        fake_get(error=requests.ConnectionError("name resolution failed"))

        with pytest.raises(NetworkRequestError, match="internet connection"):
            fetch_weather(LATITUDE, LONGITUDE)

    def test_generic_request_exception_raises_network_error(self, fake_get) -> None:
        fake_get(error=requests.RequestException("boom"))

        with pytest.raises(NetworkRequestError):
            fetch_weather(LATITUDE, LONGITUDE)

    def test_timeout_error_is_a_network_error(self, fake_get) -> None:
        """Callers can catch NetworkRequestError to handle all transport issues."""
        fake_get(error=requests.Timeout("slow"))

        with pytest.raises(NetworkRequestError):
            fetch_weather(LATITUDE, LONGITUDE)


class TestHttpFailures:
    """Non-2xx responses are translated into the right exception type."""

    def test_rate_limit_is_reported_as_such(self, fake_get) -> None:
        fake_get(FakeResponse({}, status_code=429, text="Too Many Requests"))

        with pytest.raises(APIRateLimitError, match="too many requests"):
            fetch_weather(LATITUDE, LONGITUDE)

    @pytest.mark.parametrize("status", [400, 401, 403, 404, 500, 502, 503])
    def test_other_http_errors_raise_api_response_error(self, status: int, fake_get) -> None:
        fake_get(FakeResponse({}, status_code=status, text="error"))

        with pytest.raises(APIResponseError, match=str(status)):
            fetch_weather(LATITUDE, LONGITUDE)


class TestMalformedResponses:
    """Unparseable or incomplete payloads must never reach the UI."""

    def test_invalid_json_raises_api_response_error(self, fake_get) -> None:
        fake_get(FakeResponse(invalid_json=True, text="<html>oops</html>"))

        with pytest.raises(APIResponseError, match="malformed"):
            fetch_weather(LATITUDE, LONGITUDE)

    @pytest.mark.parametrize("payload", [[1, 2, 3], "just a string", 42])
    def test_non_object_json_root_is_rejected(self, payload: object, fake_get) -> None:
        fake_get(FakeResponse(payload))

        with pytest.raises(APIResponseError, match="unexpected response format"):
            fetch_weather(LATITUDE, LONGITUDE)

    def test_error_flag_in_a_200_response_is_surfaced(self, fake_get) -> None:
        fake_get(FakeResponse({"error": True, "reason": "Latitude must be in -90..90"}))

        with pytest.raises(APIResponseError, match="Latitude must be"):
            fetch_weather(LATITUDE, LONGITUDE)

    @pytest.mark.parametrize("missing", ["latitude", "longitude", "current", "hourly", "daily"])
    def test_missing_top_level_key_is_rejected(self, missing: str, fake_get) -> None:
        payload = make_forecast_payload()
        payload.pop(missing)

        fake_get(FakeResponse(payload))

        with pytest.raises(APIResponseError, match="incomplete response"):
            fetch_weather(LATITUDE, LONGITUDE)

    @pytest.mark.parametrize("block", ["current", "hourly", "daily"])
    def test_non_object_block_is_rejected(self, block: str, fake_get) -> None:
        payload = make_forecast_payload()
        payload[block] = ["not", "an", "object"]

        fake_get(FakeResponse(payload))

        with pytest.raises(APIResponseError, match="unexpected response format"):
            fetch_weather(LATITUDE, LONGITUDE)


class TestOptionalFields:
    """Optional metadata may be absent without breaking the fetch."""

    def test_missing_metadata_falls_back_to_safe_defaults(self, fake_get) -> None:
        payload = make_forecast_payload()
        for key in ("elevation", "current_units", "hourly_units", "daily_units",
                    "timezone_abbreviation"):
            payload.pop(key, None)

        fake_get(FakeResponse(payload))

        bundle = fetch_weather(LATITUDE, LONGITUDE)

        assert bundle.elevation is None
        assert bundle.timezone_abbreviation == ""
        assert bundle.current_units == {}
        assert bundle.hourly_units == {}
        assert bundle.daily_units == {}

    def test_non_numeric_utc_offset_falls_back_to_zero(self, fake_get) -> None:
        payload = make_forecast_payload()
        payload["utc_offset_seconds"] = "not-a-number"

        fake_get(FakeResponse(payload))

        bundle = fetch_weather(LATITUDE, LONGITUDE)

        assert bundle.utc_offset_seconds == 0
        assert bundle.timezone == "Asia/Karachi"
