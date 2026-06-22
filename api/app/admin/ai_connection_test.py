from openai import AsyncOpenAI
import anthropic

from app.admin.ai_config import ANTHROPIC_CONNECTION_TEST_MODEL, ANTHROPIC_MODELS


def _friendly_error(exc: Exception) -> str:
    message = str(exc).strip()
    if not message:
        return "Connection failed"
    lowered = message.lower()
    if "401" in message or "authentication" in lowered or "invalid api key" in lowered:
        return "Invalid API key"
    if "403" in message or "permission" in lowered:
        return "API key lacks permission for this request"
    if "404" in message and "model" in lowered:
        return "Model not found or not available for this API key"
    if "timeout" in lowered:
        return "Connection timed out"
    return message[:200]


def _is_model_not_found(exc: Exception) -> bool:
    message = str(exc).lower()
    return "404" in str(exc) or ("not found" in message and "model" in message)


async def verify_openai_connection(api_key: str) -> tuple[bool, str]:
    if not api_key:
        return False, "API key is required"

    try:
        client = AsyncOpenAI(api_key=api_key, timeout=15.0)
        await client.models.list()
        return True, "Connection successful"
    except Exception as exc:
        return False, _friendly_error(exc)


async def _anthropic_ping(client: anthropic.AsyncAnthropic, model: str) -> None:
    await client.messages.create(
        model=model,
        max_tokens=1,
        messages=[{"role": "user", "content": "ping"}],
    )


async def verify_anthropic_connection(api_key: str, model: str) -> tuple[bool, str]:
    if not api_key:
        return False, "API key is required"

    client = anthropic.AsyncAnthropic(api_key=api_key, timeout=15.0)

    candidates: list[str] = []
    for candidate in (model, ANTHROPIC_CONNECTION_TEST_MODEL, *ANTHROPIC_MODELS):
        normalized = candidate.strip()
        if normalized and normalized not in candidates:
            candidates.append(normalized)

    last_error: Exception | None = None
    for candidate in candidates:
        try:
            await _anthropic_ping(client, candidate)
            if candidate != model.strip():
                return True, f"Connection successful (tested with {candidate})"
            return True, "Connection successful"
        except Exception as exc:
            last_error = exc
            if not _is_model_not_found(exc):
                return False, _friendly_error(exc)

    if last_error is not None:
        return False, _friendly_error(last_error)
    return False, "Model is required"
