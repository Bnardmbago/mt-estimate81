import pytest

from app.estimates.budget_comparison import build_budget_comparison
from app.estimates.delivery_schedule import (
    build_delivery_schedule_advisory,
    delivery_schedule_target_working_days,
    resolve_timeline_staffing,
)
from app.estimates.questionnaire_validation import missing_questionnaire_fields_for_calculation


def test_delivery_schedule_target_working_days():
    assert delivery_schedule_target_working_days("asap") == 45
    assert delivery_schedule_target_working_days("flexible") is None
    assert delivery_schedule_target_working_days("over_12_months") == 520
    assert delivery_schedule_target_working_days("within_3_6_months") == 130


def test_resolve_timeline_staffing_blank_defaults_to_natural():
    mode, target = resolve_timeline_staffing(
        {"delivery_schedule": "within_3_6_months"}
    )
    assert mode == "natural"
    assert target == 130

    mode_blank, target_blank = resolve_timeline_staffing({})
    assert mode_blank == "natural"
    assert target_blank is None


def test_resolve_timeline_staffing_match_schedule():
    mode, target = resolve_timeline_staffing(
        {
            "delivery_schedule": "within_3_6_months",
            "timeline_planning": "match_schedule",
        }
    )
    assert mode == "match_schedule"
    assert target == 130


def test_resolve_timeline_staffing_match_without_target_falls_back():
    mode, target = resolve_timeline_staffing(
        {
            "delivery_schedule": "flexible",
            "timeline_planning": "match_schedule",
        }
    )
    assert mode == "natural"
    assert target is None


def test_resolve_timeline_staffing_fastest_parallel():
    mode, target = resolve_timeline_staffing(
        {
            "delivery_schedule": "within_1_3_months",
            "timeline_planning": "fastest_parallel",
        }
    )
    assert mode == "natural"
    assert target == 65


def test_build_delivery_schedule_advisory_over_band():
    advisory = build_delivery_schedule_advisory("within_1_3_months", 120)
    assert advisory["delivery_schedule_status"] == "over_band"
    assert advisory["target_working_days"] == 65


def test_build_budget_comparison_statuses():
    under = build_budget_comparison("5000000", 4000000)
    assert under is not None
    assert under["status"] == "under"

    over = build_budget_comparison("3000000", 4000000)
    assert over is not None
    assert over["status"] == "over"

    aligned = build_budget_comparison("4000000", 4100000)
    assert aligned is not None
    assert aligned["status"] == "aligned"


def test_missing_questionnaire_fields_for_calculation():
    assert missing_questionnaire_fields_for_calculation(
        has_documents=False,
        form_data={},
    ) == ["scope_signal", "data_complexity", "ui_complexity"]

    missing = missing_questionnaire_fields_for_calculation(
        has_documents=False,
        form_data={
            "required_features": "Login",
            "data_complexity": "low",
            "ui_complexity": "medium",
        },
    )
    assert missing == []


def test_missing_questionnaire_fields_for_contact_user():
    assert missing_questionnaire_fields_for_calculation(
        has_documents=False,
        form_data={},
        contact_user=True,
    ) == ["scope_signal"]

    missing = missing_questionnaire_fields_for_calculation(
        has_documents=False,
        form_data={"required_features": "Login"},
        contact_user=True,
    )
    assert missing == []
