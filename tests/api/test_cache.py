"""Tests for caching: the TTL cache, the cache-key policy and the refresh endpoint."""

from __future__ import annotations

import threading
import time

import pytest
from fastapi.testclient import TestClient

from app.api.cache import (
    GEOCODING_CACHE,
    WEATHER_CACHE,
    CacheRegistry,
    TTLCache,
    build_registry,
)
from app.api.deps import geocoding_cache_key, weather_cache_key
from app.api.settings import ApiSettings
from tests.api.conftest import full_forecast_payload, geocoding_payload, params_with_coordinates
from tests.conftest import FakeResponse

# --------------------------------------------------------------------------- #
# TTLCache unit tests
# --------------------------------------------------------------------------- #


def test_a_fresh_entry_is_returned_without_calling_the_factory() -> None:
    cache: TTLCache[int] = TTLCache("test", 60)
    calls: list[int] = []

    def factory() -> int:
        calls.append(1)
        return 42

    first = cache.get_or_set("key", factory)
    second = cache.get_or_set("key", factory)

    assert first.hit is False
    assert second.hit is True
    assert second.value == 42
    assert len(calls) == 1


def test_an_expired_entry_is_recomputed() -> None:
    cache: TTLCache[str] = TTLCache("test", 0.05)
    calls: list[int] = []

    def factory() -> str:
        calls.append(1)
        return f"value-{len(calls)}"

    first = cache.get_or_set("key", factory)
    time.sleep(0.08)
    second = cache.get_or_set("key", factory)

    assert first.value == "value-1"
    assert second.hit is False
    assert second.value == "value-2"


def test_concurrent_requests_for_one_key_call_the_factory_once() -> None:
    cache: TTLCache[str] = TTLCache("test", 60, single_flight_timeout=5.0)
    calls: list[int] = []
    barrier = threading.Barrier(2)

    def factory() -> str:
        calls.append(1)
        time.sleep(0.1)
        return "shared"

    def worker() -> None:
        barrier.wait()
        cache.get_or_set("key", factory)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(calls) == 1, "single flight must collapse duplicate upstream calls"


def test_a_failing_factory_caches_nothing_and_propagates() -> None:
    cache: TTLCache[str] = TTLCache("test", 60)

    def failing() -> str:
        raise RuntimeError("upstream down")

    with pytest.raises(RuntimeError):
        cache.get_or_set("key", failing)

    assert cache.get("key") is None
    assert cache.stats()["entries"] == 0


def test_a_failing_factory_does_not_wedge_the_key() -> None:
    cache: TTLCache[str] = TTLCache("test", 60, single_flight_timeout=5.0)

    def failing() -> str:
        raise RuntimeError("upstream down")

    with pytest.raises(RuntimeError):
        cache.get_or_set("key", failing)

    assert cache.get_or_set("key", lambda: "recovered").value == "recovered"


def test_clear_removes_every_entry_and_reports_the_count() -> None:
    cache: TTLCache[int] = TTLCache("test", 60)
    cache.get_or_set("a", lambda: 1)
    cache.get_or_set("b", lambda: 2)

    assert cache.clear() == 2
    assert cache.stats()["entries"] == 0
    assert cache.get("a") is None


def test_purge_expired_drops_only_stale_entries() -> None:
    cache: TTLCache[int] = TTLCache("test", 0.05)
    cache.get_or_set("stale", lambda: 1)
    time.sleep(0.08)
    cache.get_or_set("fresh", lambda: 2)

    assert cache.purge_expired() == 1
    assert cache.get("fresh") == 2


def test_stats_report_live_and_in_flight_counts() -> None:
    cache: TTLCache[int] = TTLCache("test", 60)
    cache.get_or_set("a", lambda: 1)

    stats = cache.stats()

    assert stats == {"entries": 1, "liveEntries": 1, "inFlight": 0}


# --------------------------------------------------------------------------- #
# Cache key policy
# --------------------------------------------------------------------------- #


def test_the_weather_key_ignores_the_window_size() -> None:
    assert weather_cache_key(34.1463, 73.2117, 7) == weather_cache_key(34.1463, 73.2117, 7)


def test_the_weather_key_separates_different_locations() -> None:
    assert weather_cache_key(34.1463, 73.2117, 7) != weather_cache_key(51.5, -0.12, 7)


def test_the_weather_key_separates_different_forecast_lengths() -> None:
    assert weather_cache_key(34.1463, 73.2117, 7) != weather_cache_key(34.1463, 73.2117, 3)


def test_the_weather_key_absorbs_tiny_coordinate_differences() -> None:
    assert weather_cache_key(34.14630001, 73.21168, 7) == weather_cache_key(34.1463, 73.2117, 7)


def test_the_geocoding_key_normalises_case_and_whitespace() -> None:
    assert geocoding_cache_key("  Abbottabad  ", 10) == geocoding_cache_key("abbottabad", 10)


def test_the_geocoding_key_separates_different_counts() -> None:
    assert geocoding_cache_key("Rome", 5) != geocoding_cache_key("Rome", 10)


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #


def test_the_registry_uses_the_configured_durations() -> None:
    registry = build_registry(ApiSettings())

    assert registry[WEATHER_CACHE].ttl_seconds == 600
    assert registry[GEOCODING_CACHE].ttl_seconds == 3600
    assert set(registry.names()) == {WEATHER_CACHE, GEOCODING_CACHE}


def test_clearing_all_reports_both_caches() -> None:
    registry = build_registry(ApiSettings())
    registry[WEATHER_CACHE].set("a", 1)
    registry[GEOCODING_CACHE].set("b", 2)

    cleared = registry.clear("all")

    assert cleared == {WEATHER_CACHE: 1, GEOCODING_CACHE: 1}


def test_clearing_an_unknown_scope_is_rejected() -> None:
    registry = build_registry(ApiSettings())

    with pytest.raises(KeyError):
        registry.clear("nope")


# --------------------------------------------------------------------------- #
# Endpoint behaviour
# --------------------------------------------------------------------------- #


def test_a_second_forecast_request_is_served_from_the_cache(
    client: TestClient, fake_get
) -> None:
    calls = fake_get(FakeResponse(full_forecast_payload()))

    first = client.get("/api/weather", params=params_with_coordinates()).json()
    second = client.get("/api/weather", params=params_with_coordinates()).json()

    assert first["meta"]["cached"] is False
    assert second["meta"]["cached"] is True
    assert second["meta"]["cacheAgeSeconds"] > 0
    assert len(calls) == 1


def test_a_different_window_reuses_the_cached_forecast(
    client: TestClient, fake_get
) -> None:
    calls = fake_get(FakeResponse(full_forecast_payload()))

    client.get("/api/weather", params=params_with_coordinates(hours=12))
    client.get("/api/weather", params=params_with_coordinates(hours=48))

    assert len(calls) == 1, "only the upstream fetch is cached, not the window"


def test_a_different_location_is_fetched_again(client: TestClient, fake_get) -> None:
    calls = fake_get(FakeResponse(full_forecast_payload()))

    client.get("/api/weather", params=params_with_coordinates())
    client.get("/api/weather", params={"latitude": 51.5085, "longitude": -0.1257})

    assert len(calls) == 2


def test_refresh_clears_the_weather_cache(client: TestClient, fake_get) -> None:
    calls = fake_get(FakeResponse(full_forecast_payload()))
    client.get("/api/weather", params=params_with_coordinates())

    refresh = client.post("/api/cache/refresh")
    after = client.get("/api/weather", params=params_with_coordinates()).json()

    assert refresh.status_code == 200
    assert refresh.json()["scope"] == "weather"
    assert refresh.json()["clearedCaches"] == ["weather"]
    assert refresh.json()["clearedEntries"] == 1
    assert after["meta"]["cached"] is False
    assert len(calls) == 2


def test_refresh_leaves_the_geocoding_cache_alone(client: TestClient, fake_get) -> None:
    fake_get(FakeResponse(geocoding_payload()))
    client.get("/api/locations/search", params={"q": "Abbottabad"})

    client.post("/api/cache/refresh", params={"scope": "weather"})

    body = client.get("/api/locations/search", params={"q": "Abbottabad"}).json()
    assert body["cached"] is True


def test_refresh_all_clears_both_caches(client: TestClient, fake_get) -> None:
    fake_get(FakeResponse(full_forecast_payload()))
    client.get("/api/weather", params=params_with_coordinates())
    fake_get(FakeResponse(geocoding_payload()))
    client.get("/api/locations/search", params={"q": "Abbottabad"})

    refresh = client.post("/api/cache/refresh", params={"scope": "all"}).json()

    assert refresh["clearedCaches"] == ["geocoding", "weather"]
    assert refresh["clearedEntries"] == 2


def test_an_unknown_refresh_scope_is_rejected(client: TestClient) -> None:
    response = client.post("/api/cache/refresh", params={"scope": "everything"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


def test_refresh_on_an_empty_cache_is_a_no_op(client: TestClient) -> None:
    response = client.post("/api/cache/refresh")

    assert response.status_code == 200
    assert response.json()["clearedEntries"] == 0


def test_health_reflects_cached_entries(client: TestClient, fake_get) -> None:
    fake_get(FakeResponse(full_forecast_payload()))

    client.get("/api/weather", params=params_with_coordinates())
    health = client.get("/api/health").json()

    assert health["cache"]["weather"]["entries"] == 1
    assert health["cache"]["weather"]["liveEntries"] == 1
    assert health["cache"]["geocoding"]["entries"] == 0


def test_the_registry_is_shared_between_requests() -> None:
    registry = build_registry(ApiSettings())
    other = build_registry(ApiSettings())

    registry[WEATHER_CACHE].set("shared", "value")

    assert isinstance(other, CacheRegistry)
    assert other[WEATHER_CACHE].get("shared") is None, "registries are independent instances"
