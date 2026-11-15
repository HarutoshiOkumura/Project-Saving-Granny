"""Timeout and retries for one model call (CLAUDE.md conventions, perception rules).

Each attempt gets a hard `asyncio.timeout`, whatever the client library does. Timeouts, network
errors, 408, 429 and 5xx are retried with backoff, at most `len(backoff_s)` times; anything else
(a 400, a bad key, an incomplete answer) is raised at once, because asking again will not help.
The clients' own retries are off, so these are the only ones.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence

import httpx

logger = logging.getLogger(__name__)

BACKOFF_S: tuple[float, ...] = (1.0, 2.0, 4.0)
RETRY_AFTER_CAP_S = 30.0
RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


class GiveUp(Exception):
    """A failure that retrying cannot fix. Raise it from inside the call."""


def status_of(exc: BaseException) -> int | None:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code
    status = getattr(exc, "status_code", None)
    return status if isinstance(status, int) else None


def is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, GiveUp):
        return False
    if isinstance(exc, TimeoutError | httpx.TransportError):
        return True
    status = status_of(exc)
    if status is not None:
        return status in RETRYABLE_STATUS
    # The Gemini SDK's connection and timeout errors carry no status. The SDK exports their class
    # only from a private module, so match the name (APITimeoutError subclasses it).
    return any(cls.__name__ == "APIConnectionError" for cls in type(exc).__mro__)


def retry_after_s(exc: BaseException) -> float | None:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    value = headers.get("retry-after") if headers is not None else None
    try:
        return min(float(value), RETRY_AFTER_CAP_S) if value else None
    except (TypeError, ValueError):
        return None


async def with_retries[T](
    call: Callable[[], Awaitable[T]],
    *,
    timeout_s: float,
    what: str,
    backoff_s: Sequence[float] | None = None,
) -> T:
    """Run `call` until it succeeds; raise its last error after the retries run out."""
    delays = BACKOFF_S if backoff_s is None else tuple(backoff_s)
    for attempt in range(len(delays) + 1):
        try:
            async with asyncio.timeout(timeout_s):
                return await call()
        except Exception as exc:
            if attempt == len(delays) or not is_retryable(exc):
                raise
            delay = retry_after_s(exc) or delays[attempt]
            logger.info(
                "%s attempt=%d failed error=%s retry_in_s=%.1f",
                what,
                attempt + 1,
                describe(exc),
                delay,
            )
            await asyncio.sleep(delay)
    raise AssertionError("unreachable")


def describe(exc: BaseException) -> str:
    detail = str(exc).replace("\n", " ")[:200]
    status = status_of(exc)
    name = f"{type(exc).__name__} {status}" if status else type(exc).__name__
    return f"{name}: {detail}" if detail else name
