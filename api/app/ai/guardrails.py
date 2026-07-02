from app.models.ai_instruction_layer import InstructionLocation

JSON_SCHEMA_GUARDRAIL = (
    "Return valid JSON matching the required schema exactly. "
    "Do not include markdown fences, commentary, or extra keys outside the schema."
)

LOCATION_GUARDRAILS: dict[InstructionLocation, str] = {
    "ai_spec_assistant": (
        f"{JSON_SCHEMA_GUARDRAIL}\n"
        "Populate only specification fields from the provided field definitions. "
        "Do not populate or modify header/client questionnaire fields. "
        "For select fields, use exactly one allowed option value from the field definitions."
    ),
    "extraction": (
        f"{JSON_SCHEMA_GUARDRAIL}\n"
        "Suggested hours must be positive numbers. "
        "Use only roles and phases from the provided rate card when assigning feature items. "
        "Each feature item role must exactly match one rate card role name."
    ),
    "rate_card_generation": (
        f"{JSON_SCHEMA_GUARDRAIL}\n"
        "Phase percentages must sum to 1.0. "
        "Recommend exactly four roles: Tech Lead, Senior Engineer, Full Stack Engineer, and Engineer. "
        "All monetary amounts must be in JPY."
    ),
    "rate_card_section": (
        f"{JSON_SCHEMA_GUARDRAIL}\n"
        "Do not duplicate items that already exist in the current section (match by name, case-insensitive). "
        "Return only data for the requested section."
    ),
}


def get_guardrails(location: InstructionLocation) -> str:
    return LOCATION_GUARDRAILS[location]
