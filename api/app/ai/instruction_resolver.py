from dataclasses import dataclass
from typing import Any, Callable, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.ai_instruction_config import get_instruction_layer, merge_parameters
from app.ai.guardrails import get_guardrails
from app.models.ai_instruction_layer import InstructionLocation

InstructionLocale = Literal["en", "ja"]


@dataclass(frozen=True)
class ResolvedInstructions:
    system: str
    user_prefix: str
    parameters: dict[str, int | float]


def _append_section(base: str, section: str | None) -> str:
    if not section:
        return base
    section = section.strip()
    if not section:
        return base
    if not base:
        return section
    return f"{base.rstrip()}\n\n{section}"


def _append_restrictions(base: str, negative_prompt: str | None) -> str:
    if not negative_prompt or not negative_prompt.strip():
        return base
    return _append_section(base, f"## Restrictions\n{negative_prompt.strip()}")


def merge_system_prompt(
    *,
    location: InstructionLocation,
    base_system: str,
    system_prompt: str | None = None,
    default_prompt: str | None = None,
    negative_prompt: str | None = None,
) -> str:
    merged = base_system
    merged = _append_section(merged, system_prompt)
    merged = _append_section(merged, default_prompt)
    merged = _append_restrictions(merged, negative_prompt)
    merged = _append_section(merged, get_guardrails(location))
    return merged


def merge_user_message(user_prefix: str | None, runtime_user: str) -> str:
    prefix = (user_prefix or "").strip()
    runtime = runtime_user.strip()
    if not prefix:
        return runtime_user
    if not runtime:
        return prefix
    return f"{prefix}\n\n{runtime}"


async def resolve_instructions(
    db: AsyncSession,
    location: InstructionLocation,
    locale: InstructionLocale,
    *,
    build_base_system: Callable[..., str],
    system_kwargs: dict[str, Any] | None = None,
    user_prefix_override: str | None = None,
) -> ResolvedInstructions:
    layer = await get_instruction_layer(db, location, locale)
    base_system = build_base_system(**(system_kwargs or {}))

    system = merge_system_prompt(
        location=location,
        base_system=base_system,
        system_prompt=layer.system_prompt if layer else None,
        default_prompt=layer.default_prompt if layer else None,
        negative_prompt=layer.negative_prompt if layer else None,
    )

    user_prefix = user_prefix_override
    if user_prefix is None and layer and layer.user_prompt:
        user_prefix = layer.user_prompt

    parameters = merge_parameters(location, layer.parameters if layer else None)

    return ResolvedInstructions(
        system=system,
        user_prefix=user_prefix or "",
        parameters=parameters,
    )


def preview_instructions(
    *,
    location: InstructionLocation,
    locale: InstructionLocale,
    base_system: str,
    system_prompt: str | None = None,
    default_prompt: str | None = None,
    user_prompt: str | None = None,
    negative_prompt: str | None = None,
    parameters: dict[str, Any] | None = None,
) -> ResolvedInstructions:
    system = merge_system_prompt(
        location=location,
        base_system=base_system,
        system_prompt=system_prompt,
        default_prompt=default_prompt,
        negative_prompt=negative_prompt,
    )
    return ResolvedInstructions(
        system=system,
        user_prefix=(user_prompt or "").strip(),
        parameters=merge_parameters(location, parameters),
    )
