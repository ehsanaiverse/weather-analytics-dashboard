"""Health and static contract endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app import config
from app.api.deps import RegistryDependency, SettingsDependency
from app.api.schemas import AppConfigResponse, HealthResponse
from app.api.transformers import build_app_config, build_health

router = APIRouter(tags=["meta"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness, cache state and upstream configuration",
)
def get_health(
    registry: RegistryDependency,
    settings: SettingsDependency,
) -> HealthResponse:
    """Report service health without contacting the upstream provider.

    Args:
        registry: Process-wide cache registry.
        settings: Resolved API settings.

    Returns:
        Status, cache statistics and the public upstream endpoints. No
        credential or environment value is ever included.
    """
    return build_health(
        version=config.APP_VERSION,
        api_prefix=config.API_PREFIX,
        docs_url=config.API_DOCS_PATH,
        cache_ttl_seconds={
            name: int(registry[name].ttl_seconds) for name in registry.names()
        },
        cache_stats=registry.stats(),
        upstream={
            "forecast": config.FORECAST_API_URL,
            "geocoding": config.GEOCODING_API_URL,
        },
        frontend_served=settings.serve_frontend and settings.frontend_dist.is_dir(),
    )


@router.get(
    "/config",
    response_model=AppConfigResponse,
    summary="Static description of the API contract",
)
def get_config() -> AppConfigResponse:
    """Return the constants a client needs to build its controls.

    Returns:
        Selectable hour windows, forecast-day limits, face counts, units,
        attribution and the data-freshness wording used by the dashboard.
    """
    return build_app_config()
