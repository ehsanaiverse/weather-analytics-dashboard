"""Tests for the health and static-configuration endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app import config
from app.api.errors import REQUEST_ID_HEADER
from app.api.settings import ApiSettings
from app.main import create_application


def test_health_reports_status_and_cache_policy(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == config.APP_VERSION
    assert body["apiPrefix"] == config.API_PREFIX
    assert body["authentication"] == "none"


def test_health_reports_whether_a_built_frontend_is_served(client: TestClient) -> None:
    """The answer depends on whether `frontend/dist` exists, so derive it."""
    body = client.get("/api/health").json()

    assert body["frontendDistServed"] is Path(config.FRONTEND_DIST_PATH).is_dir()


def test_a_built_frontend_is_served_from_the_api(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>spa</title>", encoding="utf-8")

    with TestClient(create_application(ApiSettings(frontend_dist=dist))) as static_client:
        response = static_client.get("/")

    assert response.status_code == 200
    assert "spa" in response.text


def test_the_frontend_mount_can_be_switched_off(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>spa</title>", encoding="utf-8")

    with TestClient(
        create_application(ApiSettings(frontend_dist=dist, serve_frontend=False))
    ) as api_only:
        assert api_only.get("/api/health").status_code == 200
        assert api_only.get("/").status_code == 404


def test_health_preserves_the_existing_cache_durations(client: TestClient) -> None:
    body = client.get("/api/health").json()

    assert body["cacheTtlSeconds"]["weather"] == config.WEATHER_CACHE_TTL_SECONDS == 600
    assert body["cacheTtlSeconds"]["geocoding"] == config.GEOCODING_CACHE_TTL_SECONDS == 3600


def test_health_lists_public_upstream_endpoints_only(client: TestClient) -> None:
    body = client.get("/api/health").json()

    assert body["upstream"]["forecast"] == config.FORECAST_API_URL
    assert body["upstream"]["geocoding"] == config.GEOCODING_API_URL
    assert set(body["upstream"]) == {"forecast", "geocoding"}


def test_health_never_exposes_credentials(client: TestClient) -> None:
    response = client.get("/api/health")
    text = response.text.lower()

    for secret_marker in ("api_key", "apikey", "token", "password", "secret", "authorization"):
        assert secret_marker not in text


def test_health_includes_cache_statistics(client: TestClient) -> None:
    body = client.get("/api/health").json()

    assert set(body["cache"]) == {"weather", "geocoding"}
    assert body["cache"]["weather"]["entries"] == 0
    assert body["cache"]["geocoding"]["liveEntries"] == 0


def test_every_response_carries_a_correlation_id(client: TestClient) -> None:
    response = client.get("/api/health")

    assert REQUEST_ID_HEADER in response.headers
    assert len(response.headers[REQUEST_ID_HEADER]) == 12


def test_incoming_correlation_id_is_preserved(client: TestClient) -> None:
    response = client.get("/api/health", headers={REQUEST_ID_HEADER: "trace-me-01"})

    assert response.headers[REQUEST_ID_HEADER] == "trace-me-01"


def test_config_describes_the_client_contract(client: TestClient) -> None:
    body = client.get("/api/config").json()

    assert body["hoursChoices"] == list(config.HOURLY_PERIOD_CHOICES)
    assert body["defaultHours"] == config.DEFAULT_HOURLY_PERIOD
    assert body["forecastDays"] == config.FORECAST_DAYS
    assert body["faceCountChoices"] == [4, 6, 8, 12]
    assert body["units"] == {"temperature": "°C", "windSpeed": "km/h", "precipitation": "mm"}
    assert "Open-Meteo" in body["attribution"]


def test_openapi_schema_is_served_under_the_api_prefix(client: TestClient) -> None:
    response = client.get(config.API_OPENAPI_PATH)

    assert response.status_code == 200
    assert "/api/weather" in response.json()["paths"]


def test_openapi_documents_the_real_validation_status(client: TestClient) -> None:
    """Validation answers 400, so the generated 422 entry must not be advertised."""
    schema = client.get(config.API_OPENAPI_PATH).json()

    for path, operations in schema["paths"].items():
        for operation in operations.values():
            codes = set(operation["responses"])
            assert "422" not in codes, f"{path} still advertises 422"
    assert "400" in schema["paths"]["/api/weather"]["get"]["responses"]


def test_every_documented_endpoint_exists(client: TestClient) -> None:
    schema = client.get(config.API_OPENAPI_PATH).json()

    assert set(schema["paths"]) == {
        "/api/health",
        "/api/config",
        "/api/locations/default",
        "/api/locations/search",
        "/api/weather",
        "/api/chernoff",
        "/api/cache/refresh",
    }


def test_unknown_route_returns_the_shared_error_envelope(client: TestClient) -> None:
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "not_found"
    assert response.json()["path"] == "/api/does-not-exist"


def test_wrong_method_returns_the_shared_error_envelope(client: TestClient) -> None:
    response = client.post("/api/health")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"
