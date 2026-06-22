import asyncio
import re
from collections.abc import Awaitable, Callable
from typing import TypeVar

from anthropic import RateLimitError as AnthropicRateLimitError
from openai import APIStatusError as OpenAIAPIStatusError
from openai import RateLimitError as OpenAIRateLimitError

T = TypeVar("T")

_RETRY_AFTER_PATTERN = re.compile(r"try again in ([\d.]+)\s*s", re.IGNORECASE)

# Retries after the first failed attempt (4 attempts total by default).
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_SECONDS = 2.0
MAX_WAIT_SECONDS = 120.0
RETRY_BUFFER_SECONDS = 0.5


def parse_retry_after_seconds(message: str) -> float | None:
    match = _RETRY_AFTER_PATTERN.search(message)
    if not match:
        return None
    return float(match.group(1))


def is_rate_limit_error(exc: BaseException) -> bool:
    if isinstance(exc, (OpenAIRateLimitError, AnthropicRateLimitError)):
        return True
    if isinstance(exc, OpenAIAPIStatusError) and exc.status_code == 429:
        return True
    message = str(exc).lower()
    return "rate limit" in message or "error code: 429" in message


def retry_wait_seconds(exc: BaseException, attempt: int) -> float:
    parsed = parse_retry_after_seconds(str(exc))
    if parsed is not None:
        return min(parsed + RETRY_BUFFER_SECONDS, MAX_WAIT_SECONDS)
    return min(DEFAULT_BACKOFF_SECONDS * (2**attempt), MAX_WAIT_SECONDS)


async def with_rate_limit_retry(
    operation: Callable[[], Awaitable[T]],
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> T:
    for attempt in range(max_retries + 1):
        try:
            return await operation()
        except BaseException as exc:
            if not is_rate_limit_error(exc) or attempt >= max_retries:
                raise
            await asyncio.sleep(retry_wait_seconds(exc, attempt))
