import pytest

from app.estimates.budget_comparison import build_budget_comparison
from app.estimates.delivery_schedule import (
    build_delivery_schedule_advisory,
    delivery_schedule_target_working_days,
)
from app.estimates.questionnaire_validation import missing_questionnaire_fields_for_calculation


def test_delivery_schedule_target_working_days():
    assert delivery_schedule_target_working_days("asap") == 45
    assert delivery_schedule_target_working_days("flexible") is None
    assert delivery_schedule_target_working_days("over_12_months") == 520


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
