"""Tests for the environment-driven API settings."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from app import config
from app.api.settings import (
    DEFAULT_SINGLE_FLIGHT_TIMEOUT,
    ApiSettings,
    load_settings,
)


def test_defaults_come_from_the_project_configuration() -> None:
    settings = load_settings({})

    assert settings.cors_origins == config.DEFAULT_CORS_ORIGINS
    assert settings.weather_cache_ttl_seconds == config.WEATHER_CACHE_TTL_SECONDS
    assert settings.geocoding_cache_ttl_seconds == config.GEOCODING_CACHE_TTL_SECONDS
    assert settings.log_level == config.DEFAULT_LOG_LEVEL
    assert settings.serve_frontend is True
    assert settings.frontend_dist == Path(config.FRONTEND_DIST_PATH)
    assert settings.single_flight_timeout == DEFAULT_SINGLE_FLIGHT_TIMEOUT


def test_the_default_origins_cover_the_vite_dev_server() -> None:
    settings = load_settings({})

    assert "http://localhost:5173" in settings.cors_origins
    assert "http://127.0.0.1:5173" in settings.cors_origins


def test_cors_origins_can_be_overridden() -> None:
    settings = load_settings({"CORS_ORIGINS": "https://dash.example, http://localhost:4173"})

    assert settings.cors_origins == ("https://dash.example", "http://localhost:4173")


def test_blank_cors_origins_fall_back_to_the_defaults() -> None:
    settings = load_settings({"CORS_ORIGINS": "   "})

    assert settings.cors_origins == config.DEFAULT_CORS_ORIGINS


def test_cache_ttls_can_be_overridden() -> None:
    settings = load_settings(
        {"WEATHER_CACHE_TTL_SECONDS": "60", "GEOCODING_CACHE_TTL_SECONDS": "120"}
    )

    assert settings.weather_cache_ttl_seconds == 60
    assert settings.geocoding_cache_ttl_seconds == 120


def test_nonsensical_cache_ttls_fall_back_to_the_defaults() -> None:
    settings = load_settings(
        {"WEATHER_CACHE_TTL_SECONDS": "abc", "GEOCODING_CACHE_TTL_SECONDS": "-5"}
    )

    assert settings.weather_cache_ttl_seconds == config.WEATHER_CACHE_TTL_SECONDS
    assert settings.geocoding_cache_ttl_seconds == config.GEOCODING_CACHE_TTL_SECONDS


def test_log_level_is_normalised() -> None:
    assert load_settings({"LOG_LEVEL": " debug "}).log_level == "DEBUG"


def test_serving_the_frontend_can_be_switched_off() -> None:
    assert load_settings({"SERVE_FRONTEND": "false"}).serve_frontend is False
    assert load_settings({"SERVE_FRONTEND": "0"}).serve_frontend is False
    assert load_settings({"SERVE_FRONTEND": "yes"}).serve_frontend is True


def test_the_frontend_dist_path_can_be_overridden() -> None:
    settings = load_settings({"FRONTEND_DIST": "dist/spa"})

    assert settings.frontend_dist == Path("dist/spa")


def test_settings_are_immutable() -> None:
    settings = ApiSettings()

    with pytest.raises(FrozenInstanceError):
        settings.log_level = "DEBUG"  # type: ignore[misc]


def test_settings_never_carry_secrets() -> None:
    settings = load_settings({"WEATHER_API_KEY": "super-secret"})

    rendered = repr(settings)
    assert "super-secret" not in rendered
    assert not hasattr(settings, "weather_api_key")
