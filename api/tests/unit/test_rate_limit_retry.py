import asyncio

import httpx
import pytest
from openai import RateLimitError

from app.ai.rate_limit_retry import (
    is_rate_limit_error,
    parse_retry_after_seconds,
    retry_wait_seconds,
    with_rate_limit_retry,
)


def _rate_limit_error(message: str) -> RateLimitError:
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(429, request=request, text=message)
    return RateLimitError(message, response=response, body={"error": {"message": message}})


def test_parse_retry_after_seconds_from_openai_message():
    message = (
        "Rate limit reached for gpt-4o ... Limit 30000, Used 29673, "
        "Requested 7575. Please try again in 14.496s."
    )
    assert parse_retry_after_seconds(message) == pytest.approx(14.496)


def test_is_rate_limit_error_openai():
    exc = _rate_limit_error("rate limited")
    assert is_rate_limit_error(exc) is True
    assert is_rate_limit_error(ValueError("other")) is False


def test_retry_wait_seconds_uses_provider_hint():
    exc = _rate_limit_error("try again in 10s")
    assert retry_wait_seconds(exc, attempt=0) == pytest.approx(10.5)


def test_retry_wait_seconds_exponential_fallback():
    assert retry_wait_seconds(ValueError("429 rate limit"), attempt=0) == 2.0
    assert retry_wait_seconds(ValueError("429 rate limit"), attempt=2) == 8.0


@pytest.mark.asyncio
async def test_with_rate_limit_retry_succeeds_after_rate_limit(monkeypatch):
    calls = {"count": 0}
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    async def operation():
        calls["count"] += 1
        if calls["count"] == 1:
            raise _rate_limit_error("Please try again in 1.5s")
        return "ok"

    result = await with_rate_limit_retry(operation, max_retries=2)

    assert result == "ok"
    assert calls["count"] == 2
    assert sleeps == [pytest.approx(2.0)]


@pytest.mark.asyncio
async def test_with_rate_limit_retry_raises_after_exhausted_retries(monkeypatch):
    calls = {"count": 0}

    async def fake_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    async def operation():
        calls["count"] += 1
        raise _rate_limit_error("rate limited")

    with pytest.raises(RateLimitError):
        await with_rate_limit_retry(operation, max_retries=2)

    assert calls["count"] == 3


@pytest.mark.asyncio
async def test_with_rate_limit_retry_does_not_retry_other_errors():
    calls = {"count": 0}

    async def operation():
        calls["count"] += 1
        raise ValueError("bad request")

    with pytest.raises(ValueError, match="bad request"):
        await with_rate_limit_retry(operation)

    assert calls["count"] == 1
