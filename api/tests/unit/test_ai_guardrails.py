from app.ai.guardrails import LOCATION_GUARDRAILS, get_guardrails
from app.models.ai_instruction_layer import INSTRUCTION_LOCATIONS


def test_each_location_has_guardrails_with_json_schema_language():
    for location in INSTRUCTION_LOCATIONS:
        guardrails = get_guardrails(location)
        assert guardrails
        assert "valid JSON" in guardrails
        assert location in LOCATION_GUARDRAILS
