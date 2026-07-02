from typing import Any

from app.ai.instruction_resolver import ResolvedInstructions

AI_TIMEOUT_SECONDS = 90.0


def max_document_chars(instructions: ResolvedInstructions | None) -> int | None:
    if instructions is None:
        return None
    value = instructions.parameters.get("max_document_chars")
    return int(value) if value is not None else None


def completion_kwargs(instructions: ResolvedInstructions | None) -> dict[str, Any]:
    if instructions is None:
        return {}

    kwargs: dict[str, Any] = {}
    max_tokens = instructions.parameters.get("max_tokens")
    if max_tokens is not None:
        kwargs["max_tokens"] = int(max_tokens)

    temperature = instructions.parameters.get("temperature")
    if temperature is not None:
        kwargs["temperature"] = float(temperature)

    timeout_seconds = instructions.parameters.get("timeout_seconds")
    if timeout_seconds is not None:
        kwargs["timeout"] = float(timeout_seconds)

    return kwargs


def anthropic_completion_kwargs(instructions: ResolvedInstructions | None) -> dict[str, Any]:
    kwargs = completion_kwargs(instructions)
    kwargs.setdefault("max_tokens", 8192)
    return kwargs
