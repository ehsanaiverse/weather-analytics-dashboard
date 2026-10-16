"""Settings for the HTTP API layer, resolved from the environment.

Every tunable the API needs comes from :mod:`app.config` by default and can be
overridden with an environment variable. No secret is ever read, stored or
returned by this module - the upstream provider needs no API key, and the API
surface has no authentication.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from app import config

#: Environment variables recognised by :func:`load_settings`.
ENV_CORS_ORIGINS: Final[str] = "CORS_ORIGINS"
ENV_WEATHER_CACHE_TTL: Final[str] = "WEATHER_CACHE_TTL_SECONDS"
ENV_GEOCODING_CACHE_TTL: Final[str] = "GEOCODING_CACHE_TTL_SECONDS"
ENV_LOG_LEVEL: Final[str] = "LOG_LEVEL"
ENV_SERVE_FRONTEND: Final[str] = "SERVE_FRONTEND"
ENV_FRONTEND_DIST: Final[str] = "FRONTEND_DIST"

#: How long a request waits for another in-flight call to populate the cache.
DEFAULT_SINGLE_FLIGHT_TIMEOUT: Final[float] = 30.0


@dataclass(frozen=True, slots=True)
class ApiSettings:
    """Resolved configuration for the FastAPI application.

    Attributes:
        cors_origins: Origins permitted by the CORS middleware.
        weather_cache_ttl_seconds: Lifetime of a cached forecast response.
        geocoding_cache_ttl_seconds: Lifetime of a cached geocoding result.
        log_level: Logging level name applied to the root logger.
        serve_frontend: Whether to mount the built frontend when it exists.
        frontend_dist: Directory holding the built frontend.
        single_flight_timeout: Seconds a request waits on an in-flight fetch.
    """

    cors_origins: tuple[str, ...] = config.DEFAULT_CORS_ORIGINS
    weather_cache_ttl_seconds: int = config.WEATHER_CACHE_TTL_SECONDS
    geocoding_cache_ttl_seconds: int = config.GEOCODING_CACHE_TTL_SECONDS
    log_level: str = "INFO"
    serve_frontend: bool = True
    frontend_dist: Path = Path(config.FRONTEND_DIST_PATH)
    single_flight_timeout: float = DEFAULT_SINGLE_FLIGHT_TIMEOUT


def load_settings(env: Mapping[str, str] | None = None) -> ApiSettings:
    """Build :class:`ApiSettings` from environment variables.

    Args:
        env: Environment mapping to read. Defaults to :data:`os.environ`.

    Returns:
        The resolved settings, falling back to the values in :mod:`app.config`
        whenever a variable is absent, blank or not a positive integer.
    """
    source: Mapping[str, str] = os.environ if env is None else env

    return ApiSettings(
        cors_origins=_parse_origins(source.get(ENV_CORS_ORIGINS)),
        weather_cache_ttl_seconds=_positive_int(
            source.get(ENV_WEATHER_CACHE_TTL), config.WEATHER_CACHE_TTL_SECONDS
        ),
        geocoding_cache_ttl_seconds=_positive_int(
            source.get(ENV_GEOCODING_CACHE_TTL), config.GEOCODING_CACHE_TTL_SECONDS
        ),
        log_level=(source.get(ENV_LOG_LEVEL) or config.DEFAULT_LOG_LEVEL).strip().upper(),
        serve_frontend=_parse_bool(source.get(ENV_SERVE_FRONTEND), default=True),
        frontend_dist=Path(
            (source.get(ENV_FRONTEND_DIST) or config.FRONTEND_DIST_PATH).strip()
            or config.FRONTEND_DIST_PATH
        ),
    )


def _parse_origins(raw: str | None) -> tuple[str, ...]:
    """Split a comma-separated ``CORS_ORIGINS`` value into a tuple."""
    if not raw or not raw.strip():
        return config.DEFAULT_CORS_ORIGINS
    origins = tuple(origin.strip() for origin in raw.split(",") if origin.strip())
    return origins or config.DEFAULT_CORS_ORIGINS


def _positive_int(raw: str | None, default: int) -> int:
    """Return ``raw`` as a positive integer, or ``default``."""
    if not raw or not raw.strip():
        return default
    try:
        value = int(raw.strip())
    except ValueError:
        return default
    return value if value > 0 else default


def _parse_bool(raw: str | None, *, default: bool) -> bool:
    """Interpret a boolean-ish environment value."""
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
