"""Routers exposed by the FastAPI application.

Each module maps one URL prefix to a :class:`fastapi.APIRouter`. Endpoints are
synchronous ``def`` functions on purpose: the underlying HTTP client blocks, and
FastAPI runs sync endpoints in a thread pool.
"""

from app.api.routers import cache, health, locations, weather

__all__ = ["cache", "health", "locations", "weather"]
