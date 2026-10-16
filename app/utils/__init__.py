"""Utility layer: weather-code mapping, timezone helpers, pandas processing.

Also holds the Chernoff Faces encoding, which both the Streamlit renderer and
the REST API use.
"""

from app.utils.chernoff import (
    DEFAULT_FACE_COUNT,
    FACE_SOURCES,
    FaceSource,
    FaceSpec,
    FaceVariable,
    build_face_rows,
    face_geometry,
    normalise,
)
from app.utils.data_processing import (
    build_current_conditions,
    build_daily_forecast,
    build_hourly_forecast,
)
from app.utils.weather_codes import describe_weather_code, weather_icon, weather_label

__all__ = [
    "DEFAULT_FACE_COUNT",
    "FACE_SOURCES",
    "FaceSource",
    "FaceSpec",
    "FaceVariable",
    "build_current_conditions",
    "build_daily_forecast",
    "build_face_rows",
    "build_hourly_forecast",
    "describe_weather_code",
    "face_geometry",
    "normalise",
    "weather_icon",
    "weather_label",
]
