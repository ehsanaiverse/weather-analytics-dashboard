"""FastAPI application factory for the Weather Analytics Dashboard.

Run it with::

    uvicorn app.main:app --reload --port 8000

The application is a thin HTTP shell around the existing Python layer: it
reuses :mod:`app.services` for HTTP access to Open-Meteo, :mod:`app.utils` for
validation, timezone handling, WMO codes and pandas reshaping, and
:mod:`app.utils.chernoff` for the Chernoff encoding. The Streamlit dashboard in
``app.py`` keeps working against exactly the same services.

Routes live under :data:`app.config.API_PREFIX` (``/api``):

============================  ==========================================
Endpoint                      Purpose
============================  ==========================================
``GET /api/health``           Liveness, cache state, upstream config
``GET /api/config``           Static contract description
``GET /api/locations/search`` City search (Geocoding API, 1 h cache)
``GET /api/weather``          Current + hourly + daily + Chernoff faces
``GET /api/chernoff``         Chernoff faces for one source only
``POST /api/cache/refresh``   Drop cached data (the "refresh" button)
============================  ==========================================
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles

from app import config
from app.api.deps import get_registry, get_settings
from app.api.errors import REQUEST_ID_HEADER, register_exception_handlers
from app.api.routers import cache as cache_router
from app.api.routers import health as health_router
from app.api.routers import locations as locations_router
from app.api.routers import weather as weather_router
from app.api.settings import ApiSettings

LOGGER = logging.getLogger("app.main")

DESCRIPTION = (
    "REST access to the Real-Time Weather Analytics Dashboard. Data is provided "
    f"by {config.PROVIDER_NAME} ({config.PROVIDER_LICENSE}) and needs no API key. "
    "Current conditions are the nearest 15-minute interval of a forecast model "
    "blend, not a live station reading."
)


def configure_logging(level: str) -> None:
    """Configure root logging for the API process.

    Uses :func:`logging.basicConfig`, which is a no-op when the root logger
    already has handlers, so it never clobbers a host application's logging.

    Args:
        level: Logging level name, e.g. ``"INFO"`` or ``"DEBUG"``.
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Log startup and drop expired cache entries on shutdown.

    Args:
        application: The FastAPI application being started.

    Yields:
        Control back to the server while the application runs.
    """
    registry = get_registry()
    settings: ApiSettings = application.state.settings
    LOGGER.info(
        "API ready: weather cache %ds, geocoding cache %ds, CORS %s",
        settings.weather_cache_ttl_seconds,
        settings.geocoding_cache_ttl_seconds,
        ", ".join(settings.cors_origins),
    )
    try:
        yield
    finally:
        removed = registry.purge_expired()
        if removed:
            LOGGER.info("Purged %d expired cache entries on shutdown", removed)


def create_application(settings: ApiSettings | None = None) -> FastAPI:
    """Build the FastAPI application.

    Args:
        settings: Resolved settings. Loaded from the environment when omitted,
            which is what the command-line server does.

    Returns:
        A configured application with CORS, correlation ids, the shared error
        envelope, every router and - when the built frontend exists - a static
        mount for it.
    """
    resolved = settings or get_settings()
    configure_logging(resolved.log_level)

    application = FastAPI(
        title=f"{config.APP_TITLE} API",
        description=DESCRIPTION,
        version=config.APP_VERSION,
        lifespan=lifespan,
        docs_url=config.API_DOCS_PATH,
        redoc_url=None,
        openapi_url=config.API_OPENAPI_PATH,
    )
    application.state.settings = resolved

    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER],
        max_age=600,
    )
    application.middleware("http")(request_id_middleware)

    register_exception_handlers(application)
    application.openapi = lambda: build_openapi_schema(application)  # type: ignore[method-assign]

    for router in (
        health_router.router,
        locations_router.router,
        weather_router.router,
        cache_router.router,
    ):
        application.include_router(router, prefix=config.API_PREFIX)

    mount_frontend(application, resolved)
    return application


def build_openapi_schema(application: FastAPI) -> dict[str, Any]:
    """Build the OpenAPI schema, documenting the real validation status.

    FastAPI advertises HTTP 422 for query-parameter validation errors by
    default. This API answers 400 with the shared error envelope instead, so
    the generated 422 entry is removed to keep the documentation truthful for
    the frontend developer.

    Args:
        application: The application whose routes should be described.

    Returns:
        The OpenAPI schema as a plain dictionary.
    """
    if application.openapi_schema:
        return application.openapi_schema

    schema = get_openapi(
        title=application.title,
        version=application.version,
        description=application.description,
        routes=application.routes,
    )
    for operations in schema.get("paths", {}).values():
        for operation in operations.values():
            operation.get("responses", {}).pop("422", None)

    application.openapi_schema = schema
    return schema


async def request_id_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Attach a correlation id to every request and echo it in the response.

    Args:
        request: The incoming request.
        call_next: The next handler in the chain.

    Returns:
        The response, with an ``X-Request-ID`` header added.
    """
    incoming = request.headers.get(REQUEST_ID_HEADER, "").strip()
    request_id = incoming or uuid.uuid4().hex[:12]
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers[REQUEST_ID_HEADER] = request_id
    return response


def mount_frontend(application: FastAPI, settings: ApiSettings) -> bool:
    """Serve the built React frontend when it is present.

    The mount is skipped silently while the frontend has not been built yet, so
    the API is usable on its own.

    Args:
        application: The application to mount the static files on.
        settings: Resolved settings holding the dist directory.

    Returns:
        Whether the static mount was installed.
    """
    if not settings.serve_frontend:
        return False
    dist = Path(settings.frontend_dist)
    if not dist.is_dir():
        LOGGER.info("No built frontend at %s; serving the API only", dist)
        return False

    application.mount(
        "/",
        StaticFiles(directory=str(dist), html=True),
        name="frontend",
    )
    LOGGER.info("Serving built frontend from %s", dist)
    return True


#: Module-level application for ``uvicorn app.main:app``.
app = create_application()


if __name__ == "__main__":  # pragma: no cover - manual entry point
    import uvicorn  # noqa: PLC0415 - imported only when run as a script

    configure_logging(config.DEFAULT_LOG_LEVEL)
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
