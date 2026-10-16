"""Real-Time Weather Analytics Dashboard.

A Streamlit dashboard for current conditions and short-range forecasts from the
Open-Meteo API. The package is layered so that each concern stays testable:

``app.config``
    Endpoints, requested variables, cache lifetimes and theme values.
``app.services``
    All HTTP access and API payload validation.
``app.utils``
    Weather-code mapping, timezone helpers and pandas reshaping.
``app.components``
    Streamlit presentation only - no requests, no business logic.
"""

__version__ = "1.0.0"
