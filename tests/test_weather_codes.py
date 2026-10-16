"""Tests for the WMO weather-code mapping.

Covers the full code table plus the graceful handling of unknown, missing and
malformed values.
"""

from __future__ import annotations

import math

import pytest

from app.utils.weather_codes import (
    MISSING_CONDITION,
    WMO_WEATHER_CODES,
    describe_weather_code,
    normalise_weather_code,
    weather_icon,
    weather_label,
)

#: One representative code per condition category the dashboard must support.
REQUIRED_CATEGORIES: dict[str, int] = {
    "Clear sky": 0,
    "Mainly clear": 1,
    "Partly cloudy": 2,
    "Overcast": 3,
    "Fog": 45,
    "Depositing rime fog": 48,
    "Light drizzle": 51,
    "Moderate drizzle": 53,
    "Dense drizzle": 55,
    "Light freezing drizzle": 56,
    "Dense freezing drizzle": 57,
    "Slight rain": 61,
    "Moderate rain": 63,
    "Heavy rain": 65,
    "Light freezing rain": 66,
    "Heavy freezing rain": 67,
    "Slight snow fall": 71,
    "Moderate snow fall": 73,
    "Heavy snow fall": 75,
    "Snow grains": 77,
    "Slight rain showers": 80,
    "Moderate rain showers": 81,
    "Violent rain showers": 82,
    "Slight snow showers": 85,
    "Heavy snow showers": 86,
    "Thunderstorm": 95,
    "Thunderstorm with slight hail": 96,
    "Thunderstorm with heavy hail": 99,
}


class TestWeatherCodeTable:
    """The mapping table itself must stay complete and consistent."""

    def test_table_is_not_empty(self) -> None:
        assert len(WMO_WEATHER_CODES) >= 28

    @pytest.mark.parametrize("code", sorted(WMO_WEATHER_CODES))
    def test_every_code_has_a_label_and_icon(self, code: int) -> None:
        label, icon = WMO_WEATHER_CODES[code]
        assert isinstance(label, str) and label.strip()
        assert isinstance(icon, str) and icon.strip()

    @pytest.mark.parametrize("category,code", sorted(REQUIRED_CATEGORIES.items()))
    def test_required_condition_categories_are_covered(self, category: str, code: int) -> None:
        condition = describe_weather_code(code)
        assert condition.label == category
        assert condition.is_known is True

    def test_every_required_category_is_represented_in_the_table(self) -> None:
        """The dashboard must cover all documented condition families."""
        labels = {label for label, _ in WMO_WEATHER_CODES.values()}
        for category in REQUIRED_CATEGORIES:
            assert category in labels

        for family in ("sky", "cloud", "fog", "drizzle", "rain", "snow", "thunderstorm"):
            assert any(family in label.lower() for label in labels), family

    def test_known_codes_map_to_expected_icons(self) -> None:
        assert describe_weather_code(0).icon == "☀️"
        assert describe_weather_code(3).icon == "☁️"
        assert describe_weather_code(95).icon == "⛈️"


class TestNormaliseWeatherCode:
    """Raw API values must be coerced into usable integer codes."""

    @pytest.mark.parametrize(
        "raw,expected",
        [
            (0, 0),
            (95, 95),
            (3.0, 3),
            ("61", 61),
            (  " 2 ", 2),
            (99.0, 99),
        ],
    )
    def test_valid_values_are_normalised(self, raw: object, expected: int) -> None:
        assert normalise_weather_code(raw) == expected

    @pytest.mark.parametrize(
        "raw",
        [None, True, False, -1, -0.5, 1.5, "", "abc", float("nan"), float("inf"), [], {}],
    )
    def test_invalid_values_become_none(self, raw: object) -> None:
        assert normalise_weather_code(raw) is None

    def test_nan_is_rejected(self) -> None:
        assert normalise_weather_code(math.nan) is None


class TestDescribeWeatherCode:
    """Unknown and missing codes must degrade instead of raising."""

    def test_unknown_code_is_reported(self) -> None:
        condition = describe_weather_code(123)
        assert condition.label == "Unknown weather code (123)"
        assert condition.icon == "❓"
        assert condition.is_known is False

    @pytest.mark.parametrize("raw", [None, float("nan"), "not-a-code", True, 2.5])
    def test_missing_codes_return_the_missing_condition(self, raw: object) -> None:
        condition = describe_weather_code(raw)
        assert condition == MISSING_CONDITION
        assert condition.is_known is False
        assert condition.label == "No data available"

    def test_string_code_from_json_is_supported(self) -> None:
        assert describe_weather_code("0").label == "Clear sky"

    def test_convenience_helpers(self) -> None:
        assert weather_label(0) == "Clear sky"
        assert weather_label(None) == "No data available"
        assert weather_icon(95) == "⛈️"
        assert weather_icon(999) == "❓"

    def test_result_is_immutable(self) -> None:
        condition = describe_weather_code(0)
        with pytest.raises(AttributeError):
            condition.label = "changed"  # type: ignore[misc]
