"""Guard against drift between the Python and TypeScript Chernoff ports.

The Chernoff Faces feature is implemented twice on purpose: Plotly draws it in
the Streamlit dashboard, SVG draws it in the React frontend, and both must encode
the same numbers the same way. The geometry ranges therefore live in two places -
``app/utils/chernoff.py`` and ``frontend/src/lib/chernoff.ts`` - and this test
parses the TypeScript file and fails when a value drifts.

The TypeScript suite pins the *behaviour* (normalisation, feature mapping, SVG
paths); this file pins the *constants*, which is the part that cannot be derived
from the other side.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.utils import chernoff as cf

#: TypeScript file holding the port.
FRONTEND_CHERNOFF = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "chernoff.ts"

#: ``TS constant -> Python attribute``.
SHARED_CONSTANTS: dict[str, str] = {
    "HEAD_BASE_RADIUS": "HEAD_BASE_RADIUS",
    "EYE_SPREAD": "EYE_SPREAD",
    "BROW_SPREAD": "BROW_SPREAD",
    "MOUTH_SPREAD": "MOUTH_SPREAD",
    "EYE_OFFSET_Y": "EYE_OFFSET_Y",
    "BROW_OFFSET_Y": "BROW_OFFSET_Y",
    "NOSE_OFFSET_Y": "NOSE_OFFSET_Y",
    "MOUTH_OFFSET_Y": "MOUTH_OFFSET_Y",
    "NOSE_HOOK_WIDTH": "NOSE_HOOK_WIDTH",
    "CELL_PX": "CELL_PIXELS",

    "NEUTRAL": "NEUTRAL",
    "EPSILON": "_EPSILON",
    "FACE_COUNT_CHOICES": "FACE_COUNT_CHOICES",
    "DEFAULT_FACE_COUNT": "DEFAULT_FACE_COUNT",
}

#: ``TS constant -> Python attribute`` for the bounded ranges.
SHARED_RANGES: dict[str, str] = {
    "HEAD_WIDTH_RANGE": "HEAD_WIDTH_RANGE",
    "EYE_RADIUS_RANGE": "EYE_RADIUS_RANGE",
    "BROW_ANGLE_RANGE": "BROW_ANGLE_RANGE",
    "MOUTH_DEPTH_RANGE": "MOUTH_DEPTH_RANGE",
    "NOSE_LENGTH_RANGE": "NOSE_LENGTH_RANGE",
}


def _typescript_source() -> str:
    """Read the TypeScript chernoff module, skipping when it is absent."""
    if not FRONTEND_CHERNOFF.is_file():
        pytest.skip("frontend/src/lib/chernoff.ts is not present")
    return FRONTEND_CHERNOFF.read_text(encoding="utf-8")


def _scalar(source: str, name: str) -> float:
    """Extract a numeric constant declared as ``const NAME = <number>``."""
    match = re.search(rf"export const {name} = (-?[\d.]+(?:e-?\d+)?)", source)
    if match is None:
        pytest.fail(f"{name} is not declared as a numeric constant in the TypeScript port")
    return float(match.group(1))


def _array(source: str, name: str) -> tuple[float, ...]:
    """Extract a numeric array constant, e.g. ``const X = [4, 6, 8, 12]``."""
    match = re.search(rf"export const {name}: readonly number\[\] = \[([^\]]+)\]", source)
    if match is None:
        pytest.fail(f"{name} is not declared as a numeric array constant")
    return tuple(float(part) for part in match.group(1).split(","))


def _pair(source: str, name: str) -> tuple[float, float]:
    """Extract a two-number tuple constant, e.g. ``const X = [0.72, 1.2]``."""
    match = re.search(rf"export const {name}: readonly \[number, number\] = \[([^\]]+)\]", source)
    if match is None:
        pytest.fail(f"{name} is not declared as a [number, number] constant")
    parts = [float(part) for part in match.group(1).split(",")]
    if len(parts) != 2:
        pytest.fail(f"{name} must hold exactly two numbers")
    return parts[0], parts[1]


@pytest.mark.parametrize(("ts_name", "python_attribute"), sorted(SHARED_CONSTANTS.items()))
def test_scalar_constants_match(ts_name: str, python_attribute: str) -> None:
    """Every shared scalar constant has the same value on both sides."""
    source = _typescript_source()
    expected = getattr(cf, python_attribute)
    if isinstance(expected, tuple):
        # Tuple-valued constants are declared as arrays in TypeScript.
        assert _array(source, ts_name) == pytest.approx(
            tuple(float(value) for value in expected), abs=1e-12
        )
        return
    assert _scalar(source, ts_name) == pytest.approx(float(expected), abs=1e-12)


@pytest.mark.parametrize(("ts_name", "python_attribute"), sorted(SHARED_RANGES.items()))
def test_bounded_ranges_match(ts_name: str, python_attribute: str) -> None:
    """Every geometry range has the same bounds on both sides."""
    expected = getattr(cf, python_attribute)
    assert _pair(_typescript_source(), ts_name) == pytest.approx(
        (float(expected[0]), float(expected[1])), abs=1e-12
    )


def test_the_typescript_port_documents_its_python_source() -> None:
    """The port must point at the module it mirrors, or nobody will keep it in sync."""
    source = _typescript_source()
    assert "app/utils/chernoff.py" in source
    assert "FaceSpec" in source


def test_both_ports_expose_the_same_neutral_spec() -> None:
    """The neutral spec is the fallback for missing data in both implementations."""
    source = _typescript_source()
    neutral = _scalar(source, "NEUTRAL")
    assert pytest.approx(neutral) == cf.NEUTRAL
    # FaceSpec() defaults every field to NEUTRAL on the Python side.
    spec = cf.FaceSpec()
    assert all(
        pytest.approx(getattr(spec, field)) == neutral
        for field in ("temperature", "humidity", "wind", "precipitation", "apparent_temperature")
    )
