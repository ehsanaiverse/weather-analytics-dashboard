"""Timezone-aware helpers for local-time rendering.

The Open-Meteo API returns naive timestamps already expressed in the queried
location's local time (``timezone=auto``). These helpers attach the correct
IANA timezone for display purposes and gracefully fall back to the UTC offset
supplied by the API when the zone is unavailable on this machine.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

LOGGER = logging.getLogger(__name__)


def resolve_timezone(iana_name: str | None, utc_offset_seconds: int | None = None):
    """Return a ``tzinfo`` for ``iana_name`` with a fixed-offset fallback.

    Args:
        iana_name: IANA zone name such as ``"Asia/Karachi"``.
        utc_offset_seconds: Offset reported by the Forecast API, used when the
            IANA zone cannot be resolved locally.

    Returns:
        A ``tzinfo`` instance, or UTC when nothing usable is available.
    """
    if iana_name:
        try:
            return ZoneInfo(iana_name)
        except (ZoneInfoNotFoundError, ValueError, OSError):
            LOGGER.warning("Unknown timezone %r; falling back to UTC offset", iana_name)

    if isinstance(utc_offset_seconds, (int, float)):
        return timezone(timedelta(seconds=int(utc_offset_seconds)))

    return UTC


def local_now(tzinfo) -> datetime:
    """Return the current time in the given timezone."""
    return datetime.now(tzinfo)


def to_local(naive_local: datetime, tzinfo) -> datetime:
    """Attach ``tzinfo`` to a naive timestamp already expressed in local time."""
    return naive_local.replace(tzinfo=tzinfo)


def format_local_time(naive_local: datetime | None, tzinfo, fmt: str = "%H:%M") -> str:
    """Format a local timestamp, returning an em dash when unavailable."""
    if naive_local is None:
        return "—"
    return to_local(naive_local, tzinfo).strftime(fmt)


def format_utc_retrieval(retrieved_at: datetime | None, fmt: str = "%Y-%m-%d %H:%M UTC") -> str:
    """Format the UTC instant at which a response was fetched."""
    if retrieved_at is None:
        return "—"
    return retrieved_at.astimezone(UTC).strftime(fmt)
