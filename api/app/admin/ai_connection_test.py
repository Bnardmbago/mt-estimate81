from openai import AsyncOpenAI
import anthropic


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


async def test_openai_connection(api_key: str) -> tuple[bool, str]:
    if not api_key:
        return False, "API key is required"

    try:
        client = AsyncOpenAI(api_key=api_key, timeout=15.0)
        await client.models.list()
        return True, "Connection successful"
    except Exception as exc:
        return False, _friendly_error(exc)


async def test_anthropic_connection(api_key: str, model: str) -> tuple[bool, str]:
    if not api_key:
        return False, "API key is required"
    if not model:
        return False, "Model is required"

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key, timeout=15.0)
        await client.messages.create(
            model=model,
            max_tokens=1,
            messages=[{"role": "user", "content": "ping"}],
        )
        return True, "Connection successful"
    except Exception as exc:
        return False, _friendly_error(exc)
