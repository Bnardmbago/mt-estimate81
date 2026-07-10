import pytest

from app.ai.schemas import FeatureItemSuggestion
from app.estimates.extraction_constraints import (
    apply_extraction_constraints,
    assess_constraint_feasibility,
    format_constraints_for_prompt,
    parse_extraction_constraints,
)


def test_parse_returns_none_when_no_constraints():
    assert parse_extraction_constraints({}, None) is None
    assert parse_extraction_constraints({"delivery_schedule": "flexible"}, None) is None
    assert parse_extraction_constraints({"client_budget": ""}, None) is None


def test_schedule_only_cap():
    constraints = parse_extraction_constraints(
        {"delivery_schedule": "within_1_3_months"},
        None,
    )
    assert constraints is not None
    assert constraints.target_working_days == 65
    assert constraints.max_hours_schedule == 520.0
    assert constraints.binding_constraint == "schedule"
    assert constraints.max_hours == 520.0


def test_budget_only_cap():
    roles = [{"name": "Engineer", "hourly_rate": 10000}]
    constraints = parse_extraction_constraints(
        {"client_budget": "1000000"},
        roles,
    )
    assert constraints is not None
    assert constraints.client_budget_jpy == 1_000_000
    assert constraints.max_labor_jpy == 650_000
    assert constraints.blended_hourly_rate_jpy == 10_000
    assert constraints.max_hours_budget == 65.0
    assert constraints.binding_constraint == "budget"
    assert constraints.max_hours == 65.0


def test_both_constraints_budget_is_tighter():
    roles = [{"name": "Engineer", "hourly_rate": 10000}]
    constraints = parse_extraction_constraints(
        {
            "client_budget": "1000000",
            "delivery_schedule": "within_1_3_months",
        },
        roles,
    )
    assert constraints is not None
    assert constraints.binding_constraint == "budget"
    assert constraints.max_hours == 65.0


def test_over_12_months_schedule_target():
    constraints = parse_extraction_constraints(
        {"delivery_schedule": "over_12_months"},
        None,
    )
    assert constraints is not None
    assert constraints.target_working_days == 520
    assert constraints.max_hours == 4160.0


def test_apply_scales_hours_when_over_cap():
    roles = [{"name": "Engineer", "hourly_rate": 10000}]
    constraints = parse_extraction_constraints({"client_budget": "1000000"}, roles)
    assert constraints is not None

    items = [
        FeatureItemSuggestion(
            name="A",
            description="",
            suggested_hours=200,
            phase="development",
            role="Engineer",
        ),
        FeatureItemSuggestion(
            name="B",
            description="",
            suggested_hours=200,
            phase="development",
            role="Engineer",
        ),
    ]
    adjusted, report = apply_extraction_constraints(items, constraints, locale="en")
    assert report["hours_scaled"] is True
    assert report["original_total_hours"] == 400.0
    assert report["adjusted_total_hours"] <= constraints.max_hours + 1
    assert report["applied_scale_factor"] == pytest.approx(65 / 400, rel=0.01)
    total = sum(item.suggested_hours for item in adjusted)
    assert total == pytest.approx(65.0, rel=0.05)


def test_apply_leaves_hours_when_under_cap():
    roles = [{"name": "Engineer", "hourly_rate": 10000}]
    constraints = parse_extraction_constraints({"client_budget": "10000000"}, roles)
    assert constraints is not None

    items = [
        FeatureItemSuggestion(
            name="A",
            description="",
            suggested_hours=40,
            phase="development",
            role="Engineer",
        ),
    ]
    adjusted, report = apply_extraction_constraints(items, constraints, locale="en")
    assert report["hours_scaled"] is False
    assert adjusted[0].suggested_hours == 40


def test_assess_requires_confirmation_when_over_cap():
    roles = [{"name": "Engineer", "hourly_rate": 10000}]
    constraints = parse_extraction_constraints({"client_budget": "1000000"}, roles)
    assert constraints is not None
    items = [
        FeatureItemSuggestion(
            name="A",
            description="",
            suggested_hours=200,
            phase="development",
            role="Engineer",
        ),
    ]
    feasibility = assess_constraint_feasibility(items, constraints)
    assert feasibility is not None
    assert feasibility.requires_confirmation is True
    assert feasibility.budget_below_minimum is True


def test_assess_no_confirmation_when_under_cap():
    roles = [{"name": "Engineer", "hourly_rate": 10000}]
    constraints = parse_extraction_constraints({"client_budget": "10000000"}, roles)
    assert constraints is not None
    items = [
        FeatureItemSuggestion(
            name="A",
            description="",
            suggested_hours=40,
            phase="development",
            role="Engineer",
        ),
    ]
    feasibility = assess_constraint_feasibility(items, constraints)
    assert feasibility is not None
    assert feasibility.requires_confirmation is False


def test_format_constraints_uses_template_placeholders():
    roles = [{"name": "Engineer", "hourly_rate": 10000}]
    constraints = parse_extraction_constraints({"client_budget": "1000000"}, roles)
    assert constraints is not None
    rendered = format_constraints_for_prompt(
        constraints,
        "en",
        template="Budget line: {budget_section} Cap: {max_hours}h",
    )
    assert "Budget line:" in rendered
    assert "Cap: 65.0h" in rendered
