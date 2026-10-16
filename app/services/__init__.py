"""Service layer: API clients, shared HTTP transport and domain models."""

from app.services.exceptions import (
    APIRateLimitError,
    APIResponseError,
    APITimeoutError,
    DataProcessingError,
    EmptyQueryError,
    LocationNotFoundError,
    NetworkRequestError,
    WeatherDashboardError,
)

__all__ = [
    "APIRateLimitError",
    "APIResponseError",
    "APITimeoutError",
    "DataProcessingError",
    "EmptyQueryError",
    "LocationNotFoundError",
    "NetworkRequestError",
    "WeatherDashboardError",
]
