"""A small, thread-safe TTL cache for the HTTP API.

The Streamlit dashboard caches through ``st.cache_data`` (see ``app.py``). The
API cannot use that, so it owns an equivalent cache here: a plain in-process
store with time-to-live entries, guarded by a lock because FastAPI runs
synchronous endpoints in a worker thread pool.

Two properties matter for a forecast API:

* **Bounded staleness.** Entries expire after a TTL (ten minutes for weather,
  one hour for geocoding) and the age of the entry that served a request is
  reported back in ``meta`` so the UI can be honest about it.
* **Single flight.** Two requests for the same uncached key do not both hit
  Open-Meteo. The first computes and stores, the others wait briefly and then
  reuse the result. Without this, a page load that fires several requests would
  multiply load on the free-tier provider.

Nothing here caches errors: a factory that raises leaves the cache untouched.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic
from typing import Final, Generic, TypeVar

from app.api.settings import ApiSettings, load_settings
from app.services.geocoding_service import Location
from app.services.weather_service import WeatherBundle

LOGGER = logging.getLogger(__name__)

T = TypeVar("T")

#: Cache names exposed by the refresh endpoint.
WEATHER_CACHE: Final[str] = "weather"
GEOCODING_CACHE: Final[str] = "geocoding"
ALL_CACHES: Final[str] = "all"
CACHE_NAMES: Final[tuple[str, ...]] = (WEATHER_CACHE, GEOCODING_CACHE)


@dataclass(frozen=True, slots=True)
class CacheEntry(Generic[T]):
    """One cached value with its creation instant and expiry deadline."""

    value: T
    stored_at: datetime
    expires_at: float

    def age_seconds(self, now: datetime | None = None) -> float:
        """Seconds elapsed since the entry was stored (never negative)."""
        moment = datetime.now(UTC) if now is None else now
        return max(0.0, (moment - self.stored_at).total_seconds())

    def is_expired(self, now: float | None = None) -> bool:
        """Whether the entry has passed its deadline."""
        return (monotonic() if now is None else now) >= self.expires_at


@dataclass(frozen=True, slots=True)
class CacheLookup(Generic[T]):
    """Result of a cache lookup: the value plus how it was obtained."""

    value: T
    hit: bool
    age_seconds: float = 0.0


class TTLCache(Generic[T]):
    """An in-process cache whose entries expire after a fixed TTL.

    Args:
        name: Human-readable cache name, used in logs and the stats endpoint.
        ttl_seconds: Entry lifetime in seconds.
        single_flight_timeout: How long a concurrent caller waits for the
            in-flight computation of the same key before computing it itself.
    """

    def __init__(
        self,
        name: str,
        ttl_seconds: float,
        *,
        single_flight_timeout: float = 30.0,
    ) -> None:
        """Create an empty cache.

        Args:
            name: Human-readable cache name.
            ttl_seconds: Entry lifetime in seconds.
            single_flight_timeout: Wait budget for a concurrent duplicate key.
        """
        self.name = name
        self.ttl_seconds = float(ttl_seconds)
        self.single_flight_timeout = float(single_flight_timeout)
        self._entries: dict[str, CacheEntry[T]] = {}
        self._inflight: dict[str, threading.Event] = {}
        self._lock = threading.RLock()

    # -- lookup / storage ---------------------------------------------------- #

    def get_or_set(self, key: str, factory: Callable[[], T]) -> CacheLookup[T]:
        """Return the cached value for ``key``, computing it when needed.

        Args:
            key: Cache key.
            factory: Zero-argument callable producing the value. Only one
                caller runs it per key at a time; its result is stored and its
                exceptions are propagated without caching anything.

        Returns:
            A :class:`CacheLookup` reporting the value and whether it was
            already cached.
        """
        with self._lock:
            entry = self._entries.get(key)
            if entry is not None and not entry.is_expired():
                return CacheLookup(entry.value, hit=True, age_seconds=entry.age_seconds())

            waiter = self._inflight.get(key)
            owner = waiter is None
            if owner:
                waiter = threading.Event()
                self._inflight[key] = waiter

        if waiter is None:  # pragma: no cover - defensive, owner always sets one
            return CacheLookup(factory(), hit=False)

        if not owner:
            waiter.wait(timeout=self.single_flight_timeout)
            with self._lock:
                entry = self._entries.get(key)
            if entry is not None and not entry.is_expired():
                return CacheLookup(entry.value, hit=True, age_seconds=entry.age_seconds())

        try:
            value = factory()
        except BaseException:
            if owner:
                self._release(key, waiter)
            raise

        now = monotonic()
        stored_at = datetime.now(UTC)
        with self._lock:
            self._entries[key] = CacheEntry(
                value=value,
                stored_at=stored_at,
                expires_at=now + self.ttl_seconds,
            )
        if owner:
            self._release(key, waiter)
        LOGGER.debug("Cache %r stored key %s", self.name, key)
        return CacheLookup(value, hit=False, age_seconds=0.0)

    def _release(self, key: str, waiter: threading.Event) -> None:
        """Wake any waiters on ``key`` and stop tracking the in-flight call."""
        with self._lock:
            self._inflight.pop(key, None)
        waiter.set()

    def get(self, key: str) -> T | None:
        """Return a live entry for ``key``, or ``None`` when absent or expired."""
        with self._lock:
            entry = self._entries.get(key)
            if entry is None or entry.is_expired():
                return None
            return entry.value

    def set(self, key: str, value: T) -> None:
        """Store ``value`` under ``key``, resetting its expiry deadline."""
        with self._lock:
            self._entries[key] = CacheEntry(
                value=value,
                stored_at=datetime.now(UTC),
                expires_at=monotonic() + self.ttl_seconds,
            )

    # -- maintenance --------------------------------------------------------- #

    def clear(self) -> int:
        """Drop every entry and return how many were removed."""
        with self._lock:
            count = len(self._entries)
            self._entries.clear()
        LOGGER.info("Cache %r cleared (%d entries)", self.name, count)
        return count

    def purge_expired(self) -> int:
        """Remove expired entries and return how many were removed."""
        now = monotonic()
        with self._lock:
            stale = [key for key, entry in self._entries.items() if entry.is_expired(now)]
            for key in stale:
                del self._entries[key]
        return len(stale)

    def stats(self) -> dict[str, int]:
        """Return entry counts for the health and refresh responses."""
        with self._lock:
            live = sum(1 for entry in self._entries.values() if not entry.is_expired())
            return {
                "entries": len(self._entries),
                "liveEntries": live,
                "inFlight": len(self._inflight),
            }


class CacheRegistry:
    """The named caches exposed by the API.

    Args:
        caches: Mapping of cache name to cache instance.
        single_flight_timeout: Wait budget shared by every cache.
    """

    def __init__(
        self,
        caches: Mapping[str, TTLCache[object]],
        *,
        single_flight_timeout: float = 30.0,
    ) -> None:
        """Store the named caches.

        Args:
            caches: Mapping of cache name to cache instance.
            single_flight_timeout: Wait budget for duplicate concurrent keys.
        """
        self._caches = dict(caches)
        self.single_flight_timeout = single_flight_timeout

    def __getitem__(self, name: str) -> TTLCache[object]:
        """Return the cache registered under ``name``."""
        return self._caches[name]

    def names(self) -> tuple[str, ...]:
        """Return every registered cache name."""
        return tuple(self._caches)

    def clear(self, scope: str = ALL_CACHES) -> dict[str, int]:
        """Clear one cache, or every cache when ``scope`` is ``"all"``.

        Args:
            scope: Cache name, or ``"all"``.

        Returns:
            Mapping of cache name to the number of entries removed.

        Raises:
            KeyError: ``scope`` is not a registered cache name.
        """
        names = self.names() if scope == ALL_CACHES else (scope,)
        return {name: self._caches[name].clear() for name in names}

    def stats(self) -> dict[str, dict[str, int]]:
        """Return the stats of every registered cache."""
        return {name: cache.stats() for name, cache in self._caches.items()}

    def purge_expired(self) -> int:
        """Remove expired entries everywhere and return the total removed."""
        return sum(cache.purge_expired() for cache in self._caches.values())


def build_registry(settings: ApiSettings | None = None) -> CacheRegistry:
    """Create the API caches described by ``settings``.

    Args:
        settings: Resolved API settings. Loaded from the environment when
            omitted.

    Returns:
        A registry holding the weather and geocoding caches with the TTLs from
        :mod:`app.config` (10 minutes and 1 hour) unless overridden.
    """
    resolved = settings or load_settings()
    timeout = resolved.single_flight_timeout
    return CacheRegistry(
        {
            WEATHER_CACHE: TTLCache[WeatherBundle](
                WEATHER_CACHE, resolved.weather_cache_ttl_seconds, single_flight_timeout=timeout
            ),
            GEOCODING_CACHE: TTLCache[list[Location]](
                GEOCODING_CACHE, resolved.geocoding_cache_ttl_seconds, single_flight_timeout=timeout
            ),
        },
        single_flight_timeout=timeout,
    )
