"""Pandas-based reshaping of Open-Meteo payloads into analysis-ready frames.

This module is the boundary between raw API JSON and the presentation layer.
Rules followed throughout:

* Missing measurements stay missing (``NaN``) so Plotly renders real gaps.
  They are never silently replaced with ``0``, which would misrepresent the
  weather.
* Timestamps are parsed leniently; unparseable rows are dropped and logged.
* Empty results are returned as empty frames with the correct columns so the UI
  can degrade gracefully instead of raising.
"""

from __future__ import annotations

import logging
import warnings
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

import pandas as pd

from app.services.weather_service import WeatherBundle
from app.utils.time_utils import resolve_timezone
from app.utils.weather_codes import (
    WeatherCondition,
    describe_weather_code,
    normalise_weather_code,
)

LOGGER = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Output schemas (single source of truth for components and tests)
# --------------------------------------------------------------------------- #

HOURLY_COLUMNS: Final[tuple[str, ...]] = (
    "time",
    "label",
    "temperature",
    "humidity",
    "precipitation_probability",
    "wind_speed",
    "apparent_temperature",
)

DAILY_COLUMNS: Final[tuple[str, ...]] = (
    "date",
    "label",
    "condition",
    "icon",
    "temperature_max",
    "temperature_min",
    "precipitation_probability_max",
    "precipitation_total",
    "wind_speed_max",
    "apparent_temperature_max",
    "humidity_mean",
)

#: Weekday abbreviations, indexed to match ``datetime.weekday()``.
_WEEKDAYS: Final[tuple[str, ...]] = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

#: ``(API variable, frame column)`` pairs for the hourly block.
_HOURLY_FIELDS: Final[tuple[tuple[str, str], ...]] = (
    ("temperature_2m", "temperature"),
    ("relative_humidity_2m", "humidity"),
    ("precipitation_probability", "precipitation_probability"),
    ("wind_speed_10m", "wind_speed"),
    ("apparent_temperature", "apparent_temperature"),
)

#: ``(API variable, frame column)`` pairs for the daily block. The weather code
#: is kept as a raw numeric column and mapped to text afterwards.
_DAILY_FIELDS: Final[tuple[tuple[str, str], ...]] = (
    ("weather_code", "weather_code"),
    ("temperature_2m_max", "temperature_max"),
    ("temperature_2m_min", "temperature_min"),
    ("precipitation_probability_max", "precipitation_probability_max"),
    ("precipitation_sum", "precipitation_total"),
    ("wind_speed_10m_max", "wind_speed_max"),
    ("apparent_temperature_max", "apparent_temperature_max"),
    ("relative_humidity_2m_mean", "humidity_mean"),
)


# --------------------------------------------------------------------------- #
# Current conditions
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class CurrentConditions:
    """Validated current-conditions values ready for display.

    Numeric attributes are ``None`` when the provider omitted them or sent a
    value that could not be interpreted.
    """

    observed_at: datetime | None
    temperature_c: float | None
    feels_like_c: float | None
    humidity_pct: float | None
    wind_speed_kmh: float | None
    precipitation_mm: float | None
    weather_code: int | None
    condition: WeatherCondition
    timezone: str
    timezone_abbreviation: str
    utc_offset_seconds: int

    @property
    def has_measurements(self) -> bool:
        """``True`` when at least one numeric measurement is present."""
        return any(
            value is not None
            for value in (
                self.temperature_c,
                self.feels_like_c,
                self.humidity_pct,
                self.wind_speed_kmh,
                self.precipitation_mm,
            )
        )

    @property
    def tzinfo(self):
        """``tzinfo`` for the location, resolved from the IANA name."""
        return resolve_timezone(self.timezone, self.utc_offset_seconds)


def build_current_conditions(bundle: WeatherBundle) -> CurrentConditions:
    """Extract current conditions from a :class:`WeatherBundle`.

    Args:
        bundle: Validated forecast response.

    Returns:
        A :class:`CurrentConditions` value. Individual fields may be ``None``
        when the provider omitted them.
    """
    current: Mapping[str, Any] = bundle.current or {}
    raw_code = _first_value(current.get("weather_code"))

    return CurrentConditions(
        observed_at=_first_timestamp(current.get("time")),
        temperature_c=_first_number(current.get("temperature_2m")),
        feels_like_c=_first_number(current.get("apparent_temperature")),
        humidity_pct=_first_number(current.get("relative_humidity_2m")),
        wind_speed_kmh=_first_number(current.get("wind_speed_10m")),
        precipitation_mm=_first_number(current.get("precipitation")),
        weather_code=normalise_weather_code(raw_code),
        condition=describe_weather_code(raw_code),
        timezone=bundle.timezone,
        timezone_abbreviation=bundle.timezone_abbreviation,
        utc_offset_seconds=bundle.utc_offset_seconds,
    )


# --------------------------------------------------------------------------- #
# Hourly forecast
# --------------------------------------------------------------------------- #


def build_hourly_forecast(bundle: WeatherBundle, hours: int = 24) -> pd.DataFrame:
    """Build the upcoming hourly forecast window.

    The window starts at the hour containing the API's reference "current" time
    and contains at most ``hours`` consecutive rows. Using the response's own
    reference time (rather than the wall clock) keeps the window stable while a
    cached response is reused.

    Args:
        bundle: Validated forecast response.
        hours: Number of hourly rows to return.

    Returns:
        A DataFrame with :data:`HOURLY_COLUMNS`. May be empty when the provider
        returns no usable hourly data.
    """
    window = max(1, int(hours))
    hourly: Mapping[str, Any] = bundle.hourly or {}
    frame = _assemble_block(hourly, "time", _HOURLY_FIELDS, "hourly")

    if frame.empty:
        LOGGER.warning("Hourly forecast is empty for tz=%s", bundle.timezone)
        return _empty_frame(HOURLY_COLUMNS)

    start = _window_start(bundle, frame["time"].min())
    frame = frame[frame["time"] >= start]

    frame = frame.sort_values("time", kind="stable").head(window)
    frame["label"] = [format_hour_label(value) for value in frame["time"]]
    frame = frame[list(HOURLY_COLUMNS)]

    if frame.empty:
        LOGGER.warning("No hourly rows remain after filtering to the %dh window", window)

    return frame.reset_index(drop=True)


def _window_start(bundle: WeatherBundle, earliest: pd.Timestamp) -> pd.Timestamp:
    """First hour to display: the hour containing the API's current time.

    Falls back to the earliest available timestamp when the provider omitted
    the current block, so the full series is still usable.
    """
    reference = _first_timestamp((bundle.current or {}).get("time"))
    if reference is None:
        LOGGER.warning("No usable reference time; using the full hourly series")
        return earliest
    return pd.Timestamp(reference).floor("h")


# --------------------------------------------------------------------------- #
# Daily forecast
# --------------------------------------------------------------------------- #


def build_daily_forecast(bundle: WeatherBundle) -> pd.DataFrame:
    """Build the daily forecast frame from a :class:`WeatherBundle`.

    Args:
        bundle: Validated forecast response.

    Returns:
        A DataFrame with :data:`DAILY_COLUMNS`, ordered by date. May be empty
        when the provider returns no usable daily data.
    """
    daily: Mapping[str, Any] = bundle.daily or {}
    frame = _assemble_block(daily, "time", _DAILY_FIELDS, "daily", time_column="date")

    if frame.empty:
        LOGGER.warning("Daily forecast is empty for tz=%s", bundle.timezone)
        return _empty_frame(DAILY_COLUMNS)

    conditions = [describe_weather_code(code) for code in frame["weather_code"]]
    frame["condition"] = [item.label for item in conditions]
    frame["icon"] = [item.icon for item in conditions]
    frame["label"] = [format_day_label(value) for value in frame["date"]]

    frame = frame.sort_values("date", kind="stable").reset_index(drop=True)
    return frame[list(DAILY_COLUMNS)]


# --------------------------------------------------------------------------- #
# Display formatting
# --------------------------------------------------------------------------- #


def format_measurement(value: float | None, decimals: int = 1, suffix: str = "") -> str:
    """Format a measurement for display, using an em dash for missing values.

    Args:
        value: Measurement, possibly ``None`` or ``NaN``.
        decimals: Number of decimal places.
        suffix: Unit suffix appended to the formatted number.
    """
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):.{decimals}f}{suffix}"


def format_hour_label(timestamp: pd.Timestamp | datetime | None) -> str:
    """``"Mon 14:00"`` style label for an hourly axis point."""
    if timestamp is None or pd.isna(timestamp):
        return "—"
    value = pd.Timestamp(timestamp)
    return f"{_WEEKDAYS[value.weekday()]} {value:%H:%M}"


def format_day_label(timestamp: pd.Timestamp | datetime | None) -> str:
    """``"Mon 06 Oct"`` style label for a daily axis point."""
    if timestamp is None or pd.isna(timestamp):
        return "—"
    value = pd.Timestamp(timestamp)
    return f"{_WEEKDAYS[value.weekday()]} {value.day:02d} {value:%b}"


# --------------------------------------------------------------------------- #
# Low-level parsing helpers
# --------------------------------------------------------------------------- #


def _empty_frame(columns: Sequence[str]) -> pd.DataFrame:
    """Build an empty frame with the expected columns and dtypes."""
    data: dict[str, Any] = {}
    for column in columns:
        if column in {"time", "date"}:
            data[column] = pd.Series([], dtype="datetime64[ns]")
        elif column in {"label", "condition", "icon"}:
            data[column] = pd.Series([], dtype="object")
        else:
            data[column] = pd.Series([], dtype="float64")
    return pd.DataFrame(data, columns=list(columns))


def _assemble_block(
    block: Mapping[str, Any],
    time_key: str,
    fields: Sequence[tuple[str, str]],
    block_name: str,
    *,
    time_column: str = "time",
) -> pd.DataFrame:
    """Turn an API block's parallel arrays into an aligned DataFrame.

    All arrays share the ``time`` array's length. Rows whose timestamp cannot be
    parsed are dropped from the *whole* row - values and timestamps together -
    so a single bad timestamp can never shift the remaining measurements.

    Args:
        block: The raw ``hourly`` or ``daily`` mapping.
        time_key: Key holding the timestamp array, e.g. ``"time"``.
        fields: ``(API variable, frame column)`` pairs.
        block_name: Block name used in log messages.
        time_column: Output column name for the timestamps.

    Returns:
        A DataFrame with ``time_column`` plus one column per field. Empty when
        the block has no usable timestamps.
    """
    columns = [time_column, *(name for _, name in fields)]
    raw_time = block.get(time_key)
    if not isinstance(raw_time, (list, tuple)):
        LOGGER.warning("Block %r has no usable %r list", block_name, time_key)
        return pd.DataFrame(columns=columns)

    data: dict[str, Any] = {time_column: parse_timestamp_series(raw_time)}
    for api_name, column in fields:
        data[column] = _aligned_numeric_series(block.get(api_name), len(raw_time), api_name)

    frame = pd.DataFrame(data, columns=columns)
    dropped = int(frame[time_column].isna().sum())
    if dropped:
        LOGGER.warning(
            "Dropped %d row(s) with invalid timestamps from %r", dropped, block_name
        )
    return frame.dropna(subset=[time_column]).reset_index(drop=True)


def parse_timestamp_series(values: Any) -> pd.Series:
    """Parse timestamps leniently, returning ``NaT`` for anything unparseable.

    Open-Meteo documents ISO 8601 strings, which are parsed first. Any leftover
    values fall back to pandas' own inference so slightly different formats
    still work.
    """
    series = pd.Series(list(values), dtype="object")
    if series.empty:
        return pd.Series([], dtype="datetime64[ns]")

    parsed = pd.to_datetime(series, format="ISO8601", errors="coerce")
    unresolved = parsed.isna() & series.notna() & (series.astype("string").str.strip() != "")
    if bool(unresolved.any()):
        # Deliberate per-element fallback for non-ISO input, hence the local
        # suppression of pandas' "could not infer format" advice.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            parsed = parsed.fillna(pd.to_datetime(series[unresolved], errors="coerce"))
    return parsed


def _aligned_numeric_series(values: Any, length: int, field_name: str) -> pd.Series:
    """Coerce a parallel array to a float Series of exactly ``length`` rows.

    Missing, short or non-numeric entries become ``NaN`` rather than ``0``, so a
    gap in the chart always means "not reported".
    """
    if not isinstance(values, (list, tuple)):
        LOGGER.warning(
            "Field %r is missing or not a list; padding %d rows with NaN", field_name, length
        )
        series = pd.Series([None] * length, dtype="object")
    else:
        series = pd.Series(list(values), dtype="object")
        if len(series) != length:
            LOGGER.warning(
                "Field %r has %d values but %d timestamps; padding with NaN",
                field_name,
                len(series),
                length,
            )
            series = series.reindex(range(length))

    return pd.to_numeric(series, errors="coerce").astype("float64")


def _first_value(raw: Any) -> Any:
    """Return the first non-null entry of a scalar or single-item list value."""
    if isinstance(raw, (list, tuple)):
        return raw[0] if raw else None
    return raw


def _first_number(raw: Any) -> float | None:
    """Return a float measurement, or ``None`` when absent or non-numeric."""
    value = _first_value(raw)
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        LOGGER.warning("Non-numeric measurement %r; treating as missing", value)
        return None
    return None if pd.isna(number) else number


def _first_timestamp(raw: Any) -> datetime | None:
    """Return the first parseable timestamp, or ``None``."""
    value = _first_value(raw)
    if value is None:
        return None
    parsed = parse_timestamp_series([value])
    if parsed.empty or pd.isna(parsed.iloc[0]):
        LOGGER.warning("Unparseable timestamp %r; treating as missing", value)
        return None
    return parsed.iloc[0].to_pydatetime()
