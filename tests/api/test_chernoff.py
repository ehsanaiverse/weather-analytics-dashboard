"""Tests for the Chernoff Faces payloads and the extraction that enabled them."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.utils import chernoff as pure
from tests.api.conftest import full_forecast_payload, params_with_coordinates
from tests.conftest import FakeResponse

#: Every normalised feature value must land inside this range.
SPEC_FEATURES = (
    "temperature",
    "humidity",
    "wind",
    "precipitation",
    "apparentTemperature",
)


def test_weather_response_carries_faces_for_both_sources(
    client: TestClient, fake_get
) -> None:
    fake_get(FakeResponse(full_forecast_payload()))

    chernoff = client.get("/api/weather", params=params_with_coordinates()).json()["chernoff"]

    assert set(chernoff["sources"]) == {"hourly", "daily"}
    assert len(chernoff["sources"]["hourly"]["faces"]) == 6
    assert len(chernoff["sources"]["daily"]["faces"]) == 6
    assert chernoff["note"]


@pytest.mark.parametrize("source", ["hourly", "daily"])
def test_every_spec_value_is_normalised(client: TestClient, fake_get, source: str) -> None:
    fake_get(FakeResponse(full_forecast_payload()))

    faces = client.get(
        "/api/chernoff",
        params=params_with_coordinates(source=source, count=6),
    ).json()["sources"][source]["faces"]

    assert len(faces) == 6
    for face in faces:
        for feature in SPEC_FEATURES:
            assert 0.0 <= face["spec"][feature] <= 1.0


def test_normalisation_spans_the_full_range_across_the_faces(
    client: TestClient, fake_get
) -> None:
    fake_get(FakeResponse(full_forecast_payload()))

    faces = client.get(
        "/api/chernoff",
        params=params_with_coordinates(source="daily", count=8),
    ).json()["sources"]["daily"]["faces"]

    assert len(faces) == 7
    temperatures = [face["spec"]["temperature"] for face in faces]
    assert min(temperatures) == pytest.approx(0.0)
    assert max(temperatures) == pytest.approx(1.0)


def test_a_constant_variable_normalises_to_the_neutral_value(
    client: TestClient, fake_get
) -> None:
    payload = full_forecast_payload()
    payload["daily"]["wind_speed_10m_max"] = [12.0] * 7
    fake_get(FakeResponse(payload))

    body = client.get(
        "/api/chernoff",
        params=params_with_coordinates(source="daily", count=8),
    ).json()

    assert body["sources"]["daily"]["neutralValue"] == pure.NEUTRAL
    assert all(face["spec"]["wind"] == pure.NEUTRAL for face in body["sources"]["daily"]["faces"])


def test_each_face_reports_the_real_reported_values(
    client: TestClient, fake_get
) -> None:
    fake_get(FakeResponse(full_forecast_payload()))

    face = client.get(
        "/api/chernoff",
        params=params_with_coordinates(source="daily", count=4),
    ).json()["sources"]["daily"]["faces"][0]

    assert face["label"] == "Fri 02 Oct"
    assert face["values"]["temperature_max"] == "26.6"
    assert face["values"]["humidity_mean"] == "48"
    assert "Daily maximum temperature (°C): 26.6" in face["tooltip"]
    assert face["summary"]


def test_the_mapping_legend_is_included(client: TestClient, fake_get) -> None:
    fake_get(FakeResponse(full_forecast_payload()))

    features = client.get(
        "/api/chernoff",
        params=params_with_coordinates(source="hourly"),
    ).json()["sources"]["hourly"]["features"]

    assert [feature["feature"] for feature in features] == [
        "face width",
        "eye size",
        "eyebrow angle",
        "mouth curvature",
        "nose length",
    ]
    assert [feature["variable"] for feature in features] == [
        "temperature",
        "humidity",
        "wind",
        "precipitation",
        "apparent_temperature",
    ]


@pytest.mark.parametrize("count", [4, 6, 8])
def test_supported_face_counts_are_honoured(client: TestClient, fake_get, count: int) -> None:
    fake_get(FakeResponse(full_forecast_payload()))

    faces = client.get(
        "/api/chernoff",
        params=params_with_coordinates(source="hourly", count=count),
    ).json()["sources"]["hourly"]["faces"]

    assert len(faces) == count


def test_daily_faces_are_capped_by_the_number_of_days(
    client: TestClient, fake_get
) -> None:
    fake_get(FakeResponse(full_forecast_payload()))

    body = client.get(
        "/api/chernoff",
        params=params_with_coordinates(source="daily", count=12),
    ).json()["sources"]["daily"]

    assert body["requestedCount"] == 12
    assert len(body["faces"]) == 7


@pytest.mark.parametrize("count", [1, 3, 5, 9, 13])
def test_unsupported_face_counts_are_rejected(
    client: TestClient, fake_get, count: int
) -> None:
    fake_get(FakeResponse(full_forecast_payload()))

    response = client.get(
        "/api/chernoff",
        params=params_with_coordinates(source="hourly", count=count),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


@pytest.mark.parametrize("source", ["weekly", "", "HOURLY2", "hourly,daily"])
def test_unknown_sources_are_rejected(client: TestClient, fake_get, source: str) -> None:
    calls = fake_get(FakeResponse(full_forecast_payload()))

    response = client.get(
        "/api/chernoff", params=params_with_coordinates(source=source)
    )

    assert response.status_code == 400
    assert calls == []


def test_missing_source_parameter_is_rejected(client: TestClient, fake_get) -> None:
    calls = fake_get(FakeResponse(full_forecast_payload()))

    response = client.get("/api/chernoff", params=params_with_coordinates())

    assert response.status_code == 400
    assert calls == []


def test_source_is_case_insensitive(client: TestClient, fake_get) -> None:
    fake_get(FakeResponse(full_forecast_payload()))

    response = client.get(
        "/api/chernoff", params=params_with_coordinates(source=" DAILY ")
    )

    assert response.status_code == 200
    assert "daily" in response.json()["sources"]


def test_missing_values_do_not_break_the_faces(client: TestClient, fake_get) -> None:
    payload = full_forecast_payload()
    payload["daily"]["apparent_temperature_max"] = [None] * 7
    fake_get(FakeResponse(payload))

    body = client.get(
        "/api/chernoff",
        params=params_with_coordinates(source="daily", count=8),
    ).json()

    faces = body["sources"]["daily"]["faces"]
    assert len(faces) == 7
    assert all(0.0 <= face["spec"]["apparentTemperature"] <= 1.0 for face in faces)
    assert all(face["values"]["apparent_temperature_max"] == "—" for face in faces)


def test_an_unusable_source_returns_404(client: TestClient, fake_get) -> None:
    payload = full_forecast_payload()
    payload["daily"] = {"time": ["not-a-date"], "temperature_2m_max": [1.0]}
    fake_get(FakeResponse(payload))

    response = client.get(
        "/api/chernoff", params=params_with_coordinates(source="daily")
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_hourly_faces_reuse_the_same_cached_forecast(
    client: TestClient, fake_get
) -> None:
    calls = fake_get(FakeResponse(full_forecast_payload()))

    client.get("/api/chernoff", params=params_with_coordinates(source="hourly"))
    client.get("/api/chernoff", params=params_with_coordinates(source="daily"))

    assert len(calls) == 1


# --------------------------------------------------------------------------- #
# Backwards compatibility of the extraction
# --------------------------------------------------------------------------- #


def test_streamlit_module_reexports_the_pure_logic() -> None:
    from app.components import chernoff as ui  # noqa: PLC0415 - import under test

    assert ui.normalise is pure.normalise
    assert ui.face_geometry is pure.face_geometry
    assert ui.build_face_rows is pure.build_face_rows
    assert ui.FACE_SOURCES is pure.FACE_SOURCES
    assert ui._summary_columns is pure._summary_columns


def test_streamlit_module_still_renders() -> None:
    from app.components import chernoff as ui  # noqa: PLC0415 - import under test

    assert callable(ui.render_chernoff_faces)
    assert callable(ui.chernoff_figure)
    assert callable(ui.face_values_table)


def test_the_extracted_module_does_not_import_a_ui_framework() -> None:
    source = pure.__file__
    assert source is not None
    with open(source, encoding="utf-8") as handle:
        text = handle.read()
    assert "import streamlit" not in text
    assert "import plotly" not in text
