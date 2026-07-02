from typing import Any, Literal

from app.ai.prompts import (
    build_form_fields_system_prompt,
    build_rate_card_section_system_prompt,
    build_rate_card_system_prompt,
    build_system_prompt,
)
from app.models.ai_instruction_layer import InstructionLocation

InstructionLocale = Literal["en", "ja"]

SAMPLE_FIELD_METADATA = [
    {
        "key": "nature_of_work",
        "type": "textarea",
        "required": True,
        "label": "Nature of work",
    }
]


def build_preview_base_system(
    location: InstructionLocation,
    locale: InstructionLocale,
) -> str:
    if location == "ai_spec_assistant":
        return build_form_fields_system_prompt(locale, SAMPLE_FIELD_METADATA)
    if location == "extraction":
        return build_system_prompt(locale)
    if location == "rate_card_generation":
        return build_rate_card_system_prompt(locale, has_extraction_context=False)
    if location == "rate_card_section":
        return build_rate_card_section_system_prompt(locale, "roles", free_form=False)
    raise ValueError(f"Unknown location: {location}")


def layer_to_dict(row: Any | None) -> dict[str, Any]:
    if row is None:
        return {
            "system_prompt": None,
            "default_prompt": None,
            "user_prompt": None,
            "negative_prompt": None,
            "parameters": None,
            "updated_at": None,
        }
    return {
        "system_prompt": row.system_prompt,
        "default_prompt": row.default_prompt,
        "user_prompt": row.user_prompt,
        "negative_prompt": row.negative_prompt,
        "parameters": row.parameters,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
