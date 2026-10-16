"""Tests for the geocoding service, including ambiguous and invalid searches."""

from __future__ import annotations

import pytest
import requests

from app import config
from app.services.exceptions import (
    APIRateLimitError,
    APIResponseError,
    APITimeoutError,
    EmptyQueryError,
    LocationNotFoundError,
    NetworkRequestError,
)
from app.services.geocoding_service import Location, search_locations
from tests.conftest import FakeResponse, make_geocoding_payload


class TestSuccessfulSearch:
    def test_returns_all_matches_in_provider_order(self, fake_get) -> None:
        fake_get(FakeResponse(make_geocoding_payload()))

        results = search_locations("Abbottabad")

        assert len(results) == 2
        assert results[0].name == "Abbottabad"
        assert results[0].country == "Pakistan"
        assert results[0].admin1 == "Khyber Pakhtunkhwa"
        assert results[0].latitude == pytest.approx(34.1463)
        assert results[0].longitude == pytest.approx(73.21168)
        assert results[0].timezone == "Asia/Karachi"
        assert results[0].population == 275_890
        assert results[1].name == "Abbottabad Lines"

    def test_sends_the_expected_query_parameters(self, fake_get) -> None:
        calls = fake_get(FakeResponse(make_geocoding_payload()))

        search_locations("  Abbottabad  ", count=5)

        call = calls[0]
        assert call["url"] == config.GEOCODING_API_URL
        assert call["params"] == {
            "name": "Abbottabad",
            "count": 5,
            "language": "en",
            "format": "json",
        }
        assert call["timeout"] == config.REQUEST_TIMEOUT_SECONDS

    def test_default_result_count_comes_from_config(self, fake_get) -> None:
        calls = fake_get(FakeResponse(make_geocoding_payload()))

        search_locations("Abbottabad")

        assert calls[0]["params"]["count"] == config.GEOCODING_RESULT_LIMIT

    def test_labels_are_human_readable(self, fake_get) -> None:
        fake_get(FakeResponse(make_geocoding_payload()))

        first, second = search_locations("Abbottabad")

        assert first.display_name == "Abbottabad, Khyber Pakhtunkhwa, Pakistan"
        assert first.short_label == "Abbottabad, Pakistan"
        assert second.display_name == "Abbottabad Lines, Sindh, Pakistan"

    def test_labels_omit_a_missing_admin_region(self, fake_get) -> None:
        payload = make_geocoding_payload(
            results=[{"name": "Bare", "latitude": 1.0, "longitude": 2.0, "country": "Nowhere"}]
        )
        fake_get(FakeResponse(payload))

        result = search_locations("bare")[0]

        assert result.display_name == "Bare, Nowhere"

    def test_result_without_country_uses_the_bare_name(self, fake_get) -> None:
        payload = make_geocoding_payload(
            results=[{"name": "Nowhere", "latitude": 0.0, "longitude": 0.0}]
        )
        fake_get(FakeResponse(payload))

        result = search_locations("nowhere")[0]

        assert result.display_name == "Nowhere"
        assert result.short_label == "Nowhere"
        assert result.population is None
        assert result.country_code is None


class TestEmptyQueries:
    @pytest.mark.parametrize("query", ["", "   ", "\t\n"])
    def test_blank_queries_are_rejected_without_a_request(self, fake_get, query: str) -> None:
        calls = fake_get(FakeResponse(make_geocoding_payload()))

        with pytest.raises(EmptyQueryError, match="Enter a city name"):
            search_locations(query)

        assert calls == []

    def test_none_query_is_rejected(self, fake_get) -> None:
        fake_get(FakeResponse(make_geocoding_payload()))

        with pytest.raises(EmptyQueryError):
            search_locations(None)  # type: ignore[arg-type]


class TestNoMatches:
    def test_missing_results_key_raises_not_found(self, fake_get) -> None:
        fake_get(FakeResponse({"generationtime_ms": 0.2}))

        with pytest.raises(LocationNotFoundError, match="No location found"):
            search_locations("Atlantis")

    def test_empty_results_list_raises_not_found(self, fake_get) -> None:
        fake_get(FakeResponse({"results": []}))

        with pytest.raises(LocationNotFoundError):
            search_locations("Atlantis")

    def test_results_of_the_wrong_type_raise_not_found(self, fake_get) -> None:
        fake_get(FakeResponse({"results": "not-a-list"}))

        with pytest.raises(LocationNotFoundError, match="unexpected response"):
            search_locations("Atlantis")


class TestMalformedResults:
    def test_unusable_entries_are_skipped(self, fake_get) -> None:
        payload = make_geocoding_payload(
            results=[
                {"name": "No coordinates"},  # missing latitude/longitude
                {"name": "Bad coords", "latitude": "north", "longitude": "west"},
                {"name": "Out of range", "latitude": 999.0, "longitude": 10.0},
                "a bare string",
                {"name": "Good", "latitude": 10.0, "longitude": 20.0, "country": "Nowhere"},
            ]
        )
        fake_get(FakeResponse(payload))

        results = search_locations("somewhere")

        assert [item.name for item in results] == ["Good"]

    def test_result_without_a_name_is_skipped(self, fake_get) -> None:
        """An unnamed result is unusable, so it must not be offered."""
        payload = make_geocoding_payload(
            results=[
                {"latitude": 1.0, "longitude": 2.0, "country": "Nowhere"},
                {"name": "Good", "latitude": 3.0, "longitude": 4.0},
            ]
        )
        fake_get(FakeResponse(payload))

        results = search_locations("x")

        assert [item.name for item in results] == ["Good"]

    def test_blank_name_gets_a_placeholder(self, fake_get) -> None:
        payload = make_geocoding_payload(
            results=[{"name": "   ", "latitude": 1.0, "longitude": 2.0, "country": "Nowhere"}]
        )
        fake_get(FakeResponse(payload))

        assert search_locations("x")[0].name == "Unknown location"

    def test_non_numeric_population_becomes_none(self, fake_get) -> None:
        payload = make_geocoding_payload(
            results=[
                {
                    "name": "Odd",
                    "latitude": 1.0,
                    "longitude": 2.0,
                    "population": "many",
                }
            ]
        )
        fake_get(FakeResponse(payload))

        assert search_locations("odd")[0].population is None

    def test_all_entries_invalid_raises_not_found(self, fake_get) -> None:
        fake_get(FakeResponse(make_geocoding_payload(results=[{"name": "No coordinates"}])))

        with pytest.raises(LocationNotFoundError):
            search_locations("broken")

    def test_float_population_is_converted(self, fake_get) -> None:
        payload = make_geocoding_payload(
            results=[
                {"name": "Odd", "latitude": 1.0, "longitude": 2.0, "population": 1234.7}
            ]
        )
        fake_get(FakeResponse(payload))

        assert search_locations("odd")[0].population == 1234


class TestTransportAndHttpErrors:
    def test_timeout_is_reported(self, fake_get) -> None:
        fake_get(error=requests.Timeout("slow"))

        with pytest.raises(APITimeoutError):
            search_locations("Abbottabad")

    def test_connection_failure_is_reported(self, fake_get) -> None:
        fake_get(error=requests.ConnectionError("offline"))

        with pytest.raises(NetworkRequestError):
            search_locations("Abbottabad")

    def test_rate_limit_is_reported(self, fake_get) -> None:
        fake_get(FakeResponse({}, status_code=429))

        with pytest.raises(APIRateLimitError):
            search_locations("Abbottabad")

    def test_server_error_is_reported(self, fake_get) -> None:
        fake_get(FakeResponse({}, status_code=503))

        with pytest.raises(APIResponseError, match="503"):
            search_locations("Abbottabad")

    def test_malformed_json_is_reported(self, fake_get) -> None:
        fake_get(FakeResponse(invalid_json=True, text="not json"))

        with pytest.raises(APIResponseError, match="malformed"):
            search_locations("Abbottabad")


class TestDefaultLocation:
    def test_default_location_is_abbottabad(self) -> None:
        location = Location.from_default_config()

        assert location.name == "Abbottabad"
        assert location.country == "Pakistan"
        assert location.timezone == "Asia/Karachi"
        assert -90 <= location.latitude <= 90
        assert -180 <= location.longitude <= 180

    def test_default_location_matches_config(self) -> None:
        location = Location.from_default_config()

        assert location.latitude == pytest.approx(config.DEFAULT_LOCATION["latitude"])
        assert location.longitude == pytest.approx(config.DEFAULT_LOCATION["longitude"])

    def test_locations_are_hashable_and_immutable(self) -> None:
        location = Location(name="A", latitude=1.0, longitude=2.0)

        assert isinstance(hash(location), int)
        with pytest.raises(AttributeError):
            location.name = "B"  # type: ignore[misc]
