"""Geocoding service backed by the Open-Meteo Geocoding API.

Resolves free-text city names into coordinates. All HTTP handling lives in
:mod:`app.services.http_client`; this module only owns request construction,
schema validation and mapping to the :class:`Location` model.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app import config
from app.services.exceptions import EmptyQueryError, LocationNotFoundError
from app.services.http_client import get_json

LOGGER = logging.getLogger(__name__)

#: Keys the dashboard relies on. Their absence means the payload is unusable.
_REQUIRED_RESULT_KEYS = ("name", "latitude", "longitude")


@dataclass(frozen=True, slots=True)
class Location:
    """A resolved place used as the dashboard's data source.

    Attributes:
        name: City / place name.
        country: Country name, when the provider supplies one.
        admin1: First-level administrative region (state / province).
        country_code: ISO 3166-1 alpha-2 country code.
        latitude: Latitude in decimal degrees.
        longitude: Longitude in decimal degrees.
        timezone: IANA timezone name for the place.
        population: Resident population, when known.
    """

    name: str
    latitude: float
    longitude: float
    country: str | None = None
    admin1: str | None = None
    country_code: str | None = None
    timezone: str | None = None
    population: int | None = None

    @property
    def display_name(self) -> str:
        """``"Abbottabad, Khyber Pakhtunkhwa, Pakistan"`` style label."""
        parts = [self.name]
        if self.admin1:
            parts.append(self.admin1)
        if self.country:
            parts.append(self.country)
        return ", ".join(parts)

    @property
    def short_label(self) -> str:
        """``"Abbottabad, Pakistan"`` label used in the location selector."""
        if self.country:
            return f"{self.name}, {self.country}"
        return self.name

    @classmethod
    def from_default_config(cls) -> Location:
        """Build the built-in default location (Abbottabad, Pakistan)."""
        raw: Mapping[str, Any] = config.DEFAULT_LOCATION  # type: ignore[assignment]
        return cls(
            name=str(raw["name"]),
            latitude=float(raw["latitude"]),  # type: ignore[arg-type]
            longitude=float(raw["longitude"]),  # type: ignore[arg-type]
            country=_optional_str(raw.get("country")),
            admin1=_optional_str(raw.get("admin1")),
            country_code=_optional_str(raw.get("country_code")),
            timezone=_optional_str(raw.get("timezone")),
            population=_optional_int(raw.get("population")),
        )


def search_locations(
    query: str,
    *,
    count: int = config.GEOCODING_RESULT_LIMIT,
) -> list[Location]:
    """Search for places matching ``query``.

    Args:
        query: Free-text place name, e.g. ``"Abbottabad"``.
        count: Maximum number of matches to return.

    Returns:
        Matches ordered exactly as the provider returns them (largest
        population first). An empty list means no place matched.

    Raises:
        EmptyQueryError: ``query`` is blank after stripping whitespace.
        APIRateLimitError: The provider is rate limiting requests.
        APIResponseError: The payload is malformed or the request failed.
        NetworkRequestError: The provider could not be reached.
        APITimeoutError: The provider did not respond in time.
    """
    cleaned = (query or "").strip()
    if not cleaned:
        raise EmptyQueryError("Enter a city name to search for.")

    payload = get_json(
        config.GEOCODING_API_URL,
        {
            "name": cleaned,
            "count": max(1, int(count)),
            "language": "en",
            "format": "json",
        },
    )

    raw_results = payload.get("results")
    if raw_results is None:
        # A well-formed "no matches" response simply omits the ``results`` key.
        raise LocationNotFoundError(_not_found_message(cleaned))
    if not isinstance(raw_results, list):
        LOGGER.error("Geocoding 'results' was %s, expected list", type(raw_results).__name__)
        raise LocationNotFoundError("The location service returned an unexpected response.")

    locations: list[Location] = []
    for raw in raw_results:
        location = _parse_result(raw)
        if location is not None:
            locations.append(location)

    if not locations:
        LOGGER.info("No usable geocoding matches for %r", cleaned)
        raise LocationNotFoundError(_not_found_message(cleaned))

    return locations


def _not_found_message(query: str) -> str:
    """User-facing message for a query that matched no usable location."""
    return (
        f"No location found for “{query}”. Try a different spelling, "
        "or add a country name."
    )


def _parse_result(raw: Any) -> Location | None:
    """Convert one geocoding result into a :class:`Location`, or skip it."""
    if not isinstance(raw, Mapping):
        LOGGER.warning("Skipping non-object geocoding result: %r", type(raw).__name__)
        return None

    if any(key not in raw for key in _REQUIRED_RESULT_KEYS):
        LOGGER.warning("Skipping geocoding result missing required keys: %s", sorted(raw))
        return None

    try:
        latitude = float(raw["latitude"])
        longitude = float(raw["longitude"])
    except (TypeError, ValueError):
        LOGGER.warning("Skipping geocoding result with non-numeric coordinates")
        return None

    if not (
        config.MIN_LATITUDE <= latitude <= config.MAX_LATITUDE
        and config.MIN_LONGITUDE <= longitude <= config.MAX_LONGITUDE
    ):
        LOGGER.warning("Skipping geocoding result with out-of-range coordinates")
        return None

    return Location(
        name=_optional_str(raw.get("name")) or "Unknown location",
        latitude=latitude,
        longitude=longitude,
        country=_optional_str(raw.get("country")),
        admin1=_optional_str(raw.get("admin1")),
        country_code=_optional_str(raw.get("country_code")),
        timezone=_optional_str(raw.get("timezone")),
        population=_optional_int(raw.get("population")),
    )


def _optional_str(value: Any) -> str | None:
    """Return a stripped string, or ``None`` for blank / non-string values."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    """Return an int, or ``None`` when the value is missing or not numeric."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None
