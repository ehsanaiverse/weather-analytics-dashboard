"""Central configuration for the Weather Analytics Dashboard.

Every tunable value (API endpoints, requested variables, cache lifetimes,
presentation palette) lives here so that the rest of the code stays free of
magic numbers. Importing this module must never perform network calls.
"""

from __future__ import annotations

from typing import Final

# --------------------------------------------------------------------------- #
# Application metadata
# --------------------------------------------------------------------------- #

APP_TITLE: Final[str] = "Real-Time Weather Analytics Dashboard"
APP_SUBTITLE: Final[str] = (
    "Current conditions and short-range forecasts from the Open-Meteo API"
)
APP_ICON: Final[str] = "🌤️"
APP_VERSION: Final[str] = "1.0.0"

# --------------------------------------------------------------------------- #
# API endpoints (Open-Meteo, free non-commercial tier, no API key required)
# --------------------------------------------------------------------------- #

FORECAST_API_URL: Final[str] = "https://api.open-meteo.com/v1/forecast"
GEOCODING_API_URL: Final[str] = "https://geocoding-api.open-meteo.com/v1/search"

#: Sent with every request so the provider can identify this client.
USER_AGENT: Final[str] = (
    f"weather-analytics-dashboard/{APP_VERSION} (educational; open-meteo.com)"
)

#: Seconds to wait for the server before giving up on a request.
REQUEST_TIMEOUT_SECONDS: Final[float] = 15.0

#: Maximum number of city matches requested from the Geocoding API.
GEOCODING_RESULT_LIMIT: Final[int] = 10

#: Valid decimal-degree bounds, used to reject nonsense coordinates.
MIN_LATITUDE: Final[float] = -90.0
MAX_LATITUDE: Final[float] = 90.0
MIN_LONGITUDE: Final[float] = -180.0
MAX_LONGITUDE: Final[float] = 180.0

#: HTTP status codes the client treats specially.
HTTP_TOO_MANY_REQUESTS: Final[int] = 429
HTTP_OK: Final[int] = 200
HTTP_MULTIPLE_CHOICES: Final[int] = 300

#: Forecast length limits enforced by the Open-Meteo Forecast API.
MIN_FORECAST_DAYS: Final[int] = 1
MAX_FORECAST_DAYS: Final[int] = 16

# --------------------------------------------------------------------------- #
# Forecast request parameters
# --------------------------------------------------------------------------- #

#: Only the variables the dashboard actually renders are requested.
CURRENT_VARIABLES: Final[tuple[str, ...]] = (
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "precipitation",
    "weather_code",
    "wind_speed_10m",
)

#: ``wind_speed_10m`` and ``apparent_temperature`` back the eyebrow and nose
#: features of the Chernoff Faces view. They are extra fields on the *same*
#: request, not additional calls.
HOURLY_VARIABLES: Final[tuple[str, ...]] = (
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation_probability",
    "wind_speed_10m",
    "apparent_temperature",
)
DAILY_VARIABLES: Final[tuple[str, ...]] = (
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_probability_max",
    "precipitation_sum",
    # Chernoff Faces: eyebrow, nose and eye features for the daily view.
    "wind_speed_10m_max",
    "apparent_temperature_max",
    "relative_humidity_2m_mean",
)

#: Number of days requested from the Forecast API (drives the daily forecast).
FORECAST_DAYS: Final[int] = 7

#: Selectable hourly forecast windows, in hours.
HOURLY_PERIOD_CHOICES: Final[tuple[int, ...]] = (12, 24, 48)
DEFAULT_HOURLY_PERIOD: Final[int] = 24

# --------------------------------------------------------------------------- #
# Caching policy (Streamlit ``st.cache_data`` TTLs, in seconds)
# --------------------------------------------------------------------------- #

#: Geocoding results change very rarely; one hour is plenty.
GEOCODING_CACHE_TTL_SECONDS: Final[int] = 60 * 60

#: Forecast responses are cached for ten minutes to stay well inside the
#: provider's fair-use limits. Cached data is clearly labelled in the UI.
WEATHER_CACHE_TTL_SECONDS: Final[int] = 60 * 10

# --------------------------------------------------------------------------- #
# HTTP API layer
# --------------------------------------------------------------------------- #
# The FastAPI application mounts every REST route under ``API_PREFIX`` so the
# Streamlit dashboard and the JSON API can coexist in one repository.

#: Mount point shared by every REST route.
API_PREFIX: Final[str] = "/api"

#: Logging level used by both entry points when nothing is configured.
DEFAULT_LOG_LEVEL: Final[str] = "INFO"

#: Interactive documentation and the OpenAPI schema live under the same prefix.
API_DOCS_PATH: Final[str] = f"{API_PREFIX}/docs"
API_OPENAPI_PATH: Final[str] = f"{API_PREFIX}/openapi.json"

#: Origins allowed by default: the Vite dev server, in both spellings. Override
#: with the ``CORS_ORIGINS`` environment variable when the frontend runs on a
#: different host or port.
DEFAULT_CORS_ORIGINS: Final[tuple[str, ...]] = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)

#: Build output of the React frontend, mounted at ``/`` when it exists.
FRONTEND_DIST_PATH: Final[str] = "frontend/dist"

#: Provider attribution surfaced in API responses, as the licence requires.
PROVIDER_NAME: Final[str] = "Open-Meteo"
PROVIDER_URL: Final[str] = "https://open-meteo.com/"
PROVIDER_LICENSE: Final[str] = "CC BY 4.0"

#: Longest location search query the API accepts.
MAX_LOCATION_QUERY_LENGTH: Final[int] = 120

# --------------------------------------------------------------------------- #
# Default location
# --------------------------------------------------------------------------- #

#: Abbottabad, Pakistan - coordinates resolved via the Open-Meteo Geocoding API.
#: They are embedded so the dashboard renders immediately on first load without
#: a blocking geocoding round-trip; a user search always replaces them with a
#: freshly resolved location.
DEFAULT_LOCATION: Final[dict[str, object]] = {
    "name": "Abbottabad",
    "country": "Pakistan",
    "admin1": "Khyber Pakhtunkhwa",
    "country_code": "PK",
    "latitude": 34.1463,
    "longitude": 73.21168,
    "timezone": "Asia/Karachi",
    "population": 275_890,
}

# --------------------------------------------------------------------------- #
# Presentation theme
# --------------------------------------------------------------------------- #

#: A restrained, light palette. Charts and metric cards share these values so
#: the dashboard reads as one consistent system.
COLOR_TEMPERATURE: Final[str] = "#E4572E"
COLOR_TEMPERATURE_MAX: Final[str] = "#E4572E"
COLOR_TEMPERATURE_MIN: Final[str] = "#4C78A8"
COLOR_HUMIDITY: Final[str] = "#3E8FB0"
COLOR_PRECIPITATION: Final[str] = "#3B7DD8"
COLOR_ACCENT: Final[str] = "#2F5D8C"
COLOR_GRID: Final[str] = "#E4E7EB"
COLOR_TEXT_MUTED: Final[str] = "#6B7280"

CHART_HEIGHT: Final[int] = 380
FONT_FAMILY: Final[str] = (
    "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
)

#: Short, honest explanation of what the numbers represent.
DATA_FRESHNESS_NOTE: Final[str] = (
    "Values come from Open-Meteo's forecast model blend. "
    "'Current' is the nearest 15-minute interval, not a live station reading, "
    "and cached responses are reused until the cache expires or you refresh."
)

ATTRIBUTION: Final[str] = (
    "Weather data by [Open-Meteo](https://open-meteo.com/) "
    "(CC BY 4.0). Geocoding by Open-Meteo."
)
