"""Error handling for the HTTP API.

Every failure leaves the API through the same envelope, so the frontend needs
exactly one error path:

.. code-block:: json

    {
      "error": {"code": "upstream_timeout", "message": "...", "details": []},
      "requestId": "0f0c...",
      "path": "/api/weather",
      "timestamp": "2026-10-02T12:00:00Z"
    }

The mapping reuses the existing exception hierarchy from
:mod:`app.services.exceptions`: each failure mode that the Streamlit app turns
into a friendly sentence becomes an HTTP status here, with diagnostics going to
the log rather than to the client.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Final

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.schemas import ErrorBody, ErrorCode, ErrorDetail, ErrorResponse
from app.services.exceptions import (
    APIRateLimitError,
    APIResponseError,
    APITimeoutError,
    DataProcessingError,
    EmptyQueryError,
    LocationNotFoundError,
    NetworkRequestError,
    WeatherDashboardError,
)

LOGGER = logging.getLogger(__name__)

#: Attribute used to correlate a response with its log lines.
REQUEST_ID_ATTR: Final[str] = "request_id"

#: Header carrying the correlation id back to the caller.
REQUEST_ID_HEADER: Final[str] = "X-Request-ID"

#: ``exception class -> (HTTP status, error code)``.
#:
#: ``APITimeoutError`` is a subclass of ``NetworkRequestError`` and must be
#: listed first: lookup walks the exception's MRO, so the most specific
#: mapping wins.
ERROR_MAPPING: Final[dict[type[Exception], tuple[int, ErrorCode]]] = {
    EmptyQueryError: (status.HTTP_400_BAD_REQUEST, ErrorCode.INVALID_REQUEST),
    LocationNotFoundError: (status.HTTP_404_NOT_FOUND, ErrorCode.LOCATION_NOT_FOUND),
    APIRateLimitError: (status.HTTP_429_TOO_MANY_REQUESTS, ErrorCode.UPSTREAM_RATE_LIMITED),
    APITimeoutError: (status.HTTP_504_GATEWAY_TIMEOUT, ErrorCode.UPSTREAM_TIMEOUT),
    NetworkRequestError: (status.HTTP_502_BAD_GATEWAY, ErrorCode.UPSTREAM_UNREACHABLE),
    APIResponseError: (status.HTTP_502_BAD_GATEWAY, ErrorCode.UPSTREAM_BAD_RESPONSE),
    DataProcessingError: (
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        ErrorCode.PROCESSING_ERROR,
    ),
}

#: Status codes that are the caller's fault rather than a server failure.
#: ``422`` is spelled numerically because Starlette renamed its constant.
_CLIENT_ERROR_CODES: Final[dict[int, ErrorCode]] = {
    status.HTTP_400_BAD_REQUEST: ErrorCode.INVALID_REQUEST,
    status.HTTP_401_UNAUTHORIZED: ErrorCode.INVALID_REQUEST,
    status.HTTP_403_FORBIDDEN: ErrorCode.INVALID_REQUEST,
    status.HTTP_404_NOT_FOUND: ErrorCode.NOT_FOUND,
    status.HTTP_405_METHOD_NOT_ALLOWED: ErrorCode.METHOD_NOT_ALLOWED,
    422: ErrorCode.INVALID_REQUEST,
}


def invalid_request(message: str, *, field: str | None = None) -> HTTPException:
    """Build a 400 error with the standard envelope.

    Args:
        message: User-facing explanation.
        field: Query parameter at fault, when known.

    Returns:
        An :class:`~fastapi.HTTPException` to raise from a dependency.
    """
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=message,
        headers={"field": field} if field else None,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach the shared error envelope to every failure path of ``app``.

    Args:
        app: The FastAPI application to instrument.
    """
    for exception_type, (code, error_code) in ERROR_MAPPING.items():
        app.add_exception_handler(
            exception_type, _weather_error_handler(exception_type, code, error_code)
        )

    app.add_exception_handler(WeatherDashboardError, _unexpected_dashboard_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)


def _weather_error_handler(
    exception_type: type[Exception], http_status: int, error_code: ErrorCode
):
    """Build a handler for one expected, user-facing service failure."""

    async def handler(request: Request, exc: Exception) -> JSONResponse:
        message = str(exc) or "The request could not be completed."
        log = LOGGER.warning if http_status < 500 else LOGGER.error
        log("%s on %s: %s", exception_type.__name__, request.url.path, message)
        headers = {"Retry-After": "60"} if error_code == ErrorCode.UPSTREAM_RATE_LIMITED else None
        return error_response(request, http_status, error_code, message, headers=headers)

    return handler


async def _unexpected_dashboard_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Fallback for a typed error with no explicit mapping."""
    LOGGER.exception("Unmapped dashboard error on %s", request.url.path)
    return error_response(
        request,
        status.HTTP_502_BAD_GATEWAY,
        ErrorCode.UPSTREAM_BAD_RESPONSE,
        str(exc) or "The weather service returned an unexpected response.",
    )


async def _validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Turn FastAPI's query-parameter validation errors into the envelope."""
    errors: list[Any] = list(getattr(exc, "errors", list)())
    details = [
        ErrorDetail(
            field=".".join(str(part) for part in error.get("loc", ())[1:]) or None,
            message=str(error.get("msg", "invalid value")),
        )
        for error in errors
    ]
    message = _validation_message(details)
    LOGGER.info("Rejected request to %s: %s", request.url.path, message)
    return error_response(
        request,
        status.HTTP_400_BAD_REQUEST,
        ErrorCode.INVALID_REQUEST,
        message,
        details=details,
    )


def _validation_message(details: list[ErrorDetail]) -> str:
    """Summarise validation failures in one friendly sentence."""
    if not details:
        return "One or more query parameters are invalid."
    named = [detail.field for detail in details if detail.field]
    if named:
        return f"Invalid value for: {', '.join(sorted(set(named)))}."
    return details[0].message


async def _http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Render an explicit ``HTTPException`` through the shared envelope."""
    http_status = int(getattr(exc, "status_code", status.HTTP_400_BAD_REQUEST))
    detail = getattr(exc, "detail", None)
    message = detail if isinstance(detail, str) and detail else "The request was rejected."
    error_code = _CLIENT_ERROR_CODES.get(http_status, ErrorCode.INVALID_REQUEST)
    headers = dict(getattr(exc, "headers", None) or {})
    field = headers.pop("field", None)
    details = [ErrorDetail(field=field, message=message)] if field else []
    return error_response(
        request, http_status, error_code, message, details=details, headers=headers or None
    )


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last resort: log the traceback, tell the client nothing about it."""
    LOGGER.exception("Unhandled error on %s", request.url.path, exc_info=exc)
    return error_response(
        request,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        ErrorCode.INTERNAL_ERROR,
        "The server hit an unexpected problem handling this request.",
    )


def error_response(
    request: Request,
    http_status: int,
    error_code: ErrorCode,
    message: str,
    *,
    details: list[ErrorDetail] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Build the JSON error envelope for ``request``.

    Args:
        request: The incoming request, used for its path and correlation id.
        http_status: HTTP status code to send.
        error_code: Stable machine-readable identifier.
        message: User-facing explanation; never a stack trace.
        details: Optional field-level details.
        headers: Extra response headers, such as ``Retry-After``.

    Returns:
        A :class:`~fastapi.responses.JSONResponse` carrying the envelope.
    """
    request_id = str(getattr(request.state, REQUEST_ID_ATTR, "") or "")
    payload = ErrorResponse(
        error=ErrorBody(code=error_code, message=message, details=details or []),
        request_id=request_id,
        path=request.url.path,
        timestamp=datetime.now(UTC),
    )
    response_headers = {REQUEST_ID_HEADER: request_id} if request_id else {}
    if headers:
        response_headers.update(headers)
    return JSONResponse(
        status_code=http_status,
        content=payload.model_dump(mode="json", by_alias=True),
        headers=response_headers or None,
    )
