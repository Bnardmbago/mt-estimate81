import pytest
from pydantic import ValidationError

from app.ai.schemas import (
    CostDriverSuggestion,
    ExtractedRequirements,
    FeatureItemSuggestion,
    accuracy_level_from_score,
)


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
        confidence_score=85,
        confidence_factors=["Clear scope"],
        missing_inputs=["Mobile requirements"],
        recommendations=["Clarify mobile scope"],
        estimation_warnings=["Timeline aggressive"],
        assumption_risks=["Budget may change"],
        estimate_exclusions=["Native mobile apps"],
        estimate_type="Web Application",
        cost_drivers=[CostDriverSuggestion(name="OAuth", impact_jpy=120000)],
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
    assert data.accuracy_level == "high"


def test_accuracy_level_derived_from_score():
    assert accuracy_level_from_score(85) == "high"
    assert accuracy_level_from_score(65) == "medium"
    assert accuracy_level_from_score(40) == "low"


def test_confidence_score_bounds():
    with pytest.raises(ValidationError):
        ExtractedRequirements(
            functional_requirements=[],
            non_functional_requirements=[],
            user_roles=[],
            modules=[],
            external_systems=[],
            risks=[],
            gaps=[],
            confidence_notes="",
            feature_items=[],
            maintenance_assumptions={"monthly_support_hours": 0},
            confidence_score=101,
        )


def test_invalid_feature_item_rejected():
    with pytest.raises(ValidationError):
        FeatureItemSuggestion(name="", description="", suggested_hours=-1, phase="dev", role="dev")
