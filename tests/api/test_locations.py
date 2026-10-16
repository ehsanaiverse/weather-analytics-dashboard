"""Tests for the location search endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import config
from tests.api.conftest import geocoding_payload
from tests.conftest import FakeResponse


def test_default_location_needs_no_upstream_request(client: TestClient, fake_get) -> None:
    calls = fake_get(FakeResponse(geocoding_payload()))

    response = client.get("/api/locations/default")

    assert response.status_code == 200
    body = response.json()
    assert body["displayName"] == config.DEFAULT_LOCATION["name"] + (
        f", {config.DEFAULT_LOCATION['admin1']}, {config.DEFAULT_LOCATION['country']}"
    )
    assert body["latitude"] == pytest.approx(config.DEFAULT_LOCATION["latitude"])
    assert body["longitude"] == pytest.approx(config.DEFAULT_LOCATION["longitude"])
    assert body["timezone"] == "Asia/Karachi"
    assert calls == [], "the default location is embedded, not geocoded"


def test_search_returns_every_match_in_provider_order(client: TestClient, fake_get) -> None:
    fake_get(FakeResponse(geocoding_payload()))

    response = client.get("/api/locations/search", params={"q": "Abbottabad"})

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "Abbottabad"
    assert body["count"] == 2
    assert [item["name"] for item in body["results"]] == ["Abbottabad", "Abbottabad Lines"]
    assert body["results"][0]["displayName"] == "Abbottabad, Khyber Pakhtunkhwa, Pakistan"
    assert body["results"][0]["shortLabel"] == "Abbottabad, Pakistan"
    assert body["results"][0]["timezone"] == "Asia/Karachi"


def test_search_exposes_the_coordinates_the_frontend_requests_with(
    client: TestClient, fake_get
) -> None:
    fake_get(FakeResponse(geocoding_payload()))

    results = client.get("/api/locations/search", params={"q": "Abbottabad"}).json()["results"]

    assert results[0]["latitude"] == pytest.approx(34.1463)
    assert results[0]["longitude"] == pytest.approx(73.21168)
    assert results[0]["population"] == 275_890


def test_search_sends_the_expected_upstream_request(client: TestClient, fake_get) -> None:
    calls = fake_get(FakeResponse(geocoding_payload()))

    client.get("/api/locations/search", params={"q": "Abbottabad", "count": 3})

    assert calls[0]["params"]["name"] == "Abbottabad"
    assert calls[0]["params"]["count"] == 3
    assert calls[0]["params"]["language"] == "en"


def test_search_result_is_cached_for_a_second_request(client: TestClient, fake_get) -> None:
    calls = fake_get(FakeResponse(geocoding_payload()))

    first = client.get("/api/locations/search", params={"q": "Abbottabad"}).json()
    second = client.get("/api/locations/search", params={"q": "Abbottabad"}).json()

    assert first["cached"] is False
    assert second["cached"] is True
    assert second["cacheAgeSeconds"] >= 0
    assert len(calls) == 1, "the second identical search must not hit the network"


def test_cache_key_ignores_case_and_extra_whitespace(client: TestClient, fake_get) -> None:
    calls = fake_get(FakeResponse(geocoding_payload()))

    client.get("/api/locations/search", params={"q": "Abbottabad"})
    client.get("/api/locations/search", params={"q": "  abbottabad  "})

    assert len(calls) == 1


def test_different_queries_are_cached_separately(client: TestClient, fake_get) -> None:
    calls = fake_get(FakeResponse(geocoding_payload()))

    client.get("/api/locations/search", params={"q": "Abbottabad"})
    client.get("/api/locations/search", params={"q": "Islamabad"})

    assert len(calls) == 2


def test_blank_query_is_rejected_before_any_request(client: TestClient, fake_get) -> None:
    calls = fake_get(FakeResponse(geocoding_payload()))

    response = client.get("/api/locations/search", params={"q": ""})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"
    assert calls == []


def test_missing_query_parameter_is_rejected(client: TestClient, fake_get) -> None:
    calls = fake_get(FakeResponse(geocoding_payload()))

    response = client.get("/api/locations/search")

    assert response.status_code == 400
    assert calls == []


def test_overlong_query_is_rejected(client: TestClient, fake_get) -> None:
    calls = fake_get(FakeResponse(geocoding_payload()))

    response = client.get("/api/locations/search", params={"q": "a" * 500})

    assert response.status_code == 400
    assert calls == []


def test_count_outside_the_allowed_range_is_rejected(client: TestClient, fake_get) -> None:
    calls = fake_get(FakeResponse(geocoding_payload()))

    assert client.get("/api/locations/search", params={"q": "Rome", "count": 0}).status_code == 400
    assert client.get("/api/locations/search", params={"q": "Rome", "count": 99}).status_code == 400
    assert calls == []


def test_no_match_returns_404_with_a_friendly_message(client: TestClient, fake_get) -> None:
    fake_get(FakeResponse({"generationtime_ms": 0.2}))

    response = client.get("/api/locations/search", params={"q": "zzzznotaplace"})

    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "location_not_found"
    assert "zzzznotaplace" in error["message"]


def test_results_without_required_keys_are_skipped(client: TestClient, fake_get) -> None:
    fake_get(
        FakeResponse(
            geocoding_payload(
                [
                    {"name": "Broken", "latitude": "not-a-number", "longitude": 1.0},
                    {
                        "name": "Usable",
                        "latitude": 10.0,
                        "longitude": 20.0,
                        "country": "Nowhere",
                    },
                ]
            )
        )
    )

    body = client.get("/api/locations/search", params={"q": "somewhere"}).json()

    assert [item["name"] for item in body["results"]] == ["Usable"]


def test_network_failure_maps_to_502(client: TestClient, fake_get) -> None:
    import requests  # noqa: PLC0415 - imported here to build the transport error

    fake_get(error=requests.ConnectionError("no route to host"))

    response = client.get("/api/locations/search", params={"q": "Abbottabad"})

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "upstream_unreachable"


def test_timeout_maps_to_504(client: TestClient, fake_get) -> None:
    import requests  # noqa: PLC0415 - imported here to build the transport error

    fake_get(error=requests.Timeout("too slow"))

    response = client.get("/api/locations/search", params={"q": "Abbottabad"})

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "upstream_timeout"


def test_rate_limit_maps_to_429_with_retry_after(client: TestClient, fake_get) -> None:
    fake_get(FakeResponse({}, status_code=429))

    response = client.get("/api/locations/search", params={"q": "Abbottabad"})

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "upstream_rate_limited"
    assert response.headers["Retry-After"] == "60"


def test_upstream_server_error_maps_to_502(client: TestClient, fake_get) -> None:
    fake_get(FakeResponse({}, status_code=500, text="boom"))

    response = client.get("/api/locations/search", params={"q": "Abbottabad"})

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "upstream_bad_response"


def test_malformed_json_maps_to_502(client: TestClient, fake_get) -> None:
    fake_get(FakeResponse(invalid_json=True, text="<html>nope</html>"))

    response = client.get("/api/locations/search", params={"q": "Abbottabad"})

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "upstream_bad_response"


def test_failed_search_is_not_cached(client: TestClient, fake_get) -> None:
    import requests  # noqa: PLC0415 - imported here to build the transport error

    calls = fake_get(error=requests.ConnectionError("down"))

    client.get("/api/locations/search", params={"q": "Abbottabad"})
    client.get("/api/locations/search", params={"q": "Abbottabad"})

    assert len(calls) == 2, "a failure must not be cached as a result"


def test_cors_allows_the_vite_dev_server(client: TestClient) -> None:
    response = client.get("/api/health", headers={"Origin": "http://localhost:5173"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_preflight_for_the_vite_dev_server(client: TestClient) -> None:
    response = client.options(
        "/api/weather",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "GET" in response.headers["access-control-allow-methods"]


def test_cors_rejects_an_unknown_origin(client: TestClient) -> None:
    response = client.get("/api/health", headers={"Origin": "https://evil.example"})

    assert "access-control-allow-origin" not in response.headers
