"""Chernoff Faces: normalisation and geometry, free of any UI framework.

A Chernoff face encodes several variables of one record at once, so faces can
be compared side by side at a glance. Each face here represents exactly one
real forecast record (an hourly step or a day) from a DataFrame produced by
:mod:`app.utils.data_processing` - this module never fetches data, never draws
anything and never invents values.

It is deliberately presentation-agnostic: it converts real measurements into
normalised ``[0, 1]`` encodings (:func:`normalise`) and then into concrete
drawing coordinates (:func:`face_geometry`, :func:`face_shapes`). Both the
Streamlit renderer in :mod:`app.components.chernoff` and the FastAPI layer in
:mod:`app.api.routers.weather` consume these functions, so there is exactly one
implementation of the encoding rules.

Feature mapping (see :data:`HOURLY_FACE_VARIABLES` / :data:`DAILY_FACE_VARIABLES`):

======================  =========================  ==========================
Weather variable        Facial feature            How a higher value looks
======================  =========================  ==========================
Temperature             face width                wider
Relative humidity       eye size                  larger eyes
Wind speed              eyebrow angle             steeper, more angled brows
Precipitation prob.     mouth curvature           flatter, then deeper curve
Apparent temperature    nose length               longer nose
======================  =========================  ==========================

Every variable is min-max normalised to ``[0, 1]`` *across the faces being
drawn*, then mapped onto a bounded geometry range. A constant-valued variable
normalises to the neutral midpoint, and missing values fall back to the median
of the available values for geometry only - the reported values themselves are
never modified.
"""

from __future__ import annotations

import contextlib
import logging
import math
import string
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Final

import pandas as pd

LOGGER = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Geometry bounds
# --------------------------------------------------------------------------- #
# All values are expressed in "cell units": one grid cell is 1.0 x 1.0 and the
# face is centred inside it. Keeping the feature ranges fixed here is what
# guarantees that no face can ever be drawn outside sensible bounds.

#: Half-height of the head, in cell units. The head is an ellipse, so this is
#: also half of its vertical extent.
HEAD_BASE_RADIUS: Final[float] = 0.32

#: Temperature -> horizontal half-width of the head, as a multiple of the base
#: radius. Narrow faces are cooler, wide faces warmer.
HEAD_WIDTH_RANGE: Final[tuple[float, float]] = (0.72, 1.20)

#: Relative humidity -> eye radius, in cell units.
EYE_RADIUS_RANGE: Final[tuple[float, float]] = (0.028, 0.078)

#: Eye separation and brow length, as multiples of the head half-width. These
#: scale with the face so features stay inside the head outline.
EYE_SPREAD: Final[float] = 0.40
BROW_SPREAD: Final[float] = 0.17
MOUTH_SPREAD: Final[float] = 0.34

#: Wind speed -> eyebrow tilt in degrees. Negative is a flat/resting brow,
#: positive is a steeply angled one. The range is kept modest so the raised
#: outer end of a brow cannot escape the head outline.
BROW_ANGLE_RANGE: Final[tuple[float, float]] = (-30.0, 32.0)

#: Precipitation probability -> how far the mouth curve deviates from its
#: endpoints, in cell units. Negative curls upward, positive curls downward.
MOUTH_DEPTH_RANGE: Final[tuple[float, float]] = (-0.015, 0.100)

#: Apparent temperature -> nose length, in cell units.
NOSE_LENGTH_RANGE: Final[tuple[float, float]] = (0.045, 0.125)

#: Fixed vertical placement of the features relative to the face centre. Note
#: that a y axis running downwards makes *smaller* y higher up.
EYE_OFFSET_Y: Final[float] = -0.062
BROW_OFFSET_Y: Final[float] = -0.195
NOSE_OFFSET_Y: Final[float] = 0.005
MOUTH_OFFSET_Y: Final[float] = 0.175

#: Horizontal width of the little hook at the bottom of the nose.
NOSE_HOOK_WIDTH: Final[float] = 0.035

# --------------------------------------------------------------------------- #
# Presentation constants
# --------------------------------------------------------------------------- #

#: Pixels per grid cell. Cells are square so a face is never distorted.
CELL_PIXELS: Final[int] = 165
#: Grid columns; the face count is chosen so the grid never gets too wide.
GRID_COLUMNS: Final[int] = 4
#: Extra pixels added to the figure height for the surrounding chrome.
FIGURE_CHROME_PX: Final[int] = 28
#: Vertical offset of the face centre inside its cell, leaving room for labels.
CENTRE_OFFSET_Y: Final[float] = 0.45
#: Vertical position of the two-line label, as a fraction down the cell.
LABEL_POSITION_Y: Final[float] = 0.93
#: Transparent marker size (px) that carries the hover tooltip.
HOVER_MARKER_PX: Final[int] = 132

#: How many faces a caller may ask for.
FACE_COUNT_CHOICES: Final[tuple[int, ...]] = (4, 6, 8, 12)
DEFAULT_FACE_COUNT: Final[int] = 6

#: Normalised value used for a constant or entirely missing variable.
NEUTRAL: Final[float] = 0.5
#: Spans at or below this are treated as "no variation".
_EPSILON: Final[float] = 1e-9

FACE_OUTLINE: Final[str] = "#374151"
FACE_FILL: Final[str] = "#FFFFFF"
EYE_FILL: Final[str] = "#1F2937"
PANEL_FILL: Final[str] = "#F5F7FA"


# --------------------------------------------------------------------------- #
# Variable mapping
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class FaceVariable:
    """How one DataFrame column drives one facial feature.

    Attributes:
        key: Attribute name on :class:`FaceSpec`.
        column: Column in the source DataFrame.
        label: Human-readable variable name.
        unit: Unit suffix, or an empty string.
        feature: The facial feature this variable drives.
        direction: What a higher value looks like.
    """

    key: str
    column: str
    label: str
    unit: str
    feature: str
    direction: str

    @property
    def display(self) -> str:
        """Variable name including its unit, e.g. ``"Wind speed (km/h)"``."""
        return f"{self.label} ({self.unit})" if self.unit else self.label


@dataclass(frozen=True, slots=True)
class FaceSource:
    """A forecast block that Chernoff faces can be drawn from.

    Attributes:
        key: Stable identifier, also used as the widget key in the UI.
        label: Name shown in the source selector.
        label_column: Column holding the time/date label for a record.
        time_column: Column holding the timestamp, used for tooltips.
        variables: Variable-to-feature mapping for this block.
        summary_template: ``str.format`` template for the per-face summary.
    """

    key: str
    label: str
    label_column: str
    time_column: str
    variables: tuple[FaceVariable, ...]
    summary_template: str


HOURLY_FACE_VARIABLES: Final[tuple[FaceVariable, ...]] = (
    FaceVariable(
        key="temperature",
        column="temperature",
        label="Temperature",
        unit="°C",
        feature="face width",
        direction="wider",
    ),
    FaceVariable(
        key="humidity",
        column="humidity",
        label="Relative humidity",
        unit="%",
        feature="eye size",
        direction="larger eyes",
    ),
    FaceVariable(
        key="wind",
        column="wind_speed",
        label="Wind speed",
        unit="km/h",
        feature="eyebrow angle",
        direction="steeper, more angled brows",
    ),
    FaceVariable(
        key="precipitation",
        column="precipitation_probability",
        label="Precipitation probability",
        unit="%",
        feature="mouth curvature",
        direction="flatter, then a deeper curve",
    ),
    FaceVariable(
        key="apparent_temperature",
        column="apparent_temperature",
        label="Apparent temperature",
        unit="°C",
        feature="nose length",
        direction="longer nose",
    ),
)

DAILY_FACE_VARIABLES: Final[tuple[FaceVariable, ...]] = (
    FaceVariable(
        key="temperature",
        column="temperature_max",
        label="Daily maximum temperature",
        unit="°C",
        feature="face width",
        direction="wider",
    ),
    FaceVariable(
        key="humidity",
        column="humidity_mean",
        label="Mean relative humidity",
        unit="%",
        feature="eye size",
        direction="larger eyes",
    ),
    FaceVariable(
        key="wind",
        column="wind_speed_max",
        label="Maximum wind speed",
        unit="km/h",
        feature="eyebrow angle",
        direction="steeper, more angled brows",
    ),
    FaceVariable(
        key="precipitation",
        column="precipitation_probability_max",
        label="Max precipitation probability",
        unit="%",
        feature="mouth curvature",
        direction="flatter, then a deeper curve",
    ),
    FaceVariable(
        key="apparent_temperature",
        column="apparent_temperature_max",
        label="Max apparent temperature",
        unit="°C",
        feature="nose length",
        direction="longer nose",
    ),
)

HOURLY_FACE_SOURCE: Final[FaceSource] = FaceSource(
    key="hourly",
    label="Hourly",
    label_column="label",
    time_column="time",
    variables=HOURLY_FACE_VARIABLES,
    summary_template="{temperature} °C · {humidity}% RH · {wind_speed} km/h",
)

DAILY_FACE_SOURCE: Final[FaceSource] = FaceSource(
    key="daily",
    label="Daily",
    label_column="label",
    time_column="date",
    variables=DAILY_FACE_VARIABLES,
    summary_template="{icon} {condition} · {temperature_max}/{temperature_min} °C",
)

FACE_SOURCES: Final[dict[str, FaceSource]] = {
    HOURLY_FACE_SOURCE.key: HOURLY_FACE_SOURCE,
    DAILY_FACE_SOURCE.key: DAILY_FACE_SOURCE,
}


# --------------------------------------------------------------------------- #
# Normalisation
# --------------------------------------------------------------------------- #


def coerce_float(value: Any) -> float:
    """Convert a DataFrame cell to a float, using ``NaN`` for unusable values.

    Args:
        value: Raw cell value. ``None``, booleans, blanks, text and infinities
            all become ``NaN``.

    Returns:
        A finite float, or ``NaN``.
    """
    if value is None or isinstance(value, bool):
        return math.nan
    try:
        number = float(value)
    except (TypeError, ValueError):
        return math.nan
    return number if math.isfinite(number) else math.nan


def normalise(values: Sequence[Any]) -> list[float]:
    """Min-max scale ``values`` into ``[0, 1]``.

    The scaling is relative to the values supplied, so the same 20 °C appears
    differently in a hot spell and in a cool one - that is the point of the
    comparison. Missing values are replaced by the median of the available
    values *for geometry only*; if nothing is available the whole series falls
    back to the neutral midpoint.

    Args:
        values: Raw measurements, in record order.

    Returns:
        One normalised value per input, always within ``[0, 1]``.
    """
    numbers = [coerce_float(value) for value in values]
    usable = [number for number in numbers if not math.isnan(number)]
    if not usable:
        return [NEUTRAL] * len(numbers)

    fill = statistics_median(usable)
    filled = [fill if math.isnan(number) else number for number in numbers]

    low, high = min(filled), max(filled)
    span = high - low
    if span <= _EPSILON:
        return [NEUTRAL] * len(filled)

    return [_clamp((value - low) / span) for value in filled]


def statistics_median(values: Sequence[float]) -> float:
    """Return the median of ``values`` (which must not be empty)."""
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def _clamp(value: float) -> float:
    """Clamp ``value`` into ``[0, 1]``."""
    return min(1.0, max(0.0, value))


def _lerp(normalised: float, bounds: tuple[float, float]) -> float:
    """Map a normalised value onto a bounded geometry range."""
    low, high = bounds
    return low + (high - low) * _clamp(normalised)


# --------------------------------------------------------------------------- #
# Records and geometry
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class FaceSpec:
    """Normalised ``[0, 1]`` encodings that drive one face."""

    temperature: float = NEUTRAL
    humidity: float = NEUTRAL
    wind: float = NEUTRAL
    precipitation: float = NEUTRAL
    apparent_temperature: float = NEUTRAL


@dataclass(frozen=True, slots=True)
class FaceRow:
    """One forecast record prepared for drawing.

    Attributes:
        label: Time or date label shown under the face.
        summary: One-line weather summary shown under the face.
        tooltip: Multi-line hover text with the real reported values.
        values: Display-ready values keyed by DataFrame column name.
        spec: Normalised encodings driving the geometry.
    """

    label: str
    summary: str
    tooltip: str
    values: dict[str, str]
    spec: FaceSpec


@dataclass(frozen=True, slots=True)
class FaceGeometry:
    """Concrete drawing coordinates for one face.

    All members are in cell units. Vertical offsets are absolute values derived
    from the face centre, which keeps the features inside the head outline.
    """

    cx: float
    cy: float
    head_rx: float
    head_ry: float
    eye_radius: float
    eye_dx: float
    eye_y: float
    brow_half_width: float
    brow_rise: float
    brow_y: float
    mouth_half_width: float
    mouth_depth: float
    mouth_y: float
    nose_top: float
    nose_length: float


def face_geometry(spec: FaceSpec, cx: float, cy: float) -> FaceGeometry:
    """Turn normalised encodings into drawing coordinates.

    Args:
        spec: Normalised encodings for one record.
        cx: Horizontal centre of the face.
        cy: Vertical centre of the face.

    Returns:
        The geometry for that face, with every feature inside the head outline.
    """
    head_ry = HEAD_BASE_RADIUS
    head_rx = head_ry * _lerp(spec.temperature, HEAD_WIDTH_RANGE)
    eye_dx = EYE_SPREAD * head_rx
    brow_half_width = BROW_SPREAD * head_rx
    brow_angle = _lerp(spec.wind, BROW_ANGLE_RANGE)

    return FaceGeometry(
        cx=cx,
        cy=cy,
        head_rx=head_rx,
        head_ry=head_ry,
        eye_radius=_lerp(spec.humidity, EYE_RADIUS_RANGE),
        eye_dx=eye_dx,
        eye_y=cy + EYE_OFFSET_Y,
        brow_half_width=brow_half_width,
        brow_rise=brow_half_width * math.tan(math.radians(brow_angle)),
        brow_y=cy + BROW_OFFSET_Y,
        mouth_half_width=MOUTH_SPREAD * head_rx,
        mouth_depth=_lerp(spec.precipitation, MOUTH_DEPTH_RANGE),
        mouth_y=cy + MOUTH_OFFSET_Y,
        nose_top=cy + NOSE_OFFSET_Y,
        nose_length=_lerp(spec.apparent_temperature, NOSE_LENGTH_RANGE),
    )


def face_shapes(geometry: FaceGeometry) -> list[dict[str, Any]]:
    """Convert face geometry into drawing primitives.

    The returned dictionaries describe a head ellipse, two eyes, two eyebrows,
    a nose and a mouth in cell units. They are deliberately plain data so any
    renderer can consume them: Plotly turns them into layout shapes, and a
    browser can turn them into SVG elements.

    Args:
        geometry: Coordinates from :func:`face_geometry`.

    Returns:
        Drawing primitives for the head, eyes, eyebrows, nose and mouth.
    """
    cx, cy = geometry.cx, geometry.cy
    radius = geometry.eye_radius

    head = {
        "type": "circle",
        "x0": cx - geometry.head_rx,
        "x1": cx + geometry.head_rx,
        "y0": cy - geometry.head_ry,
        "y1": cy + geometry.head_ry,
        "fillcolor": FACE_FILL,
        "line": _line(FACE_OUTLINE, 1.6),
    }

    eyes = [
        {
            "type": "circle",
            "x0": cx + sign * geometry.eye_dx - radius,
            "x1": cx + sign * geometry.eye_dx + radius,
            "y0": geometry.eye_y - radius,
            "y1": geometry.eye_y + radius,
            "fillcolor": EYE_FILL,
            "line": _line(EYE_FILL, 1.0),
        }
        for sign in (-1.0, 1.0)
    ]

    # The inner end of each brow sits below the outer end as the angle grows,
    # which is what reads as a more sharply angled brow.
    brow_inner = geometry.brow_half_width
    brows = [
        {
            "type": "line",
            "x0": cx - geometry.eye_dx - brow_inner,
            "y0": geometry.brow_y + geometry.brow_rise,
            "x1": cx - geometry.eye_dx + brow_inner,
            "y1": geometry.brow_y - geometry.brow_rise,
            "line": _line(FACE_OUTLINE, 1.8),
        },
        {
            "type": "line",
            "x0": cx + geometry.eye_dx - brow_inner,
            "y0": geometry.brow_y - geometry.brow_rise,
            "x1": cx + geometry.eye_dx + brow_inner,
            "y1": geometry.brow_y + geometry.brow_rise,
            "line": _line(FACE_OUTLINE, 1.8),
        },
    ]

    nose = {
        "type": "path",
        "path": (
            f"M {_n(cx)},{_n(geometry.nose_top)}"
            f" L {_n(cx)},{_n(geometry.nose_top + geometry.nose_length)}"
            f" L {_n(cx + NOSE_HOOK_WIDTH)},{_n(geometry.nose_top + geometry.nose_length)}"
        ),
        "line": _line(FACE_OUTLINE, 1.6),
    }

    # A quadratic Bezier: the control point sits 2x the intended deviation away
    # from the endpoints, so the curve's midpoint moves by exactly mouth_depth.
    mouth = {
        "type": "path",
        "path": (
            f"M {_n(cx - geometry.mouth_half_width)},{_n(geometry.mouth_y)}"
            f" Q {_n(cx)},{_n(geometry.mouth_y + 2 * geometry.mouth_depth)}"
            f" {_n(cx + geometry.mouth_half_width)},{_n(geometry.mouth_y)}"
        ),
        "line": _line(FACE_OUTLINE, 1.8),
    }

    return [head, *eyes, *brows, nose, mouth]


def _line(colour: str, width: float) -> dict[str, Any]:
    """Build a line style for one drawing primitive."""
    return {"color": colour, "width": width}


def _n(value: float) -> str:
    """Format a coordinate for a vector path (never scientific notation)."""
    return f"{value:.4f}"


# --------------------------------------------------------------------------- #
# Record preparation
# --------------------------------------------------------------------------- #


def _column_values(frame: pd.DataFrame, column: str) -> list[Any]:
    """Return ``frame[column]`` as a list, or all-``None`` when the column is absent."""
    if column not in frame.columns:
        return [None] * len(frame)
    return list(frame[column])


def format_value(value: Any) -> str:
    """Format a reported value for display, using an em dash when unavailable."""
    number = coerce_float(value)
    if math.isnan(number):
        if isinstance(value, str) and value.strip():
            return value.strip()
        return "—"
    if number.is_integer():
        return str(int(number))
    return f"{number:.1f}"


def build_face_rows(
    frame: pd.DataFrame | None,
    source: FaceSource,
    limit: int = DEFAULT_FACE_COUNT,
) -> list[FaceRow]:
    """Prepare up to ``limit`` records from ``frame`` for drawing.

    Normalisation is computed across the records actually drawn, so the
    comparison is always relative to the faces on screen.

    Args:
        frame: Hourly or daily DataFrame from the processing layer.
        source: Describes the columns and labels to use.
        limit: Maximum number of faces to prepare.

    Returns:
        One :class:`FaceRow` per record. Empty when there is no usable data.
    """
    if frame is None or frame.empty or limit <= 0:
        return []

    subset = frame.head(limit)
    if subset.empty:
        return []

    missing_columns = [v.column for v in source.variables if v.column not in subset.columns]
    if missing_columns:
        LOGGER.warning(
            "Chernoff faces: source %r is missing column(s) %s; those features "
            "will be drawn neutrally",
            source.key,
            missing_columns,
        )

    # Each variable is scaled across the faces being drawn.
    needed = {variable.column for variable in source.variables} | set(_summary_columns(source))
    raw_columns = {column: _column_values(subset, column) for column in needed}
    scaled = {
        variable.key: normalise(raw_columns[variable.column])
        for variable in source.variables
    }
    formatted = {
        column: [format_value(value) for value in values]
        for column, values in raw_columns.items()
    }

    labels = _column_values(subset, source.label_column)
    timestamps = _column_values(subset, source.time_column)

    rows: list[FaceRow] = []
    for index in range(len(subset)):
        spec = FaceSpec(
            **{variable.key: scaled[variable.key][index] for variable in source.variables}
        )
        values = {
            variable.column: formatted[variable.column][index]
            for variable in source.variables
        }
        label = _text_of(labels[index])
        rows.append(
            FaceRow(
                label=label or "—",
                summary=_format_summary(source, formatted, index),
                tooltip=_build_tooltip(source, label, timestamps[index], values),
                values=values,
                spec=spec,
            )
        )
    return rows


def _summary_columns(source: FaceSource) -> tuple[str, ...]:
    """Return every column referenced by the summary template."""
    names = {
        field
        for _, field, _, _ in string.Formatter().parse(source.summary_template)
        if field
    }
    return tuple(sorted(names))


def _format_summary(
    source: FaceSource, formatted: dict[str, list[str]], index: int
) -> str:
    """Render the one-line summary for record ``index``."""
    context = {
        column: values[index] for column, values in formatted.items() if len(values) > index
    }
    try:
        return source.summary_template.format(**context)
    except (KeyError, IndexError):
        return "—"


def _text_of(value: Any) -> str:
    """Return a stripped string for a label-like value, or an empty string."""
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "nat", "none"} else text


def _build_tooltip(
    source: FaceSource, label: str, timestamp: Any, values: dict[str, str]
) -> str:
    """Build the multi-line hover text for one face."""
    lines = [f"<b>{label or '—'}</b>"]
    with contextlib.suppress(TypeError, ValueError):
        if not _is_blank(timestamp):
            lines.append(f"<i>{pd.Timestamp(timestamp):%a %d %b, %H:%M}</i>")
    for variable in source.variables:
        lines.append(f"{variable.display}: {values.get(variable.column, '—')}")
    return "\n".join(lines)


def _is_blank(value: Any) -> bool:
    """Return ``True`` for ``None`` or pandas missing-value markers."""
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False
