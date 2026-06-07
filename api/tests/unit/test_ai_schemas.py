import pytest
from pydantic import ValidationError

from app.ai.schemas import ExtractedRequirements, FeatureItemSuggestion


def test_valid_extraction_payload():
    data = ExtractedRequirements(
        functional_requirements=["Login"],
        non_functional_requirements=["99.9% uptime"],
        user_roles=["Admin"],
        modules=["Auth"],
        external_systems=[],
        risks=["Tight deadline"],
        gaps=["Budget unclear"],
        confidence_notes="High confidence on auth scope",
        feature_items=[
            FeatureItemSuggestion(
                name="Login",
                description="OAuth login",
                suggested_hours=40,
                phase="development",
                role="developer",
            )
        ],
        maintenance_assumptions={"monthly_support_hours": 20, "notes": "Business hours support"},
    )
    assert len(data.feature_items) == 1


def test_invalid_feature_item_rejected():
    with pytest.raises(ValidationError):
        FeatureItemSuggestion(name="", description="", suggested_hours=-1, phase="dev", role="dev")
