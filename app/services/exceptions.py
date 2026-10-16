"""Exception hierarchy shared by the service and processing layers.

The dashboard catches :class:`WeatherDashboardError` at the presentation
boundary and shows a short, friendly message. Detailed diagnostics are logged
instead of being dumped into the UI, which keeps stack traces out of the way of
end users while remaining available during development.
"""

from __future__ import annotations


class WeatherDashboardError(Exception):
    """Base class for every expected, user-facing failure."""


# --------------------------------------------------------------------------- #
# Input / lookup errors
# --------------------------------------------------------------------------- #


class EmptyQueryError(WeatherDashboardError):
    """Raised when a location search is submitted with a blank query."""


class LocationNotFoundError(WeatherDashboardError):
    """Raised when the Geocoding API returns no match for a query."""


# --------------------------------------------------------------------------- #
# Transport errors
# --------------------------------------------------------------------------- #


class NetworkRequestError(WeatherDashboardError):
    """Raised when the request could not be completed (DNS, TLS, offline)."""


class APITimeoutError(NetworkRequestError):
    """Raised when the provider did not answer within the timeout window."""


# --------------------------------------------------------------------------- #
# Response errors
# --------------------------------------------------------------------------- #


class APIRateLimitError(WeatherDashboardError):
    """Raised on HTTP 429 when the provider asks the client to slow down."""


class APIResponseError(WeatherDashboardError):
    """Raised for HTTP failures, malformed payloads or unexpected schemas."""


# --------------------------------------------------------------------------- #
# Processing errors
# --------------------------------------------------------------------------- #


class DataProcessingError(WeatherDashboardError):
    """Raised when a payload is well-formed but cannot be processed."""
