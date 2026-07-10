from dataclasses import dataclass, replace
from typing import Any, Callable, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.ai_instruction_config import effective_prompt_fields, get_instruction_layer, merge_parameters
from app.ai.extraction_constraint_prompts import (
    get_default_constraint_negative_prompt,
    get_default_constraint_system_prompt,
    get_default_constraint_user_prompt_template,
)
from app.ai.guardrails import get_guardrails
from app.models.ai_instruction_layer import InstructionLocation, InstructionLocale


@dataclass(frozen=True)
class ResolvedInstructions:
    system: str
    user_prefix: str
    parameters: dict[str, int | float]
    constraints_section_template: str | None = None


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
    effective = effective_prompt_fields(location, locale, layer)

    if layer and layer.system_prompt and str(layer.system_prompt).strip():
        system_prompt = str(layer.system_prompt).strip()
    else:
        system_prompt = build_base_system(**(system_kwargs or {}))

    system = merge_system_prompt(
        location=location,
        base_system="",
        system_prompt=system_prompt,
        default_prompt=effective.get("default_prompt"),
        negative_prompt=effective.get("negative_prompt"),
    )

    user_prefix = user_prefix_override
    if user_prefix is None:
        stored_user = effective.get("user_prompt")
        user_prefix = stored_user if stored_user else ""

    parameters = merge_parameters(location, layer.parameters if layer else None)

    return ResolvedInstructions(
        system=system,
        user_prefix=user_prefix or "",
        parameters=parameters,
    )


def _effective_text(stored: str | None, default: str | None) -> str | None:
    if stored is not None and stored.strip():
        return stored.strip()
    if default is not None and default.strip():
        return default.strip()
    return None


async def resolve_client_constraint_prompts(
    db: AsyncSession,
    locale: InstructionLocale,
) -> dict[str, str | None]:
    layer = await get_instruction_layer(db, "extraction_client_constraints", locale)
    return {
        "system_prompt": _effective_text(
            layer.system_prompt if layer else None,
            get_default_constraint_system_prompt(locale),
        ),
        "default_prompt": _effective_text(
            layer.default_prompt if layer else None,
            get_guardrails("extraction_client_constraints"),
        ),
        "user_prompt": _effective_text(
            layer.user_prompt if layer else None,
            get_default_constraint_user_prompt_template(locale),
        ),
        "negative_prompt": _effective_text(
            layer.negative_prompt if layer else None,
            get_default_constraint_negative_prompt(locale),
        ),
    }


def merge_client_constraint_instructions(
    instructions: ResolvedInstructions,
    constraint_prompts: dict[str, str | None],
) -> ResolvedInstructions:
    system = instructions.system
    system = _append_section(system, constraint_prompts.get("system_prompt"))
    system = _append_section(system, constraint_prompts.get("default_prompt"))
    system = _append_restrictions(system, constraint_prompts.get("negative_prompt"))
    return replace(
        instructions,
        system=system,
        constraints_section_template=constraint_prompts.get("user_prompt"),
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
