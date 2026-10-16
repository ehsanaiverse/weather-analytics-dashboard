"""Tests for the forecast endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import config
from tests.api.conftest import LATITUDE, LONGITUDE, full_forecast_payload, params_with_coordinates
from tests.conftest import REFERENCE_TIME, FakeResponse


def test_weather_returns_the_full_dashboard_payload(client: TestClient, fake_get) -> None:
    fake_get(FakeResponse(full_forecast_payload()))

    response = client.get("/api/weather", params=params_with_coordinates())

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"meta", "current", "hourly", "daily", "summary", "chernoff", "warnings"}


def test_weather_meta_reports_grid_timezone_and_units(client: TestClient, fake_get) -> None:
    fake_get(FakeResponse(full_forecast_payload()))

    meta = client.get("/api/weather", params=params_with_coordinates()).json()["meta"]

    assert meta["timezone"] == "Asia/Karachi"
    assert meta["timezoneAbbreviation"] == "GMT+5"
    assert meta["utcOffsetSeconds"] == 18000
    assert meta["elevationM"] == 1241.0
    assert meta["forecastDays"] == config.FORECAST_DAYS
    assert meta["units"] == {"temperature": "°C", "windSpeed": "km/h", "precipitation": "mm"}
    assert meta["provider"]["license"] == "CC BY 4.0"
    assert meta["cached"] is False
    assert meta["cacheTtlSeconds"] == config.WEATHER_CACHE_TTL_SECONDS


def test_retrieval_time_is_returned_in_utc(client: TestClient, fake_get) -> None:
    fake_get(FakeResponse(full_forecast_payload()))

    meta = client.get("/api/weather", params=params_with_coordinates()).json()["meta"]

    assert meta["retrievedAt"].endswith("Z")


def test_current_conditions_are_extracted(client: TestClient, fake_get) -> None:
    fake_get(FakeResponse(full_forecast_payload()))

    current = client.get("/api/weather", params=params_with_coordinates()).json()["current"]

    assert current["temperatureC"] == pytest.approx(25.4)
    assert current["feelsLikeC"] == pytest.approx(25.6)
    assert current["humidityPct"] == pytest.approx(45)
    assert current["windSpeedKmh"] == pytest.approx(3.9)
    assert current["precipitationMm"] == pytest.approx(0.0)
    assert current["weatherCode"] == 2
    assert current["condition"] == {"label": "Partly cloudy", "icon": "⛅", "isKnown": True}
    assert current["hasMeasurements"] is True
    assert current["observedAt"] == "2026-10-02T09:15:00"


def test_hourly_window_defaults_to_24_hours(client: TestClient, fake_get) -> None:
    fake_get(FakeResponse(full_forecast_payload()))

    body = client.get("/api/weather", params=params_with_coordinates()).json()

    assert len(body["hourly"]) == 24
    assert body["summary"]["hours"] == 24
    assert body["summary"]["hoursCount"] == 24
    assert body["summary"]["daysCount"] == 7


@pytest.mark.parametrize(("hours", "expected"), [(12, 12), (24, 24), (48, 48)])
def test_every_supported_window_is_sliced(
    client: TestClient, fake_get, hours: int, expected: int
) -> None:
    fake_get(FakeResponse(full_forecast_payload()))

    body = client.get("/api/weather", params=params_with_coordinates(hours=hours)).json()

    assert len(body["hourly"]) == expected
    assert body["summary"]["hours"] == hours


def test_hourly_points_carry_every_variable_the_charts_need(
    client: TestClient, fake_get
) -> None:
    fake_get(FakeResponse(full_forecast_payload()))

    point = client.get("/api/weather", params=params_with_coordinates()).json()["hourly"][0]

    assert set(point) == {
        "time",
        "label",
        "temperatureC",
        "humidityPct",
        "precipitationProbabilityPct",
        "windSpeedKmh",
        "apparentTemperatureC",
    }
    assert point["label"] == "Fri 09:00"
    assert point["time"] == "2026-10-02T09:00:00"


def test_daily_points_carry_every_variable_the_charts_need(
    client: TestClient, fake_get
) -> None:
    fake_get(FakeResponse(full_forecast_payload()))

    body = client.get("/api/weather", params=params_with_coordinates()).json()

    assert len(body["daily"]) == 7
    point = body["daily"][0]
    assert set(point) == {
        "date",
        "label",
        "condition",
        "temperatureMaxC",
        "temperatureMinC",
        "precipitationProbabilityMaxPct",
        "precipitationTotalMm",
        "windSpeedMaxKmh",
        "apparentTemperatureMaxC",
        "humidityMeanPct",
    }
    assert point["label"] == "Fri 02 Oct"
    assert point["condition"]["label"] == "Clear sky"
    assert point["condition"]["isKnown"] is True


def test_daily_conditions_are_resolved_from_the_wmo_codes(
    client: TestClient, fake_get
) -> None:
    fake_get(FakeResponse(full_forecast_payload()))

    daily = client.get("/api/weather", params=params_with_coordinates()).json()["daily"]

    assert [point["condition"]["label"] for point in daily] == [
        "Clear sky",
        "Mainly clear",
        "Partly cloudy",
        "Overcast",
        "Slight rain",
        "Thunderstorm",
        "Fog",
    ]


def test_response_is_valid_json_without_nan_tokens(client: TestClient, fake_get) -> None:
    """``NaN`` is not valid JSON, so a missing value must be ``null``."""
    payload = full_forecast_payload()
    payload["hourly"]["wind_speed_10m"] = [None] * len(payload["hourly"]["time"])
    payload["daily"]["relative_humidity_2m_mean"] = [None] * 7
    fake_get(FakeResponse(payload))

    response = client.get("/api/weather", params=params_with_coordinates())

    assert response.status_code == 200
    assert "NaN" not in response.text
    assert "Infinity" not in response.text
    body = response.json()
    assert body["hourly"][0]["windSpeedKmh"] is None
    assert body["daily"][0]["humidityMeanPct"] is None


def test_missing_measurements_are_null_and_never_zero(client: TestClient, fake_get) -> None:
    payload = full_forecast_payload()
    timestamps = payload["hourly"]["time"]
    payload["hourly"]["temperature_2m"] = [20.0] * len(timestamps)
    payload["hourly"]["temperature_2m"][3] = None
    fake_get(FakeResponse(payload))

    hourly = client.get("/api/weather", params=params_with_coordinates()).json()["hourly"]

    assert hourly[3]["temperatureC"] is None
    assert hourly[2]["temperatureC"] == pytest.approx(20.0)


def test_missing_measurements_raise_a_warning(client: TestClient, fake_get) -> None:
    payload = full_forecast_payload()
    timestamps = payload["hourly"]["time"]
    payload["hourly"]["temperature_2m"] = [None] * len(timestamps)
    fake_get(FakeResponse(payload))

    body = client.get("/api/weather", params=params_with_coordinates()).json()

    assert body["summary"]["missingHourlyCount"] > 0
    assert any("not reported" in warning for warning in body["warnings"])


def test_a_zero_measurement_stays_zero(client: TestClient, fake_get) -> None:
    payload = full_forecast_payload()
    payload["hourly"]["precipitation_probability"] = [0] * len(payload["hourly"]["time"])
    fake_get(FakeResponse(payload))

    response = client.get("/api/weather", params=params_with_coordinates())
    hourly = response.json()["hourly"]

    assert response.headers["content-type"].startswith("application/json")
    assert hourly[0]["precipitationProbabilityPct"] == 0.0


def test_unusable_hourly_block_returns_empty_lists_and_a_warning(
    client: TestClient, fake_get
) -> None:
    payload = full_forecast_payload()
    payload["hourly"] = {"time": ["not-a-timestamp"], "temperature_2m": [1.0]}
    fake_get(FakeResponse(payload))

    body = client.get("/api/weather", params=params_with_coordinates()).json()

    assert body["hourly"] == []
    assert body["summary"]["hoursCount"] == 0
    assert any("hourly data" in warning for warning in body["warnings"])
    assert body["chernoff"]["sources"] == {"daily": body["chernoff"]["sources"]["daily"]}
    assert "hourly" not in body["chernoff"]["sources"]


def test_current_block_without_measurements_is_reported(client: TestClient, fake_get) -> None:
    payload = full_forecast_payload()
    payload["current"] = {
        "time": REFERENCE_TIME,
        "interval": 900,
        "temperature_2m": None,
        "relative_humidity_2m": None,
        "apparent_temperature": None,
        "precipitation": None,
        "weather_code": None,
        "wind_speed_10m": None,
    }
    fake_get(FakeResponse(payload))

    body = client.get("/api/weather", params=params_with_coordinates()).json()

    assert body["current"]["hasMeasurements"] is False
    assert body["current"]["temperatureC"] is None
    assert body["current"]["condition"]["isKnown"] is False
    assert any("current measurements" in warning for warning in body["warnings"])


def test_hourly_window_uses_the_reference_time_not_the_wall_clock(
    client: TestClient, fake_get
) -> None:
    fake_get(FakeResponse(full_forecast_payload()))

    hourly = client.get("/api/weather", params=params_with_coordinates(hours=12)).json()["hourly"]

    assert hourly[0]["time"] == "2026-10-02T09:00:00"


@pytest.mark.parametrize("hours", [0, 13, 100, -1])
def test_unsupported_window_is_rejected(client: TestClient, fake_get, hours: int) -> None:
    calls = fake_get(FakeResponse(full_forecast_payload()))

    response = client.get("/api/weather", params=params_with_coordinates(hours=hours))

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"
    assert calls == []


@pytest.mark.parametrize("days", [0, 17, 400])
def test_forecast_days_outside_the_provider_limit_are_rejected(
    client: TestClient, fake_get, days: int
) -> None:
    calls = fake_get(FakeResponse(full_forecast_payload()))

    response = client.get("/api/weather", params=params_with_coordinates(forecast_days=days))

    assert response.status_code == 400
    assert calls == []


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [(91.0, 0.0), (-91.0, 0.0), (0.0, 181.0), (0.0, -181.0)],
)
def test_coordinates_outside_the_globe_are_rejected(
    client: TestClient, fake_get, latitude: float, longitude: float
) -> None:
    calls = fake_get(FakeResponse(full_forecast_payload()))

    response = client.get("/api/weather", params={"latitude": latitude, "longitude": longitude})

    assert response.status_code == 400
    assert calls == []


def test_non_numeric_coordinates_are_rejected(client: TestClient, fake_get) -> None:
    calls = fake_get(FakeResponse(full_forecast_payload()))

    response = client.get("/api/weather", params={"latitude": "north", "longitude": LONGITUDE})

    assert response.status_code == 400
    assert calls == []


def test_missing_coordinate_parameters_are_rejected(client: TestClient, fake_get) -> None:
    calls = fake_get(FakeResponse(full_forecast_payload()))

    assert client.get("/api/weather", params={"latitude": LATITUDE}).status_code == 400
    assert client.get("/api/weather").status_code == 400
    assert calls == []


def test_unsupported_chernoff_face_count_is_rejected(client: TestClient, fake_get) -> None:
    fake_get(FakeResponse(full_forecast_payload()))

    response = client.get(
        "/api/weather", params=params_with_coordinates(chernoff_count=5)
    )

    assert response.status_code == 400
    assert "chernoff_count" in response.json()["error"]["message"]


def test_upstream_server_error_maps_to_502(client: TestClient, fake_get) -> None:
    fake_get(FakeResponse({}, status_code=503, text="unavailable"))

    response = client.get("/api/weather", params=params_with_coordinates())

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "upstream_bad_response"


def test_error_flagged_success_body_maps_to_502(client: TestClient, fake_get) -> None:
    fake_get(FakeResponse({"error": True, "reason": "Cannot initialize WeatherCode"}))

    response = client.get("/api/weather", params=params_with_coordinates())

    assert response.status_code == 502
    assert "Cannot initialize WeatherCode" in response.json()["error"]["message"]


def test_incomplete_envelope_maps_to_502(client: TestClient, fake_get) -> None:
    fake_get(FakeResponse({"latitude": 34.0, "longitude": 73.0}))

    response = client.get("/api/weather", params=params_with_coordinates())

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "upstream_bad_response"


def test_malformed_json_maps_to_502(client: TestClient, fake_get) -> None:
    fake_get(FakeResponse(invalid_json=True, text="not json"))

    response = client.get("/api/weather", params=params_with_coordinates())

    assert response.status_code == 502
