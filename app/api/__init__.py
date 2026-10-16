"""HTTP API layer.

The modules in this package turn the existing service and processing layers
into a REST interface for the React frontend:

``app.api.settings``
    Environment-driven configuration.
``app.api.cache``
    Thread-safe TTL caches with single-flight behaviour.
``app.api.schemas``
    Pydantic response models (camelCase on the wire).
``app.api.errors``
    One error envelope and the exception-to-status mapping.
``app.api.deps``
    Query validation, cached service access and data preparation.
``app.api.transformers``
    Service/pandas objects to API models, including ``NaN`` to ``null``.
``app.api.routers``
    The endpoints themselves.
"""

__all__ = [
    "cache",
    "deps",
    "errors",
    "routers",
    "schemas",
    "settings",
    "transformers",
]
