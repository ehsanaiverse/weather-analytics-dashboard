"""Tests for the pandas data-processing layer.

Verifies current-condition extraction, hourly and daily forecast shaping,
missing-value handling and invalid-timestamp recovery. No HTTP is involved.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from app.utils.data_processing import (
    DAILY_COLUMNS,
    HOURLY_COLUMNS,
    build_current_conditions,
    build_daily_forecast,
    build_hourly_forecast,
    format_day_label,
    format_hour_label,
    format_measurement,
    parse_timestamp_series,
)
from app.utils.weather_codes import MISSING_CONDITION
from tests.conftest import daily_times, hourly_times, make_bundle

# --------------------------------------------------------------------------- #
# Current conditions
# --------------------------------------------------------------------------- #


class TestCurrentConditions:
    def test_extracts_every_measurement(self) -> None:
        conditions = build_current_conditions(make_bundle())

        assert conditions.temperature_c == pytest.approx(25.4)
        assert conditions.feels_like_c == pytest.approx(25.6)
        assert conditions.humidity_pct == pytest.approx(45)
        assert conditions.wind_speed_kmh == pytest.approx(3.9)
        assert conditions.precipitation_mm == pytest.approx(0.0)
        assert conditions.weather_code == 2
        assert conditions.condition.label == "Partly cloudy"
        assert conditions.observed_at == pd.Timestamp("2026-10-02T09:15").to_pydatetime()
        assert conditions.has_measurements is True

    def test_resolves_the_location_timezone(self) -> None:
        conditions = build_current_conditions(make_bundle())

        assert str(conditions.tzinfo) == "Asia/Karachi"

    def test_unknown_timezone_falls_back_to_the_api_offset(self) -> None:
        bundle = make_bundle()
        object.__setattr__(bundle, "timezone", "Mars/Olympus_Mons")

        conditions = build_current_conditions(bundle)

        assert conditions.tzinfo.utcoffset(None).total_seconds() == 18000

    def test_missing_measurements_become_none_not_zero(self) -> None:
        bundle = make_bundle(
            current={
                "time": "2026-10-02T09:15",
                "temperature_2m": None,
                "relative_humidity_2m": None,
                "apparent_temperature": None,
                "precipitation": None,
                "weather_code": None,
                "wind_speed_10m": None,
            }
        )

        conditions = build_current_conditions(bundle)

        assert conditions.temperature_c is None
        assert conditions.humidity_pct is None
        assert conditions.feels_like_c is None
        assert conditions.precipitation_mm is None
        assert conditions.wind_speed_kmh is None
        assert conditions.weather_code is None
        assert conditions.condition == MISSING_CONDITION
        assert conditions.has_measurements is False

    def test_nan_measurements_are_treated_as_missing(self) -> None:
        bundle = make_bundle(current={"time": "2026-10-02T09:15", "temperature_2m": float("nan")})

        conditions = build_current_conditions(bundle)

        assert conditions.temperature_c is None

    def test_single_item_lists_are_accepted(self) -> None:
        """Defensive: some providers wrap scalars in a one-element list."""
        bundle = make_bundle(
            current={"time": ["2026-10-02T09:15"], "temperature_2m": [21.5], "weather_code": [0]}
        )

        conditions = build_current_conditions(bundle)

        assert conditions.temperature_c == pytest.approx(21.5)
        assert conditions.condition.label == "Clear sky"
        assert conditions.observed_at is not None

    def test_non_numeric_measurements_are_ignored(self) -> None:
        bundle = make_bundle(current={"time": "2026-10-02T09:15", "temperature_2m": "warm"})

        conditions = build_current_conditions(bundle)

        assert conditions.temperature_c is None

    def test_invalid_timestamp_is_ignored(self) -> None:
        bundle = make_bundle(current={"time": "not-a-timestamp", "temperature_2m": 20.0})

        conditions = build_current_conditions(bundle)

        assert conditions.observed_at is None
        assert conditions.temperature_c == pytest.approx(20.0)

    def test_empty_current_block_is_handled(self) -> None:
        conditions = build_current_conditions(make_bundle(current={}))

        assert conditions.observed_at is None
        assert conditions.condition == MISSING_CONDITION
        assert conditions.has_measurements is False


# --------------------------------------------------------------------------- #
# Hourly forecast
# --------------------------------------------------------------------------- #


class TestHourlyForecast:
    def test_shape_and_column_order(self) -> None:
        frame = build_hourly_forecast(make_bundle(), 24)

        assert isinstance(frame, pd.DataFrame)
        assert list(frame.columns) == list(HOURLY_COLUMNS)
        assert len(frame) == 24
        assert frame["time"].is_monotonic_increasing

    def test_window_starts_at_the_hour_of_the_current_observation(self) -> None:
        """The API reports 09:15, so the 09:00 hour must be included."""
        frame = build_hourly_forecast(make_bundle(), 24)

        assert frame["time"].iloc[0] == pd.Timestamp("2026-10-02T09:00")
        assert frame["time"].iloc[-1] == pd.Timestamp("2026-10-03T08:00")

    @pytest.mark.parametrize("hours", [12, 24, 48])
    def test_respects_the_requested_window(self, hours: int) -> None:
        frame = build_hourly_forecast(make_bundle(), hours)

        assert len(frame) == hours
        assert frame["time"].iloc[0] == pd.Timestamp("2026-10-02T09:00")

    def test_window_never_exceeds_the_available_data(self) -> None:
        frame = build_hourly_forecast(make_bundle(hours=30), 48)

        assert len(frame) == 30

    def test_late_reference_time_only_exposes_remaining_hours(self) -> None:
        """A reference time late in the series must shrink the window."""
        bundle = make_bundle(hours=48, current={"time": "2026-10-03T20:40", "temperature_2m": 15.0})

        frame = build_hourly_forecast(bundle, 48)

        # The series runs 2026-10-02 09:00 -> 2026-10-04 08:00.
        assert frame["time"].iloc[0] == pd.Timestamp("2026-10-03T20:00")
        assert frame["time"].iloc[-1] == pd.Timestamp("2026-10-04T08:00")
        assert len(frame) == 13

    def test_values_are_carried_through(self) -> None:
        frame = build_hourly_forecast(make_bundle(), 3)

        assert frame["temperature"].iloc[0] == pytest.approx(20.0)
        assert frame["humidity"].iloc[0] == pytest.approx(40)
        assert frame["precipitation_probability"].iloc[0] == pytest.approx(0)

    def test_labels_are_human_readable(self) -> None:
        frame = build_hourly_forecast(make_bundle(), 2)

        assert frame["label"].iloc[0] == "Fri 09:00"
        assert frame["label"].iloc[1] == "Fri 10:00"

    def test_rows_with_invalid_timestamps_are_dropped(self) -> None:
        times = hourly_times(48)
        times[5] = "not-a-timestamp"
        times[20] = ""
        bundle = make_bundle(hourly={
            "time": times,
            "temperature_2m": [float(index) for index in range(48)],
            "relative_humidity_2m": [50] * 48,
            "precipitation_probability": [10] * 48,
        })

        frame = build_hourly_forecast(bundle, 24)

        # Two unusable hours are skipped, so the window reaches two hours further
        # to still contain 24 valid forecast steps.
        assert len(frame) == 24
        assert frame["time"].notna().all()
        assert frame["time"].is_monotonic_increasing

    def test_dropping_a_timestamp_keeps_the_other_values_aligned(self) -> None:
        """Regression: a bad timestamp must not shift later measurements."""
        times = hourly_times(48)
        times[5] = "not-a-timestamp"
        times[20] = ""
        bundle = make_bundle(hourly={
            "time": times,
            "temperature_2m": [float(index) for index in range(48)],
            "relative_humidity_2m": [50] * 48,
            "precipitation_probability": [10] * 48,
        })

        frame = build_hourly_forecast(bundle, 24)

        surviving = [index for index in range(26) if index not in (5, 20)]
        # Every value must still belong to the hour it was reported for.
        assert frame["temperature"].tolist() == [float(index) for index in surviving]
        assert frame["time"].dt.hour.tolist() == [(9 + index) % 24 for index in surviving]
        assert frame["time"].dt.day.tolist() == [
            2 if (9 + index) < 24 else 3 for index in surviving
        ]

    def test_missing_measurements_stay_nan_and_are_never_zero_filled(self) -> None:
        times = hourly_times(24)
        temperatures: list[float | None] = [20.0] * 24
        temperatures[3] = None
        temperatures[7] = float("nan")
        bundle = make_bundle(hourly={
            "time": times,
            "temperature_2m": temperatures,
            "relative_humidity_2m": [None] * 24,
            "precipitation_probability": [0] * 24,
        })

        frame = build_hourly_forecast(bundle, 24)

        assert frame["temperature"].isna().sum() == 2
        assert not (frame["temperature"].fillna(-1) == 0).any()
        assert frame["humidity"].isna().all()
        assert not (frame["humidity"] == 0).any()

    def test_absent_field_is_padded_with_nan(self) -> None:
        bundle = make_bundle(hourly={"time": hourly_times(24)})

        frame = build_hourly_forecast(bundle, 24)

        assert len(frame) == 24
        assert frame["temperature"].isna().all()
        assert frame["humidity"].isna().all()
        assert frame["precipitation_probability"].isna().all()

    def test_length_mismatch_is_padded_with_nan(self) -> None:
        times = hourly_times(24)
        bundle = make_bundle(hourly={
            "time": times,
            "temperature_2m": [1.0, 2.0, 3.0],  # far too short
            "relative_humidity_2m": [50] * 24,
            "precipitation_probability": [10] * 24,
        })

        frame = build_hourly_forecast(bundle, 24)

        assert len(frame) == 24
        assert frame["temperature"].iloc[:3].tolist() == [1.0, 2.0, 3.0]
        assert frame["temperature"].iloc[3:].isna().all()

    def test_non_numeric_values_are_coerced_to_nan(self) -> None:
        times = hourly_times(24)
        bundle = make_bundle(hourly={
            "time": times,
            "temperature_2m": ["warm"] * 24,
            "relative_humidity_2m": [50] * 24,
            "precipitation_probability": [10] * 24,
        })

        frame = build_hourly_forecast(bundle, 24)

        assert frame["temperature"].isna().all()

    @pytest.mark.parametrize(
        "hourly",
        [
            {},
            {"time": []},
            {"time": None},
            {"time": "2026-10-02T09:00"},
            {"time": ["bad", "worse"]},
        ],
        ids=["empty-dict", "empty-list", "none-time", "string-time", "all-invalid"],
    )
    def test_unusable_hourly_data_returns_an_empty_frame(self, hourly: dict) -> None:
        frame = build_hourly_forecast(make_bundle(hourly=hourly), 24)

        assert frame.empty
        assert list(frame.columns) == list(HOURLY_COLUMNS)

    def test_all_hours_in_the_past_yields_an_empty_frame(self) -> None:
        """A stale response must not present past hours as a forecast."""
        bundle = make_bundle(hours=24, current={"time": "2026-10-10T09:00", "temperature_2m": 12.0})

        frame = build_hourly_forecast(bundle, 24)

        assert frame.empty
        assert list(frame.columns) == list(HOURLY_COLUMNS)

    def test_zero_or_negative_window_is_clamped_to_one(self) -> None:
        assert len(build_hourly_forecast(make_bundle(), 0)) == 1
        assert len(build_hourly_forecast(make_bundle(), -5)) == 1

    def test_unsorted_input_is_sorted_before_windowing(self) -> None:
        times = hourly_times(24)
        shuffled_times = [times[index] for index in range(23, -1, -1)]
        shuffled_temps = [float(index) for index in range(23, -1, -1)]
        bundle = make_bundle(hourly={
            "time": shuffled_times,
            "temperature_2m": shuffled_temps,
            "relative_humidity_2m": [50] * 24,
            "precipitation_probability": [10] * 24,
        })

        frame = build_hourly_forecast(bundle, 3)

        assert frame["time"].tolist() == [
            pd.Timestamp("2026-10-02T09:00"),
            pd.Timestamp("2026-10-02T10:00"),
            pd.Timestamp("2026-10-02T11:00"),
        ]
        assert frame["temperature"].tolist() == [0.0, 1.0, 2.0]

    def test_index_is_reset(self) -> None:
        frame = build_hourly_forecast(make_bundle(), 24)

        assert frame.index.tolist() == list(range(24))


# --------------------------------------------------------------------------- #
# Daily forecast
# --------------------------------------------------------------------------- #


class TestDailyForecast:
    def test_shape_and_column_order(self) -> None:
        frame = build_daily_forecast(make_bundle())

        assert list(frame.columns) == list(DAILY_COLUMNS)
        assert len(frame) == 7
        assert frame["date"].is_monotonic_increasing

    def test_values_and_conditions(self) -> None:
        frame = build_daily_forecast(make_bundle())

        assert frame["temperature_max"].iloc[0] == pytest.approx(26.6)
        assert frame["temperature_min"].iloc[0] == pytest.approx(19.1)
        assert frame["precipitation_probability_max"].iloc[4] == pytest.approx(60)
        assert frame["precipitation_total"].iloc[5] == pytest.approx(8.4)
        assert frame["condition"].iloc[0] == "Clear sky"
        assert frame["icon"].iloc[0] == "☀️"
        assert frame["condition"].iloc[5] == "Thunderstorm"

    def test_labels(self) -> None:
        frame = build_daily_forecast(make_bundle())

        assert frame["label"].iloc[0] == "Fri 02 Oct"
        assert frame["label"].iloc[6] == "Thu 08 Oct"

    def test_rows_are_sorted_by_date(self) -> None:
        dates = daily_times(7)
        bundle = make_bundle(daily={
            "time": list(reversed(dates)),
            "weather_code": [0] * 7,
            "temperature_2m_max": list(range(7, 0, -1)),
            "temperature_2m_min": [10] * 7,
            "precipitation_probability_max": [0] * 7,
            "precipitation_sum": [0.0] * 7,
        })

        frame = build_daily_forecast(bundle)

        assert frame["date"].tolist() == sorted(frame["date"].tolist())
        assert frame["label"].tolist() == [
            "Fri 02 Oct", "Sat 03 Oct", "Sun 04 Oct", "Mon 05 Oct",
            "Tue 06 Oct", "Wed 07 Oct", "Thu 08 Oct",
        ]
        # Values must stay attached to their own day after sorting.
        assert frame["temperature_max"].tolist() == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]

    def test_missing_weather_code_yields_no_data_condition(self) -> None:
        bundle = make_bundle(daily={
            "time": daily_times(3),
            "weather_code": [0, None, 95],
            "temperature_2m_max": [20.0, 21.0, 22.0],
            "temperature_2m_min": [10.0, 11.0, 12.0],
            "precipitation_probability_max": [0, 0, 50],
            "precipitation_sum": [0.0, 0.0, 1.0],
        })

        frame = build_daily_forecast(bundle)

        assert frame["condition"].tolist() == ["Clear sky", "No data available", "Thunderstorm"]
        assert frame["icon"].tolist() == ["☀️", "➖", "⛈️"]

    def test_short_weather_code_list_is_padded(self) -> None:
        bundle = make_bundle(daily={
            "time": daily_times(3),
            "weather_code": [0],
            "temperature_2m_max": [20.0, 21.0, 22.0],
            "temperature_2m_min": [10.0, 11.0, 12.0],
            "precipitation_probability_max": [0, 0, 0],
            "precipitation_sum": [0.0, 0.0, 0.0],
        })

        frame = build_daily_forecast(bundle)

        assert len(frame) == 3
        assert frame["condition"].iloc[2] == "No data available"

    def test_missing_daily_fields_stay_nan(self) -> None:
        bundle = make_bundle(daily={"time": daily_times(3)})

        frame = build_daily_forecast(bundle)

        assert len(frame) == 3
        assert frame["temperature_max"].isna().all()
        assert frame["temperature_min"].isna().all()
        assert frame["precipitation_probability_max"].isna().all()
        assert frame["precipitation_total"].isna().all()
        assert frame["condition"].tolist() == ["No data available"] * 3

    def test_invalid_daily_dates_are_dropped(self) -> None:
        dates = daily_times(7)
        dates[2] = "not-a-date"
        bundle = make_bundle(daily={
            "time": dates,
            "weather_code": [0] * 7,
            "temperature_2m_max": [20.0] * 7,
            "temperature_2m_min": [10.0] * 7,
            "precipitation_probability_max": [0] * 7,
            "precipitation_sum": [0.0] * 7,
        })

        frame = build_daily_forecast(bundle)

        assert len(frame) == 6

    @pytest.mark.parametrize(
        "daily",
        [{}, {"time": []}, {"time": None}, {"time": ["nope"]}],
        ids=["empty-dict", "empty-list", "none-time", "all-invalid"],
    )
    def test_unusable_daily_data_returns_an_empty_frame(self, daily: dict) -> None:
        frame = build_daily_forecast(make_bundle(daily=daily))

        assert frame.empty
        assert list(frame.columns) == list(DAILY_COLUMNS)

    def test_index_is_reset(self) -> None:
        frame = build_daily_forecast(make_bundle())

        assert frame.index.tolist() == list(range(7))


# --------------------------------------------------------------------------- #
# Formatting helpers
# --------------------------------------------------------------------------- #


class TestFormatting:
    @pytest.mark.parametrize(
        "value,decimals,suffix,expected",
        [
            (25.44, 1, " °C", "25.4 °C"),
            (25.0, 0, " %", "25 %"),
            (0.0, 1, " mm", "0.0 mm"),
            (-3.25, 2, "", "-3.25"),
        ],
    )
    def test_format_measurement(self, value, decimals, suffix, expected) -> None:
        assert format_measurement(value, decimals, suffix) == expected

    @pytest.mark.parametrize("value", [None, float("nan"), math.nan])
    def test_format_measurement_uses_an_em_dash_for_missing_values(self, value) -> None:
        assert format_measurement(value) == "—"

    def test_format_hour_label(self) -> None:
        assert format_hour_label(pd.Timestamp("2026-10-02T09:00")) == "Fri 09:00"
        assert format_hour_label(pd.Timestamp("2026-10-05T00:00")) == "Mon 00:00"
        assert format_hour_label(None) == "—"
        assert format_hour_label(pd.NaT) == "—"

    def test_format_day_label(self) -> None:
        assert format_day_label(pd.Timestamp("2026-10-02")) == "Fri 02 Oct"
        assert format_day_label(pd.Timestamp("2026-01-05")) == "Mon 05 Jan"
        assert format_day_label(None) == "—"


class TestTimestampParsing:
    def test_parses_iso_timestamps(self) -> None:
        parsed = parse_timestamp_series(["2026-10-02T09:00", "2026-10-02T10:00"])

        assert parsed.tolist() == [
            pd.Timestamp("2026-10-02T09:00"),
            pd.Timestamp("2026-10-02T10:00"),
        ]

    def test_parses_iso_dates(self) -> None:
        parsed = parse_timestamp_series(["2026-10-02", "2026-10-03"])

        assert parsed.tolist() == [pd.Timestamp("2026-10-02"), pd.Timestamp("2026-10-03")]

    def test_falls_back_to_inference_for_unusual_formats(self) -> None:
        parsed = parse_timestamp_series(["2026-10-02T09:00", "2026/10/02 11:00"])

        assert pd.isna(parsed.iloc[0]) is False
        assert pd.isna(parsed.iloc[1]) is False

    def test_unparseable_values_become_nat(self) -> None:
        parsed = parse_timestamp_series(["2026-10-02T09:00", "nonsense", "", None])

        assert parsed.iloc[0] == pd.Timestamp("2026-10-02T09:00")
        assert parsed.isna().sum() == 3

    def test_empty_input_returns_empty_series(self) -> None:
        parsed = parse_timestamp_series([])

        assert len(parsed) == 0
        assert pd.api.types.is_datetime64_any_dtype(parsed)
