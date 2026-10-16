"""Tests for the Chernoff Faces visualisation.

Covers value normalisation, the mapping from weather variables to facial
geometry, geometry bounds, record preparation and figure construction. The
figures are built from synthetic DataFrames, so no HTTP or Streamlit runtime is
involved.
"""

from __future__ import annotations

import dataclasses
import itertools
import math

import pandas as pd
import pytest

from app.components import chernoff as cf

#: The five features every source must encode, keyed by ``FaceSpec`` attribute.
ALL_FEATURES: tuple[str, ...] = (
    "temperature",
    "humidity",
    "wind",
    "precipitation",
    "apparent_temperature",
)

#: Number of shapes drawn per face: head, 2 eyes, 2 brows, nose, mouth.
SHAPES_PER_FACE = 7


# --------------------------------------------------------------------------- #
# Fixtures / builders
# --------------------------------------------------------------------------- #


def make_hourly_frame(records: int = 6) -> pd.DataFrame:
    """Build an hourly DataFrame shaped like the processing layer's output."""
    return pd.DataFrame(
        {
            "time": pd.date_range("2026-10-02 09:00", periods=records, freq="h"),
            "label": [f"Fri {9 + index:02d}:00" for index in range(records)],
            "temperature": [20.0 + index for index in range(records)],
            "humidity": [40 + index * 5 for index in range(records)],
            "precipitation_probability": [index * 10 for index in range(records)],
            "wind_speed": [5.0 + index for index in range(records)],
            "apparent_temperature": [18.0 + index * 2 for index in range(records)],
        }
    )


def make_daily_frame(records: int = 7) -> pd.DataFrame:
    """Build a daily DataFrame shaped like the processing layer's output."""
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-10-02", periods=records, freq="D"),
            "label": [f"Day {index + 1}" for index in range(records)],
            "condition": ["Clear sky"] * records,
            "icon": ["☀️"] * records,
            "temperature_max": [26.0 + index for index in range(records)],
            "temperature_min": [19.0 + index for index in range(records)],
            "precipitation_probability_max": [index * 12 for index in range(records)],
            "precipitation_total": [0.0] * records,
            "wind_speed_max": [9.0 + index for index in range(records)],
            "apparent_temperature_max": [25.0 + index for index in range(records)],
            "humidity_mean": [45 + index * 4 for index in range(records)],
        }
    )


def make_spec(**overrides: float) -> cf.FaceSpec:
    """Build a FaceSpec with neutral values except the named ones."""
    values = dict.fromkeys(ALL_FEATURES, cf.NEUTRAL)
    values.update(overrides)
    return cf.FaceSpec(**values)  # type: ignore[arg-type]


def brow_angle_degrees(geometry: cf.FaceGeometry) -> float:
    """Recover the encoded brow angle from the drawn coordinates."""
    return math.degrees(math.atan2(geometry.brow_rise, geometry.brow_half_width))


# --------------------------------------------------------------------------- #
# Value coercion
# --------------------------------------------------------------------------- #


class TestCoerceFloat:
    @pytest.mark.parametrize(
        "raw,expected",
        [(1, 1.0), (1.5, 1.5), ("2.5", 2.5), (-3, -3.0), (0, 0.0)],
    )
    def test_valid_values_convert(self, raw: object, expected: float) -> None:
        assert cf.coerce_float(raw) == pytest.approx(expected)

    @pytest.mark.parametrize(
        "raw", [None, True, False, "", "abc", "nan", math.nan, math.inf, -math.inf, [], {}]
    )
    def test_unusable_values_become_nan(self, raw: object) -> None:
        assert math.isnan(cf.coerce_float(raw))

    def test_numpy_scalars_are_supported(self) -> None:
        assert cf.coerce_float(pd.Series([7.5]).iloc[0]) == pytest.approx(7.5)


# --------------------------------------------------------------------------- #
# Normalisation
# --------------------------------------------------------------------------- #


class TestNormalise:
    def test_min_max_maps_to_zero_and_one(self) -> None:
        assert cf.normalise([10.0, 20.0, 30.0]) == [0.0, 0.5, 1.0]

    def test_output_is_always_within_unit_range(self) -> None:
        result = cf.normalise([-40.0, 0.0, 12.5, 99.9])

        assert len(result) == 4
        assert all(0.0 <= value <= 1.0 for value in result)

    def test_relative_order_is_preserved(self) -> None:
        # Raw order 5, 1, 9, 3 must become 0.5, 0.0, 1.0, 0.25.
        result = cf.normalise([5.0, 1.0, 9.0, 3.0])

        assert result[0] == pytest.approx(0.5)
        assert result[1] == pytest.approx(0.0)
        assert result[2] == pytest.approx(1.0)
        assert result[3] == pytest.approx(0.25)

    def test_negative_values_scale_correctly(self) -> None:
        assert cf.normalise([-10.0, 0.0, 10.0]) == [0.0, 0.5, 1.0]

    def test_scale_is_relative_to_the_supplied_values(self) -> None:
        """The same value normalises differently in a different peer group."""
        warm = cf.normalise([20.0, 21.0, 22.0])
        mild = cf.normalise([2.0, 3.0, 4.0])

        assert warm[0] == mild[0] == 0.0
        assert warm == mild

    @pytest.mark.parametrize("constant", [0.0, 7.5, -12.0, 100.0])
    def test_constant_values_normalise_to_neutral(self, constant: float) -> None:
        result = cf.normalise([constant] * 4)

        assert result == [cf.NEUTRAL] * 4

    def test_two_identical_and_two_different_values(self) -> None:
        assert cf.normalise([5.0, 5.0]) == [cf.NEUTRAL, cf.NEUTRAL]
        assert cf.normalise([5.0, 5.0, 7.0]) == [0.0, 0.0, 1.0]

    @pytest.mark.parametrize("empty", [[], [None], [None, None], [math.nan, math.nan]])
    def test_all_missing_normalises_to_neutral(self, empty: list) -> None:
        assert cf.normalise(empty) == [cf.NEUTRAL] * len(empty)

    def test_missing_values_use_the_median_of_available_values(self) -> None:
        # Available: 10, 20, 30 -> median 20 -> the gap must land mid-range.
        result = cf.normalise([10.0, None, 30.0, math.nan, 20.0])

        assert result[0] == 0.0
        assert result[2] == 1.0
        assert result[1] == pytest.approx(0.5)
        assert result[3] == pytest.approx(0.5)
        assert result[4] == pytest.approx(0.5)

    def test_median_of_an_even_count_averages_the_middle_pair(self) -> None:
        assert cf.statistics_median([1.0, 2.0, 3.0, 4.0]) == pytest.approx(2.5)
        assert cf.statistics_median([3.0, 1.0, 2.0]) == pytest.approx(2.0)

    def test_missing_values_never_break_the_range(self) -> None:
        result = cf.normalise([None, 100.0, None, 0.0, math.nan])

        assert all(0.0 <= value <= 1.0 for value in result)

    def test_single_value_is_neutral(self) -> None:
        assert cf.normalise([42.0]) == [cf.NEUTRAL]

    def test_string_numbers_are_accepted(self) -> None:
        assert cf.normalise(["0", "10", "20"]) == [0.0, 0.5, 1.0]


# --------------------------------------------------------------------------- #
# Variable -> feature mapping
# --------------------------------------------------------------------------- #


class TestFeatureMapping:
    """Each feature must respond to exactly one weather variable."""

    def test_temperature_controls_head_width(self) -> None:
        cold = cf.face_geometry(make_spec(temperature=0.0), 0.5, 0.45)
        hot = cf.face_geometry(make_spec(temperature=1.0), 0.5, 0.45)

        assert hot.head_rx > cold.head_rx
        assert cold.head_rx == pytest.approx(cf.HEAD_BASE_RADIUS * cf.HEAD_WIDTH_RANGE[0])
        assert hot.head_rx == pytest.approx(cf.HEAD_BASE_RADIUS * cf.HEAD_WIDTH_RANGE[1])

    def test_humidity_controls_eye_radius(self) -> None:
        dry = cf.face_geometry(make_spec(humidity=0.0), 0.5, 0.45)
        wet = cf.face_geometry(make_spec(humidity=1.0), 0.5, 0.45)

        assert wet.eye_radius > dry.eye_radius
        assert dry.eye_radius == pytest.approx(cf.EYE_RADIUS_RANGE[0])
        assert wet.eye_radius == pytest.approx(cf.EYE_RADIUS_RANGE[1])

    def test_wind_controls_eyebrow_angle(self) -> None:
        calm = cf.face_geometry(make_spec(wind=0.0), 0.5, 0.45)
        windy = cf.face_geometry(make_spec(wind=1.0), 0.5, 0.45)

        assert brow_angle_degrees(windy) > brow_angle_degrees(calm)
        assert brow_angle_degrees(calm) == pytest.approx(cf.BROW_ANGLE_RANGE[0])
        assert brow_angle_degrees(windy) == pytest.approx(cf.BROW_ANGLE_RANGE[1])

    def test_precipitation_controls_mouth_curvature(self) -> None:
        dry = cf.face_geometry(make_spec(precipitation=0.0), 0.5, 0.45)
        wet = cf.face_geometry(make_spec(precipitation=1.0), 0.5, 0.45)

        assert wet.mouth_depth > dry.mouth_depth
        assert dry.mouth_depth == pytest.approx(cf.MOUTH_DEPTH_RANGE[0])
        assert wet.mouth_depth == pytest.approx(cf.MOUTH_DEPTH_RANGE[1])

    def test_apparent_temperature_controls_nose_length(self) -> None:
        cold = cf.face_geometry(make_spec(apparent_temperature=0.0), 0.5, 0.45)
        warm = cf.face_geometry(make_spec(apparent_temperature=1.0), 0.5, 0.45)

        assert warm.nose_length > cold.nose_length
        assert cold.nose_length == pytest.approx(cf.NOSE_LENGTH_RANGE[0])
        assert warm.nose_length == pytest.approx(cf.NOSE_LENGTH_RANGE[1])

    def test_mouth_curls_up_when_dry_and_down_when_wet(self) -> None:
        dry = cf.face_geometry(make_spec(precipitation=0.0), 0.5, 0.45)
        wet = cf.face_geometry(make_spec(precipitation=1.0), 0.5, 0.45)

        assert dry.mouth_depth < 0.0  # slightly upward
        assert wet.mouth_depth > 0.0  # clearly downward

    def test_each_feature_ignores_the_other_variables(self) -> None:
        """Only the encoded quantity may depend on a given variable."""
        base = cf.face_geometry(make_spec(), 0.5, 0.45)

        hotter = cf.face_geometry(make_spec(temperature=1.0), 0.5, 0.45)
        assert hotter.eye_radius == pytest.approx(base.eye_radius)
        assert hotter.mouth_depth == pytest.approx(base.mouth_depth)
        assert hotter.nose_length == pytest.approx(base.nose_length)
        assert brow_angle_degrees(hotter) == pytest.approx(brow_angle_degrees(base))

        wetter = cf.face_geometry(make_spec(humidity=1.0), 0.5, 0.45)
        assert wetter.head_rx == pytest.approx(base.head_rx)
        assert wetter.mouth_depth == pytest.approx(base.mouth_depth)
        assert wetter.nose_length == pytest.approx(base.nose_length)
        assert brow_angle_degrees(wetter) == pytest.approx(brow_angle_degrees(base))

        windier = cf.face_geometry(make_spec(wind=1.0), 0.5, 0.45)
        assert windier.eye_radius == pytest.approx(base.eye_radius)
        assert windier.head_rx == pytest.approx(base.head_rx)
        assert windier.mouth_depth == pytest.approx(base.mouth_depth)
        assert windier.nose_length == pytest.approx(base.nose_length)

        rainier = cf.face_geometry(make_spec(precipitation=1.0), 0.5, 0.45)
        assert rainier.eye_radius == pytest.approx(base.eye_radius)
        assert rainier.head_rx == pytest.approx(base.head_rx)
        assert rainier.nose_length == pytest.approx(base.nose_length)

        warmer = cf.face_geometry(make_spec(apparent_temperature=1.0), 0.5, 0.45)
        assert warmer.eye_radius == pytest.approx(base.eye_radius)
        assert warmer.head_rx == pytest.approx(base.head_rx)
        assert warmer.mouth_depth == pytest.approx(base.mouth_depth)

    def test_features_are_monotonic_across_the_whole_range(self) -> None:
        previous = -1.0
        for step in range(11):
            geometry = cf.face_geometry(make_spec(temperature=step / 10), 0.5, 0.45)
            assert geometry.head_rx > previous
            previous = geometry.head_rx

    def test_out_of_range_specs_are_clamped(self) -> None:
        low = cf.face_geometry(make_spec(temperature=-5.0, humidity=-5.0), 0.5, 0.45)
        zero = cf.face_geometry(make_spec(temperature=0.0, humidity=0.0), 0.5, 0.45)
        high = cf.face_geometry(make_spec(temperature=5.0, humidity=5.0), 0.5, 0.45)
        one = cf.face_geometry(make_spec(temperature=1.0, humidity=1.0), 0.5, 0.45)

        assert low.head_rx == pytest.approx(zero.head_rx)
        assert high.head_rx == pytest.approx(one.head_rx)
        assert high.eye_radius == pytest.approx(one.eye_radius)


# --------------------------------------------------------------------------- #
# Geometry bounds
# --------------------------------------------------------------------------- #


def head_half_width_at(geometry: cf.FaceGeometry, y: float) -> float:
    """Half-width of the head ellipse at a given row."""
    ratio = (y - geometry.cy) / geometry.head_ry
    return geometry.head_rx * math.sqrt(max(0.0, 1.0 - ratio * ratio))


#: The two extremes of every variable. Because each feature is a monotonic
#: function of its own input (asserted separately in
#: ``TestFeatureMapping.test_features_are_monotonic_across_the_whole_range``),
#: these 32 combinations are the worst case for the containment checks.
EXTREME_SPECS: list[cf.FaceSpec] = [
    cf.FaceSpec(*values)
    for values in itertools.product([0.0, 1.0], repeat=len(ALL_FEATURES))
]
EXTREME_IDS = [
    "-".join(f"{getattr(spec, name):g}" for name in ALL_FEATURES) for spec in EXTREME_SPECS
]


class TestGeometryBounds:
    """Every feature must stay inside the head and inside its grid cell."""

    @pytest.mark.parametrize("spec", EXTREME_SPECS, ids=EXTREME_IDS)
    def test_head_fits_inside_the_cell(self, spec: cf.FaceSpec) -> None:
        geometry = cf.face_geometry(spec, 0.5, 0.45)

        assert geometry.cy - geometry.head_ry > 0.0
        assert geometry.cy + geometry.head_ry < 1.0

    @pytest.mark.parametrize("spec", EXTREME_SPECS, ids=EXTREME_IDS)
    def test_features_stay_inside_the_head_outline(self, spec: cf.FaceSpec) -> None:
        geometry = cf.face_geometry(spec, 0.5, 0.45)

        # Eyes (both use the same offset and radius, so one check covers both)
        eye_edge = geometry.eye_dx + geometry.eye_radius
        assert eye_edge < head_half_width_at(geometry, geometry.eye_y - geometry.eye_radius)

        # Eyebrows (check the outer end at both ends of the tilt)
        brow_edge = geometry.eye_dx + geometry.brow_half_width
        for brow_y in (geometry.brow_y - geometry.brow_rise, geometry.brow_y + geometry.brow_rise):
            assert brow_edge < head_half_width_at(geometry, brow_y)

        # Mouth
        assert geometry.mouth_half_width < head_half_width_at(
            geometry, geometry.mouth_y + geometry.mouth_depth
        )

        # Nose
        nose_row_width = head_half_width_at(geometry, geometry.nose_top + geometry.nose_length)
        assert nose_row_width > cf.NOSE_HOOK_WIDTH

    @pytest.mark.parametrize("spec", EXTREME_SPECS, ids=EXTREME_IDS)
    def test_features_do_not_overlap_each_other(self, spec: cf.FaceSpec) -> None:
        geometry = cf.face_geometry(spec, 0.5, 0.45)

        # The y axis is reversed, so smaller y is visually higher.
        eye_top = geometry.eye_y - geometry.eye_radius
        brow_bottom = geometry.brow_y + geometry.brow_rise
        assert eye_top > brow_bottom, "eyebrows must stay above the eyes"

        nose_bottom = geometry.nose_top + geometry.nose_length
        mouth_bottom = geometry.mouth_y + geometry.mouth_depth
        assert mouth_bottom > nose_bottom, "nose must end above the mouth"
        assert nose_bottom < geometry.cy + geometry.head_ry, "nose must stay inside the jaw"


# --------------------------------------------------------------------------- #
# Shape construction
# --------------------------------------------------------------------------- #


class TestFaceShapes:
    def test_shape_count_per_face(self) -> None:
        shapes = cf.face_shapes(cf.face_geometry(cf.FaceSpec(), 0.5, 0.45))

        assert len(shapes) == SHAPES_PER_FACE

    def test_shape_types(self) -> None:
        shapes = cf.face_shapes(cf.face_geometry(cf.FaceSpec(), 0.5, 0.45))
        types = [shape["type"] for shape in shapes]

        assert types == ["circle", "circle", "circle", "line", "line", "path", "path"]

    def test_coordinates_are_finite(self) -> None:
        for shape in cf.face_shapes(cf.face_geometry(cf.FaceSpec(), 0.5, 0.45)):
            for value in shape.values():
                if isinstance(value, (int, float)):
                    assert math.isfinite(value)

    def test_paths_avoid_scientific_notation(self) -> None:
        """Plotly's SVG path parser rejects exponents, so paths must be plain."""
        tiny = cf.FaceSpec(temperature=0.0, humidity=0.0, precipitation=0.0)
        shapes = cf.face_shapes(cf.face_geometry(tiny, 0.5, 0.45))

        for shape in shapes:
            path = shape.get("path")
            if path:
                assert "e-" not in path.lower()
                assert "e+" not in path.lower()

    def test_mouth_path_is_a_quadratic_curve(self) -> None:
        shapes = cf.face_shapes(cf.face_geometry(cf.FaceSpec(), 0.5, 0.45))
        mouth = next(shape for shape in shapes if shape["type"] == "path" and "Q" in shape["path"])

        assert mouth["path"].count("Q") == 1
        assert mouth["path"].startswith("M ")

    def test_eyebrows_are_mirror_images(self) -> None:
        geometry = cf.face_geometry(make_spec(wind=1.0), 0.5, 0.45)
        shapes = cf.face_shapes(geometry)
        left, right = [shape for shape in shapes if shape["type"] == "line"]

        # Reflection about the face centre (cx = 0.5) maps x to 1.0 - x.
        assert left["x0"] == pytest.approx(1.0 - right["x1"])
        assert left["x1"] == pytest.approx(1.0 - right["x0"])

    def test_brow_tilt_is_symmetric_about_the_vertical_axis(self) -> None:
        geometry = cf.face_geometry(make_spec(wind=1.0), 0.5, 0.45)
        shapes = cf.face_shapes(geometry)
        left, right = [shape for shape in shapes if shape["type"] == "line"]

        # Both inner ends must be raised by the same amount.
        assert left["y1"] == pytest.approx(right["y0"])
        assert left["y0"] == pytest.approx(right["y1"])


# --------------------------------------------------------------------------- #
# Record preparation
# --------------------------------------------------------------------------- #


class TestBuildFaceRows:
    def test_one_row_per_record_up_to_the_limit(self) -> None:
        rows = cf.build_face_rows(make_hourly_frame(8), cf.HOURLY_FACE_SOURCE, 4)

        assert len(rows) == 4
        assert [row.label for row in rows] == ["Fri 09:00", "Fri 10:00", "Fri 11:00", "Fri 12:00"]

    def test_limit_larger_than_the_frame(self) -> None:
        rows = cf.build_face_rows(make_hourly_frame(3), cf.HOURLY_FACE_SOURCE, 12)

        assert len(rows) == 3

    def test_daily_source(self) -> None:
        rows = cf.build_face_rows(make_daily_frame(7), cf.DAILY_FACE_SOURCE, 7)

        assert len(rows) == 7
        assert rows[0].summary.startswith("☀️")

    def test_reported_values_are_preserved_exactly(self) -> None:
        """The table must show what was reported, not a rescaled number."""
        frame = make_hourly_frame(2)
        rows = cf.build_face_rows(frame, cf.HOURLY_FACE_SOURCE, 2)

        assert rows[0].values["temperature"] == "20"
        assert rows[1].values["temperature"] == "21"
        assert rows[0].values["wind_speed"] == "5"

    def test_decimals_are_preserved(self) -> None:
        frame = make_hourly_frame(1)
        frame.loc[0, "temperature"] = 21.46
        rows = cf.build_face_rows(frame, cf.HOURLY_FACE_SOURCE, 1)

        assert rows[0].values["temperature"] == "21.5"

    def test_tooltip_contains_the_label_and_every_variable(self) -> None:
        rows = cf.build_face_rows(make_hourly_frame(2), cf.HOURLY_FACE_SOURCE, 2)
        tooltip = rows[0].tooltip

        assert "Fri 09:00" in tooltip
        for variable in cf.HOURLY_FACE_SOURCE.variables:
            assert variable.display in tooltip

    def test_summary_uses_real_values(self) -> None:
        rows = cf.build_face_rows(make_hourly_frame(1), cf.HOURLY_FACE_SOURCE, 1)

        assert rows[0].summary == "20 °C · 40% RH · 5 km/h"

    def test_normalisation_is_relative_to_the_drawn_records(self) -> None:
        frame = make_hourly_frame(3)
        rows = cf.build_face_rows(frame, cf.HOURLY_FACE_SOURCE, 3)

        assert [row.spec.temperature for row in rows] == [0.0, 0.5, 1.0]

    def test_raising_the_limit_changes_the_scale(self) -> None:
        """A 2-face view must still span the full 0-1 range."""
        frame = make_hourly_frame(4)
        rows = cf.build_face_rows(frame, cf.HOURLY_FACE_SOURCE, 2)

        assert rows[0].spec.temperature == 0.0
        assert rows[1].spec.temperature == 1.0


class TestBuildFaceRowsEdgeCases:
    @pytest.mark.parametrize(
        "frame",
        [None, pd.DataFrame(), pd.DataFrame(columns=["label", "temperature"])],
        ids=["none", "empty", "no-rows"],
    )
    def test_empty_data_yields_no_rows(self, frame) -> None:
        assert cf.build_face_rows(frame, cf.HOURLY_FACE_SOURCE, 6) == []

    @pytest.mark.parametrize("limit", [0, -3])
    def test_non_positive_limit_yields_no_rows(self, limit: int) -> None:
        assert cf.build_face_rows(make_hourly_frame(4), cf.HOURLY_FACE_SOURCE, limit) == []

    def test_missing_columns_are_drawn_neutrally(self) -> None:
        frame = make_hourly_frame(4).drop(columns=["wind_speed", "apparent_temperature"])
        rows = cf.build_face_rows(frame, cf.HOURLY_FACE_SOURCE, 4)

        assert len(rows) == 4
        assert all(row.spec.wind == cf.NEUTRAL for row in rows)
        assert all(row.spec.apparent_temperature == cf.NEUTRAL for row in rows)

    def test_missing_columns_show_an_em_dash(self) -> None:
        frame = make_hourly_frame(2).drop(columns=["wind_speed"])
        rows = cf.build_face_rows(frame, cf.HOURLY_FACE_SOURCE, 2)

        assert rows[0].values["wind_speed"] == "—"
        assert "—" in rows[0].summary

    def test_missing_values_do_not_crash(self) -> None:
        frame = make_hourly_frame(4)
        frame.loc[1, "temperature"] = math.nan
        frame.loc[2, "humidity"] = None
        rows = cf.build_face_rows(frame, cf.HOURLY_FACE_SOURCE, 4)

        assert len(rows) == 4
        assert rows[1].values["temperature"] == "—"
        assert all(0.0 <= row.spec.temperature <= 1.0 for row in rows)

    def test_every_column_missing_still_produces_neutral_faces(self) -> None:
        frame = make_hourly_frame(3)
        for column in (
            "temperature",
            "humidity",
            "wind_speed",
            "apparent_temperature",
            "precipitation_probability",
        ):
            frame[column] = None

        rows = cf.build_face_rows(frame, cf.HOURLY_FACE_SOURCE, 3)

        assert len(rows) == 3
        assert all(row.spec == cf.FaceSpec() for row in rows)

    def test_constant_columns_produce_identical_faces(self) -> None:
        frame = make_hourly_frame(4)
        for column in (
            "temperature",
            "humidity",
            "wind_speed",
            "apparent_temperature",
            "precipitation_probability",
        ):
            frame[column] = 12.0

        rows = cf.build_face_rows(frame, cf.HOURLY_FACE_SOURCE, 4)

        assert all(row.spec == cf.FaceSpec() for row in rows)

    def test_invalid_timestamps_do_not_break_the_tooltip(self) -> None:
        frame = make_hourly_frame(2)
        frame["time"] = ["not-a-time", None]
        rows = cf.build_face_rows(frame, cf.HOURLY_FACE_SOURCE, 2)

        assert len(rows) == 2
        assert "Fri 09:00" in rows[0].tooltip

    def test_blank_labels_fall_back_to_an_em_dash(self) -> None:
        frame = make_hourly_frame(2)
        frame["label"] = [None, math.nan]
        rows = cf.build_face_rows(frame, cf.HOURLY_FACE_SOURCE, 2)

        assert [row.label for row in rows] == ["—", "—"]


# --------------------------------------------------------------------------- #
# Figure construction
# --------------------------------------------------------------------------- #


class TestFigure:
    def test_no_figure_without_rows(self) -> None:
        assert cf.chernoff_figure([]) is None

    def test_shape_count_matches_faces_and_panels(self) -> None:
        rows = cf.build_face_rows(make_hourly_frame(6), cf.HOURLY_FACE_SOURCE, 6)
        figure = cf.chernoff_figure(rows)

        # 7 shapes per face plus one alternating panel for every second cell.
        assert len(figure.layout.shapes) == 6 * SHAPES_PER_FACE + 3

    def test_two_traces_for_labels_and_hover(self) -> None:
        rows = cf.build_face_rows(make_hourly_frame(4), cf.HOURLY_FACE_SOURCE, 4)
        figure = cf.chernoff_figure(rows)

        assert len(figure.data) == 2
        assert figure.data[0].mode == "markers"  # hover layer
        assert figure.data[1].mode == "text"  # labels

    def test_one_hover_entry_per_face(self) -> None:
        rows = cf.build_face_rows(make_hourly_frame(4), cf.HOURLY_FACE_SOURCE, 4)
        figure = cf.chernoff_figure(rows)

        assert len(figure.data[0].x) == 4
        assert len(figure.data[0].text) == 4
        assert len(figure.data[1].text) == 4

    def test_label_text_combines_period_and_summary(self) -> None:
        rows = cf.build_face_rows(make_hourly_frame(2), cf.HOURLY_FACE_SOURCE, 2)
        figure = cf.chernoff_figure(rows)

        assert figure.data[1].text[0] == "Fri 09:00<br>20 °C · 40% RH · 5 km/h"

    def test_grid_layout(self) -> None:
        rows = cf.build_face_rows(make_hourly_frame(6), cf.HOURLY_FACE_SOURCE, 6)
        figure = cf.chernoff_figure(rows, columns=4)

        assert figure.layout.xaxis.range == (0, 4)
        assert figure.layout.yaxis.range == (2, 0)  # reversed: first row on top
        assert figure.layout.width == cf.CELL_PIXELS * 4
        assert figure.layout.height == cf.CELL_PIXELS * 2 + cf.FIGURE_CHROME_PX

    def test_single_face_still_renders(self) -> None:
        rows = cf.build_face_rows(make_hourly_frame(1), cf.HOURLY_FACE_SOURCE, 1)
        figure = cf.chernoff_figure(rows)

        # One face, plus the background panel for the first (even) cell.
        assert len(figure.layout.shapes) == SHAPES_PER_FACE + 1
        assert figure.layout.yaxis.range == (1, 0)

    def test_more_faces_than_columns_wrap_onto_more_rows(self) -> None:
        rows = cf.build_face_rows(make_hourly_frame(12), cf.HOURLY_FACE_SOURCE, 12)
        figure = cf.chernoff_figure(rows, columns=4)

        assert figure.layout.yaxis.range == (3, 0)
        assert len(figure.data[0].x) == 12

    def test_faces_are_never_overlapping_in_the_grid(self) -> None:
        rows = cf.build_face_rows(make_hourly_frame(4), cf.HOURLY_FACE_SOURCE, 4)
        figure = cf.chernoff_figure(rows, columns=4)

        centres = list(zip(figure.data[0].x, figure.data[0].y, strict=True))
        assert centres == [(0.5, 0.45), (1.5, 0.45), (2.5, 0.45), (3.5, 0.45)]

    def test_axes_are_hidden(self) -> None:
        rows = cf.build_face_rows(make_hourly_frame(4), cf.HOURLY_FACE_SOURCE, 4)
        figure = cf.chernoff_figure(rows)

        assert figure.layout.xaxis.visible is False
        assert figure.layout.yaxis.visible is False
        assert figure.layout.showlegend is False

    def test_hover_marker_is_invisible_but_present(self) -> None:
        rows = cf.build_face_rows(make_hourly_frame(2), cf.HOURLY_FACE_SOURCE, 2)
        figure = cf.chernoff_figure(rows)

        assert figure.data[0].marker.color == "rgba(0, 0, 0, 0)"
        assert figure.data[0].marker.size == cf.HOVER_MARKER_PX
        assert "%{text}" in figure.data[0].hovertemplate

    def test_empty_frame_still_produces_drawable_output(self) -> None:
        frame = make_hourly_frame(3)
        for variable in cf.HOURLY_FACE_SOURCE.variables:
            frame[variable.column] = None
        rows = cf.build_face_rows(frame, cf.HOURLY_FACE_SOURCE, 3)

        assert cf.chernoff_figure(rows) is not None


# --------------------------------------------------------------------------- #
# Supporting views
# --------------------------------------------------------------------------- #


class TestValuesTable:
    def test_table_columns_follow_the_source_mapping(self) -> None:
        rows = cf.build_face_rows(make_hourly_frame(3), cf.HOURLY_FACE_SOURCE, 3)
        table = cf.face_values_table(rows, cf.HOURLY_FACE_SOURCE)

        assert list(table.columns) == [
            "Period",
            "Temperature (°C)",
            "Relative humidity (%)",
            "Wind speed (km/h)",
            "Precipitation probability (%)",
            "Apparent temperature (°C)",
        ]

    def test_table_holds_one_row_per_face(self) -> None:
        rows = cf.build_face_rows(make_daily_frame(5), cf.DAILY_FACE_SOURCE, 5)
        table = cf.face_values_table(rows, cf.DAILY_FACE_SOURCE)

        assert len(table) == 5
        assert table["Period"].tolist() == [row.label for row in rows]

    def test_table_shows_reported_values_not_normalised_ones(self) -> None:
        frame = make_hourly_frame(3)
        rows = cf.build_face_rows(frame, cf.HOURLY_FACE_SOURCE, 3)
        table = cf.face_values_table(rows, cf.HOURLY_FACE_SOURCE)

        assert table["Temperature (°C)"].tolist() == ["20", "21", "22"]


class TestFormatValue:
    @pytest.mark.parametrize(
        "raw,expected",
        [(20.0, "20"), (21.46, "21.5"), (0, "0"), ("30", "30"), (-3.0, "-3")],
    )
    def test_numbers_are_formatted_compactly(self, raw: object, expected: str) -> None:
        assert cf.format_value(raw) == expected

    @pytest.mark.parametrize("raw", [None, math.nan, ""])
    def test_missing_values_use_an_em_dash(self, raw: object) -> None:
        assert cf.format_value(raw) == "—"

    def test_text_values_pass_through(self) -> None:
        assert cf.format_value("Clear sky") == "Clear sky"


class TestSourceDefinitions:
    def test_both_sources_exist(self) -> None:
        assert set(cf.FACE_SOURCES) == {"hourly", "daily"}

    @pytest.mark.parametrize("source", [cf.HOURLY_FACE_SOURCE, cf.DAILY_FACE_SOURCE])
    def test_every_source_maps_all_five_features(self, source: cf.FaceSource) -> None:
        assert {variable.key for variable in source.variables} == set(ALL_FEATURES)

    @pytest.mark.parametrize("source", [cf.HOURLY_FACE_SOURCE, cf.DAILY_FACE_SOURCE])
    def test_every_variable_documents_its_feature(self, source: cf.FaceSource) -> None:
        for variable in source.variables:
            assert variable.feature.strip()
            assert variable.direction.strip()
            assert variable.display.strip()

    def test_hourly_and_daily_use_the_documented_features(self) -> None:
        features = {variable.key: variable.feature for variable in cf.HOURLY_FACE_SOURCE.variables}

        assert features == {
            "temperature": "face width",
            "humidity": "eye size",
            "wind": "eyebrow angle",
            "precipitation": "mouth curvature",
            "apparent_temperature": "nose length",
        }

    def test_daily_reuses_the_same_features(self) -> None:
        hourly = {v.key: v.feature for v in cf.HOURLY_FACE_SOURCE.variables}
        daily = {v.key: v.feature for v in cf.DAILY_FACE_SOURCE.variables}

        assert hourly == daily

    @pytest.mark.parametrize("source", [cf.HOURLY_FACE_SOURCE, cf.DAILY_FACE_SOURCE])
    def test_variable_keys_match_the_face_spec_fields(self, source: cf.FaceSource) -> None:
        spec_fields = {field.name for field in dataclasses.fields(cf.FaceSpec)}

        assert {variable.key for variable in source.variables} <= spec_fields

    def test_variable_columns_exist_in_the_matching_frame(self) -> None:
        hourly_columns = set(make_hourly_frame(6).columns)
        daily_columns = set(make_daily_frame(7).columns)

        assert all(v.column in hourly_columns for v in cf.HOURLY_FACE_SOURCE.variables)
        assert all(v.column in daily_columns for v in cf.DAILY_FACE_SOURCE.variables)

    def test_summary_columns_exist_in_the_matching_frame(self) -> None:
        assert set(cf._summary_columns(cf.HOURLY_FACE_SOURCE)) <= set(make_hourly_frame(6).columns)
        assert set(cf._summary_columns(cf.DAILY_FACE_SOURCE)) <= set(make_daily_frame(7).columns)
