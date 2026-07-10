import pytest

from app.admin.ai_instruction_config import get_prompt_defaults, validate_parameters
from app.ai.guardrails import get_guardrails
from app.ai.instruction_resolver import (
    ResolvedInstructions,
    merge_client_constraint_instructions,
    merge_system_prompt,
    merge_user_message,
    preview_instructions,
)
from app.models.ai_instruction_layer import INSTRUCTION_LOCATIONS, INSTRUCTION_LOCALES


def test_merge_system_prompt_without_layers_returns_base_only():
    base = "Base system prompt."
    merged = merge_system_prompt(
        location="extraction",
        base_system=base,
    )
    assert merged == base


def test_merge_system_prompt_appends_layers_in_order():
    merged = merge_system_prompt(
        location="ai_spec_assistant",
        base_system="",
        system_prompt="Admin system.",
        default_prompt="Admin default.",
        negative_prompt="Do not invent fields.",
    )
    assert merged.index("Admin system.") < merged.index("Admin default.")
    assert merged.index("Admin default.") < merged.index("## Restrictions")
    assert merged.index("## Restrictions") < merged.index("Do not invent fields.")


def test_prompt_defaults_include_system_and_guardrails_for_each_location():
    for location in INSTRUCTION_LOCATIONS:
        for locale in INSTRUCTION_LOCALES:
            defaults = get_prompt_defaults(location, locale)
            assert defaults["system_prompt"]
            assert defaults["default_prompt"] == get_guardrails(location)


def test_get_prompt_defaults_extraction_client_constraints():
    defaults = get_prompt_defaults("extraction_client_constraints", "en")
    assert defaults["system_prompt"]
    assert defaults["user_prompt"]
    assert "{max_hours}" in defaults["user_prompt"]
    assert defaults["negative_prompt"]


def test_merge_user_message_prefix_and_runtime():
    merged = merge_user_message("Admin prefix.", "Runtime content.")
    assert merged == "Admin prefix.\n\nRuntime content."


def test_merge_user_message_blank_prefix_returns_runtime():
    assert merge_user_message(None, "Runtime only.") == "Runtime only."
    assert merge_user_message("", "Runtime only.") == "Runtime only."


def test_validate_parameters_rejects_out_of_bounds():
    with pytest.raises(ValueError, match="max_tokens"):
        validate_parameters({"max_tokens": 100}, location="extraction")

    with pytest.raises(ValueError, match="temperature"):
        validate_parameters({"temperature": 2.0}, location="extraction")

    with pytest.raises(ValueError, match="timeout_seconds"):
        validate_parameters({"timeout_seconds": 10}, location="extraction")

    with pytest.raises(ValueError, match="max_document_chars"):
        validate_parameters({"max_document_chars": 1000}, location="extraction")


def test_validate_parameters_accepts_valid_values():
    result = validate_parameters(
        {
            "max_tokens": 4096,
            "temperature": 0.5,
            "timeout_seconds": 60,
            "max_document_chars": 50000,
        },
        location="extraction",
    )
    assert result == {
        "max_tokens": 4096,
        "temperature": 0.5,
        "timeout_seconds": 60,
        "max_document_chars": 50000,
    }


def test_preview_instructions_uses_extraction_document_defaults():
    resolved = preview_instructions(
        location="extraction",
        locale="en",
        base_system="Base.",
    )
    assert resolved.parameters["max_document_chars"] == 40_000
    assert resolved.parameters["timeout_seconds"] == 120


def test_preview_instructions_merges_custom_parameters():
    resolved = preview_instructions(
        location="ai_spec_assistant",
        locale="en",
        base_system="Base.",
        parameters={"max_tokens": 2048, "temperature": 0.2},
    )
    assert resolved.parameters["max_tokens"] == 2048
    assert resolved.parameters["temperature"] == 0.2


def test_merge_client_constraint_instructions_adds_template():
    base = ResolvedInstructions(
        system="Extraction base.",
        user_prefix="",
        parameters={"max_tokens": 8192, "temperature": 0.0, "timeout_seconds": 120, "max_document_chars": 40000},
    )
    merged = merge_client_constraint_instructions(
        base,
        {
            "system_prompt": "Estimate full scope.",
            "default_prompt": None,
            "user_prompt": "Template {max_hours}",
            "negative_prompt": "Do not pre-shrink.",
        },
    )
    assert "Estimate full scope." in merged.system
    assert "## Restrictions" in merged.system
    assert merged.constraints_section_template == "Template {max_hours}"
