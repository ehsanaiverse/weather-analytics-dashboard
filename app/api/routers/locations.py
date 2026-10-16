"""Location search endpoint backed by the Open-Meteo Geocoding API."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import (
    DEFAULT_SEARCH_COUNT,
    CountQuery,
    QueryText,
    RegistryDependency,
    cached_search_locations,
)
from app.api.schemas import LocationOut, LocationSearchResponse
from app.api.transformers import build_location_search, location_to_out
from app.services.geocoding_service import Location

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get(
    "/default",
    response_model=LocationOut,
    summary="The built-in default location",
)
def get_default_location() -> LocationOut:
    """Return the location the dashboard starts on.

    The coordinates live in :data:`app.config.DEFAULT_LOCATION`, so a client
    (such as the React frontend) can render a first screen without hardcoding a
    place of its own or spending a geocoding request on a round trip.

    Returns:
        Abbottabad, Pakistan, as configured for this project.
    """
    return location_to_out(Location.from_default_config())


@router.get(
    "/search",
    response_model=LocationSearchResponse,
    responses={
        404: {"description": "No location matched the query."},
        429: {"description": "The upstream provider is rate limiting requests."},
        502: {"description": "The upstream provider could not be reached."},
        504: {"description": "The upstream provider did not respond in time."},
    },
    summary="Search for a place by name",
)
def search_locations_endpoint(
    q: QueryText,
    registry: RegistryDependency,
    count: CountQuery = DEFAULT_SEARCH_COUNT,
) -> LocationSearchResponse:
    """Resolve free-text place names into coordinates.

    Results are ordered exactly as the provider returns them (largest
    population first) and cached for an hour, because place names rarely
    change. A blank query is rejected before any request is made.

    Args:
        q: Place name, e.g. ``"London"``.
        registry: Cache registry holding the geocoding cache.
        count: Maximum number of matches to return.

    Returns:
        The matching locations plus cache metadata.

    Raises:
        LocationNotFoundError: The provider returned no usable match.
        EmptyQueryError: The query was blank.
        NetworkRequestError: The provider could not be reached.
        APITimeoutError: The provider did not respond in time.
        APIRateLimitError: The provider is rate limiting requests.
    """
    locations, cached, age = cached_search_locations(q, count, registry)
    return build_location_search(q.strip(), locations, cached=cached, cache_age_seconds=age)


__all__ = ["router", "search_locations_endpoint"]
