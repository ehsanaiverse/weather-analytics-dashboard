"""A single, well-behaved HTTP entry point for every Open-Meteo call.

Keeping transport concerns here guarantees the dashboard never duplicates
request logic and that timeouts, status codes and malformed payloads are
handled uniformly. Every failure is translated into a
:class:`~app.services.exceptions.WeatherDashboardError` subclass so callers
never have to import :mod:`requests`.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import requests

from app import config
from app.services.exceptions import (
    APIRateLimitError,
    APIResponseError,
    APITimeoutError,
    NetworkRequestError,
)

LOGGER = logging.getLogger(__name__)


def get_json(
    url: str,
    params: Mapping[str, Any] | None = None,
    *,
    timeout: float = config.REQUEST_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Perform a GET request and return the decoded JSON object.

    Args:
        url: Absolute endpoint URL.
        params: Query string parameters.
        timeout: Read timeout in seconds.

    Returns:
        The parsed JSON body, guaranteed to be a ``dict``.

    Raises:
        APITimeoutError: The request exceeded ``timeout``.
        NetworkRequestError: Connection, DNS or TLS failure.
        APIRateLimitError: The provider returned HTTP 429.
        APIResponseError: Any other non-2xx status, or a body that is not a
            JSON object.
    """
    try:
        response = requests.get(
            url,
            params=params,
            timeout=timeout,
            headers={"User-Agent": config.USER_AGENT, "Accept": "application/json"},
        )
    except requests.Timeout as exc:
        LOGGER.warning("Timeout after %ss calling %s", timeout, url)
        raise APITimeoutError(
            f"The weather service did not respond within {timeout:.0f} seconds."
        ) from exc
    except requests.RequestException as exc:
        LOGGER.warning("Network failure calling %s: %s", url, exc)
        raise NetworkRequestError(
            "Could not reach the weather service. Check your internet connection."
        ) from exc

    if response.status_code == config.HTTP_TOO_MANY_REQUESTS:
        LOGGER.warning("Rate limited by %s (HTTP 429)", url)
        raise APIRateLimitError(
            "The weather service is receiving too many requests. "
            "Please wait a minute and refresh."
        )

    if not config.HTTP_OK <= response.status_code < config.HTTP_MULTIPLE_CHOICES:
        LOGGER.error("HTTP %s from %s: %s", response.status_code, url, response.text[:300])
        raise APIResponseError(
            f"The weather service returned an unexpected status "
            f"(HTTP {response.status_code})."
        )

    return _decode_json_object(response, url)


def _decode_json_object(response: requests.Response, url: str) -> dict[str, Any]:
    """Validate that ``response`` carries a JSON object.

    Raises:
        APIResponseError: The body is not valid JSON or not a JSON object.
    """
    try:
        payload = response.json()
    except ValueError as exc:  # includes json.JSONDecodeError
        LOGGER.error("Malformed JSON from %s: %s", url, response.text[:300])
        raise APIResponseError(
            "The weather service returned a malformed response."
        ) from exc

    if not isinstance(payload, dict):
        LOGGER.error("Unexpected JSON root type %s from %s", type(payload).__name__, url)
        raise APIResponseError(
            "The weather service returned an unexpected response format."
        )

    # Open-Meteo signals errors with HTTP 200 plus an ``error``/``reason`` body.
    if "error" in payload and payload["error"] is True:
        reason = payload.get("reason") or "unknown error"
        LOGGER.error("API reported an error for %s: %s", url, reason)
        raise APIResponseError(f"The weather service reported an error: {reason}.")

    return payload
