"""WMO 4677 weather-code mapping.

Open-Meteo reports present conditions as numeric WMO codes. This module turns
those codes into a human-readable label plus an emoji icon in a single,
reusable place. Unknown or missing codes degrade gracefully instead of raising.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class WeatherCondition:
    """A presentable description of a weather observation.

    Attributes:
        label: Human-readable description, e.g. ``"Partly cloudy"``.
        icon: Emoji rendered next to the label in the dashboard.
        is_known: ``False`` when the code was missing or not in the WMO table.
    """

    label: str
    icon: str
    is_known: bool = True


#: The official WMO 4677 code table used by Open-Meteo.
WMO_WEATHER_CODES: Final[dict[int, tuple[str, str]]] = {
    # Clear sky and clouds
    0: ("Clear sky", "☀️"),
    1: ("Mainly clear", "🌤️"),
    2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    # Fog
    45: ("Fog", "🌫️"),
    48: ("Depositing rime fog", "🌫️"),
    # Drizzle
    51: ("Light drizzle", "🌦️"),
    53: ("Moderate drizzle", "🌦️"),
    55: ("Dense drizzle", "🌧️"),
    56: ("Light freezing drizzle", "🌧️"),
    57: ("Dense freezing drizzle", "🌧️"),
    # Rain
    61: ("Slight rain", "🌦️"),
    63: ("Moderate rain", "🌧️"),
    65: ("Heavy rain", "🌧️"),
    66: ("Light freezing rain", "🌧️"),
    67: ("Heavy freezing rain", "🌧️"),
    # Snow
    71: ("Slight snow fall", "🌨️"),
    73: ("Moderate snow fall", "🌨️"),
    75: ("Heavy snow fall", "❄️"),
    77: ("Snow grains", "❄️"),
    # Rain showers
    80: ("Slight rain showers", "🌦️"),
    81: ("Moderate rain showers", "🌧️"),
    82: ("Violent rain showers", "⛈️"),
    # Snow showers
    85: ("Slight snow showers", "🌨️"),
    86: ("Heavy snow showers", "❄️"),
    # Thunderstorms
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm with slight hail", "⛈️"),
    99: ("Thunderstorm with heavy hail", "⛈️"),
}

#: Returned when a code is absent (``None`` or ``NaN``).
MISSING_CONDITION: Final[WeatherCondition] = WeatherCondition(
    label="No data available", icon="➖", is_known=False
)


def normalise_weather_code(code: object) -> int | None:
    """Coerce a raw API value into a usable WMO code.

    Accepts ints, floats (including ``numpy`` scalars) and numeric strings.
    Fractional, negative, boolean and non-numeric values return ``None``.

    Args:
        code: Raw value taken from an API payload.

    Returns:
        The integer WMO code, or ``None`` when it cannot be interpreted.
    """
    if code is None or isinstance(code, bool):
        return None

    try:
        numeric = float(code)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None

    if not math.isfinite(numeric) or numeric < 0:
        return None

    if not numeric.is_integer():
        return None

    return int(numeric)


def describe_weather_code(code: object) -> WeatherCondition:
    """Translate a WMO weather code into a label and emoji icon.

    Args:
        code: WMO 4677 code as returned by the Open-Meteo API.

    Returns:
        A :class:`WeatherCondition`. Unknown codes fall back to a generic
        description, missing codes to :data:`MISSING_CONDITION`.
    """
    normalised = normalise_weather_code(code)
    if normalised is None:
        return MISSING_CONDITION

    entry = WMO_WEATHER_CODES.get(normalised)
    if entry is None:
        return WeatherCondition(
            label=f"Unknown weather code ({normalised})", icon="❓", is_known=False
        )

    return WeatherCondition(label=entry[0], icon=entry[1])


def weather_label(code: object) -> str:
    """Return only the textual description for ``code``."""
    return describe_weather_code(code).label


def weather_icon(code: object) -> str:
    """Return only the emoji icon for ``code``."""
    return describe_weather_code(code).icon
