from datetime import datetime
from typing import Any, Literal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_instruction_layer import (
    INSTRUCTION_LOCALES,
    INSTRUCTION_LOCATIONS,
    AiInstructionLayer,
    InstructionLocale,
    InstructionLocation,
)

MAX_PROMPT_LENGTH = 32_000

PARAMETER_BOUNDS: dict[str, tuple[int | float, int | float]] = {
    "max_tokens": (256, 16384),
    "temperature": (0.0, 1.0),
    "timeout_seconds": (30, 180),
    "max_document_chars": (5_000, 80_000),
}

DEFAULT_PARAMETERS: dict[str, int | float] = {
    "max_tokens": 8192,
    "temperature": 0.0,
    "timeout_seconds": 90,
    "max_document_chars": 80_000,
}

EXTRACTION_DEFAULT_MAX_DOCUMENT_CHARS = 40_000


def get_prompt_defaults(
    location: InstructionLocation,
    locale: InstructionLocale,
) -> dict[str, str | None]:
    from app.admin.ai_instruction_preview import build_preview_base_system
    from app.ai.extraction_constraint_prompts import (
        get_default_constraint_negative_prompt,
        get_default_constraint_system_prompt,
        get_default_constraint_user_prompt_template,
    )
    from app.ai.guardrails import get_guardrails

    if location == "extraction_client_constraints":
        return {
            "system_prompt": get_default_constraint_system_prompt(locale),
            "default_prompt": get_guardrails(location),
            "user_prompt": get_default_constraint_user_prompt_template(locale),
            "negative_prompt": get_default_constraint_negative_prompt(locale),
        }

    return {
        "system_prompt": build_preview_base_system(location, locale),
        "default_prompt": get_guardrails(location),
        "user_prompt": None,
        "negative_prompt": None,
    }


def effective_prompt_fields(
    location: InstructionLocation,
    locale: InstructionLocale,
    layer: AiInstructionLayer | None,
) -> dict[str, str | None]:
    defaults = get_prompt_defaults(location, locale)

    def pick(field: str) -> str | None:
        stored = getattr(layer, field, None) if layer else None
        if stored is not None and str(stored).strip():
            return str(stored).strip()
        return defaults.get(field)

    return {
        "system_prompt": pick("system_prompt"),
        "default_prompt": pick("default_prompt"),
        "user_prompt": pick("user_prompt"),
        "negative_prompt": pick("negative_prompt"),
    }


def is_valid_location(value: str) -> bool:
    return value in INSTRUCTION_LOCATIONS


def is_valid_locale(value: str) -> bool:
    return value in INSTRUCTION_LOCALES


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    if len(stripped) > MAX_PROMPT_LENGTH:
        raise ValueError(f"Prompt text must be at most {MAX_PROMPT_LENGTH} characters")
    return stripped


def validate_parameters(
    parameters: dict[str, Any] | None,
    *,
    location: InstructionLocation,
) -> dict[str, int | float] | None:
    if parameters is None:
        return None

    if not isinstance(parameters, dict):
        raise ValueError("parameters must be an object")

    validated: dict[str, int | float] = {}
    for key, value in parameters.items():
        if key not in PARAMETER_BOUNDS:
            raise ValueError(f"Unknown parameter: {key}")
        if not isinstance(value, (int, float)):
            raise ValueError(f"Parameter {key} must be a number")
        low, high = PARAMETER_BOUNDS[key]
        if value < low or value > high:
            raise ValueError(f"Parameter {key} must be between {low} and {high}")
        if key in ("max_tokens", "timeout_seconds", "max_document_chars"):
            validated[key] = int(value)
        else:
            validated[key] = float(value)

    return validated or None


def get_default_parameters(
    location: InstructionLocation,
    *,
    purpose_defaults: dict[str, int | float] | None = None,
) -> dict[str, int | float]:
    if purpose_defaults is not None:
        params = dict(DEFAULT_PARAMETERS)
        params.update(purpose_defaults)
        return params
    params = dict(DEFAULT_PARAMETERS)
    if location == "extraction":
        params["max_document_chars"] = EXTRACTION_DEFAULT_MAX_DOCUMENT_CHARS
        params["timeout_seconds"] = 120
    if location in ("proposal_assessment", "proposal_body", "proposal_poc"):
        # Fallback when purpose settings are unavailable (preview without DB).
        from app.proposals.generation_presets import (
            DEFAULT_PROPOSAL_AI_SETTINGS,
            LOCATION_TO_PART,
            budget_parameters,
            purpose_for_part,
        )

        part = LOCATION_TO_PART[location]
        purpose = purpose_for_part(DEFAULT_PROPOSAL_AI_SETTINGS, part)
        params.update(budget_parameters(purpose))
    return params


def merge_parameters(
    location: InstructionLocation,
    stored: dict[str, Any] | None,
    *,
    purpose_defaults: dict[str, int | float] | None = None,
) -> dict[str, int | float]:
    merged = get_default_parameters(location, purpose_defaults=purpose_defaults)
    if stored:
        validated = validate_parameters(stored, location=location)
        if validated:
            merged.update(validated)
    return merged


async def list_instruction_layers(db: AsyncSession) -> list[AiInstructionLayer]:
    result = await db.execute(
        select(AiInstructionLayer).order_by(AiInstructionLayer.location, AiInstructionLayer.locale)
    )
    return list(result.scalars().all())


async def get_instruction_layer(
    db: AsyncSession,
    location: InstructionLocation,
    locale: InstructionLocale,
) -> AiInstructionLayer | None:
    result = await db.execute(
        select(AiInstructionLayer).where(
            AiInstructionLayer.location == location,
            AiInstructionLayer.locale == locale,
        )
    )
    return result.scalar_one_or_none()


async def upsert_instruction_layer(
    db: AsyncSession,
    *,
    location: InstructionLocation,
    locale: InstructionLocale,
    system_prompt: str | None = None,
    default_prompt: str | None = None,
    user_prompt: str | None = None,
    negative_prompt: str | None = None,
    parameters: dict[str, Any] | None = None,
    clear_system_prompt: bool = False,
    clear_default_prompt: bool = False,
    clear_user_prompt: bool = False,
    clear_negative_prompt: bool = False,
    clear_parameters: bool = False,
) -> AiInstructionLayer:
    row = await get_instruction_layer(db, location, locale)
    if row is None:
        row = AiInstructionLayer(location=location, locale=locale)
        db.add(row)

    if clear_system_prompt:
        row.system_prompt = None
    elif system_prompt is not None:
        row.system_prompt = _normalize_optional_text(system_prompt)

    if clear_default_prompt:
        row.default_prompt = None
    elif default_prompt is not None:
        row.default_prompt = _normalize_optional_text(default_prompt)

    if clear_user_prompt:
        row.user_prompt = None
    elif user_prompt is not None:
        row.user_prompt = _normalize_optional_text(user_prompt)

    if clear_negative_prompt:
        row.negative_prompt = None
    elif negative_prompt is not None:
        row.negative_prompt = _normalize_optional_text(negative_prompt)

    if clear_parameters:
        row.parameters = None
    elif parameters is not None:
        row.parameters = validate_parameters(parameters, location=location)

    row.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(row)
    return row


async def reset_instruction_layer(
    db: AsyncSession,
    location: InstructionLocation,
    locale: InstructionLocale,
) -> None:
    await db.execute(
        delete(AiInstructionLayer).where(
            AiInstructionLayer.location == location,
            AiInstructionLayer.locale == locale,
        )
    )
    await db.commit()
