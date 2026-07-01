import pytest
from pydantic import ValidationError

from app.ai.constants import MAX_AI_USER_PROMPT_CHARS
from app.schemas.estimate import EstimateAiSuggestFormRequest


def test_ai_suggest_form_request_accepts_prompt_up_to_max_length():
    prompt = "x" * MAX_AI_USER_PROMPT_CHARS
    request = EstimateAiSuggestFormRequest(prompt=prompt)
    assert request.prompt == prompt


def test_ai_suggest_form_request_rejects_prompt_over_max_length():
    with pytest.raises(ValidationError):
        EstimateAiSuggestFormRequest(prompt="x" * (MAX_AI_USER_PROMPT_CHARS + 1))
