"""Cache administration endpoint.

The Streamlit dashboard has a *Refresh weather data* button that clears the
forecast cache and refetches. This endpoint is the equivalent for API clients:
it drops cached entries so the next request goes back to the provider.

Clearing the cache does not guarantee newer numbers - Open-Meteo may not have
published a newer model run - which is why every response also reports the
retrieval timestamp.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.api.cache import ALL_CACHES, GEOCODING_CACHE, WEATHER_CACHE
from app.api.deps import RegistryDependency
from app.api.schemas import CacheRefreshResponse

router = APIRouter(prefix="/cache", tags=["cache"])

Scope = Annotated[
    Literal["weather", "geocoding", "all"],
    Query(description="Which cache to clear."),
]


@router.post(
    "/refresh",
    response_model=CacheRefreshResponse,
    summary="Drop cached entries so the next request refetches",
)
def refresh_cache(
    registry: RegistryDependency,
    scope: Scope = WEATHER_CACHE,
) -> CacheRefreshResponse:
    """Clear one cache, or both.

    Args:
        registry: Cache registry to clear.
        scope: ``"weather"`` (default), ``"geocoding"`` or ``"all"``.

    Returns:
        The caches that were cleared and how many entries were removed.
    """
    cleared = registry.clear(scope)
    return CacheRefreshResponse(
        scope=scope,
        cleared_caches=sorted(cleared),
        cleared_entries=sum(cleared.values()),
        timestamp=datetime.now(UTC),
    )


__all__ = ["ALL_CACHES", "GEOCODING_CACHE", "Scope", "WEATHER_CACHE", "refresh_cache", "router"]
