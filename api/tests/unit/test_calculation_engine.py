import pytest

from app.calculation.development_approach import DevelopmentApproach
from app.calculation.engine import CalculationError, calculate_estimate, role_personnel_count
from app.calculation.schemas import FeatureItemInput, RateCardSettings

SAMPLE_RATE_CARD = RateCardSettings(
    roles=[
        {"name": "PM", "hourly_rate_jpy": 8000},
        {"name": "developer", "hourly_rate_jpy": 6000},
        {"name": "QA", "hourly_rate_jpy": 5000},
    ],
    phases=[
        {"name": "requirement", "percentage": 0.10},
        {"name": "design", "percentage": 0.15},
        {"name": "development", "percentage": 0.40},
        {"name": "testing", "percentage": 0.25},
        {"name": "deployment", "percentage": 0.10},
    ],
    development_approach="traditional",
    contingency_rate=0.15,
    overhead_rate=0.10,
    monthly_rc_items=[{"name": "hosting", "amount_jpy": 50000}],
    setup_costs={"infrastructure_jpy": 300000, "tooling_jpy": 100000, "third_party_jpy": 0},
    productivity={"hours_per_feature_default": 40},
    tax_rate=0.10,
)


def test_basic_nrc_calculation():
    items = [
        FeatureItemInput(name="Auth", hours=40, phase="development", role="developer"),
        FeatureItemInput(name="PM work", hours=20, phase="requirement", role="PM"),
    ]
    maintenance = {"monthly_support_hours": 20, "support_role": "developer"}
    result = calculate_estimate(items, SAMPLE_RATE_CARD, maintenance, rate_card_version_id="v1")
    assert result.total_effort_hours == 60
    assert result.total_effort_days == 7.5  # 60 / 8
    assert result.estimated_duration_days == 7.5
    assert result.recommended_team_size == 3
    assert result.nrc["labor_jpy"] == 25 * 6000 + 20 * 8000 + 15 * 5000
    assert result.nrc["contingency_jpy"] == int(result.nrc["labor_jpy"] * 0.15)
    assert result.nrc["overhead_jpy"] == int(result.nrc["labor_jpy"] * 0.10)
    assert result.nrc["setup_jpy"] == 400000
    assert len(result.nrc["setup_items"]) == 3
    assert result.nrc["total_jpy"] == (
        result.nrc["labor_jpy"]
        + result.nrc["setup_jpy"]
        + result.nrc["contingency_jpy"]
        + result.nrc["overhead_jpy"]
    )
    assert result.rc["monthly_total_jpy"] == 50000 + 20 * 6000
    assert len(result.nrc_line_items) >= 2
    assert len(result.rc_line_items) >= 2
    assert all("category" in row for row in result.rc_line_items)
    assert all(row["personnel_count"] >= 1 for row in result.role_breakdown)


def test_role_personnel_count_minimum_one():
    assert role_personnel_count(40, estimated_duration_days=5, total_days=5) == 1


def test_role_personnel_count_scales_with_hours():
    assert role_personnel_count(160, estimated_duration_days=10, total_days=20) == 2


def test_role_breakdown_includes_personnel_count():
    items = [
        FeatureItemInput(name="Auth", hours=40, phase="development", role="developer"),
        FeatureItemInput(name="PM work", hours=20, phase="requirement", role="PM"),
    ]
    result = calculate_estimate(items, SAMPLE_RATE_CARD, {}, rate_card_version_id="v1")
    assert [row["role"] for row in result.role_breakdown] == ["PM", "developer", "QA"]
    for row in result.role_breakdown:
        assert "personnel_count" in row
        if row["hours"] > 0:
            assert row["personnel_count"] >= 1
        else:
            assert row["personnel_count"] == 0


def test_role_breakdown_lists_all_rate_card_roles():
    items = [FeatureItemInput(name="Auth", hours=40, phase="development", role="developer")]
    result = calculate_estimate(items, SAMPLE_RATE_CARD, {}, rate_card_version_id="v1")
    assert len(result.role_breakdown) == 3
    qa_row = next(row for row in result.role_breakdown if row["role"] == "QA")
    assert qa_row["hours"] == 10.0
    assert qa_row["cost_jpy"] == 10 * 5000


def test_cost_drivers_passed_through():
    items = [FeatureItemInput(name="Auth", hours=40, phase="development", role="developer")]
    drivers = [{"name": "OAuth", "impact_jpy": 100000}]
    result = calculate_estimate(
        items,
        SAMPLE_RATE_CARD,
        {},
        rate_card_version_id="v1",
        cost_drivers=drivers,
    )
    assert result.cost_drivers == drivers


def test_unknown_role_raises():
    items = [FeatureItemInput(name="Bad", hours=10, phase="development", role="unknown")]
    with pytest.raises(CalculationError) as exc:
        calculate_estimate(items, SAMPLE_RATE_CARD, {}, "v1")
    assert "unknown" in str(exc.value).lower()
    assert exc.value.feature_item_name == "Bad"


def test_combined_designer_developer_role_maps_to_developer():
    items = [
        FeatureItemInput(name="UI Design", hours=40, phase="design-phase", role="designer/developer"),
        FeatureItemInput(name="Build", hours=40, phase="development", role="developer"),
    ]
    result = calculate_estimate(items, SAMPLE_RATE_CARD, {}, rate_card_version_id="v1")
    dev_row = next(row for row in result.role_breakdown if row["role"] == "developer")
    assert dev_row["hours"] > 0
    assert result.total_effort_hours == 80


def test_zero_hour_item():
    items = [
        FeatureItemInput(name="Placeholder", hours=0, phase="development", role="developer"),
        FeatureItemInput(name="Auth", hours=40, phase="development", role="developer"),
    ]
    result = calculate_estimate(items, SAMPLE_RATE_CARD, {}, rate_card_version_id="v1")
    assert result.total_effort_hours == 40
    assert result.total_effort_days == 5.0
    assert result.nrc["labor_jpy"] == int(26 * 6000 + 10 * 5000 + 4 * 8000)
    assert len(result.role_breakdown) == 3
    dev_row = next(row for row in result.role_breakdown if row["role"] == "developer")
    assert dev_row["hours"] == 26


def test_maintenance_rc():
    items = [FeatureItemInput(name="Auth", hours=10, phase="development", role="developer")]
    maintenance = {"monthly_support_hours": 30, "support_role": "PM"}
    result = calculate_estimate(items, SAMPLE_RATE_CARD, maintenance, rate_card_version_id="v1")
    assert result.rc["maintenance_jpy"] == 30 * 8000
    assert result.rc["monthly_total_jpy"] == 50000 + 30 * 8000
    assert result.rc["annual_total_jpy"] == result.rc["monthly_total_jpy"] * 12
    assert result.first_year_total_jpy == result.nrc["total_jpy"] + result.rc["annual_total_jpy"]


def test_calculate_includes_gantt_when_start_date_provided():
    from datetime import date

    items = [
        FeatureItemInput(name="PM work", hours=20, phase="requirement", role="PM"),
        FeatureItemInput(name="Auth", hours=40, phase="development", role="developer"),
    ]
    result = calculate_estimate(
        items,
        SAMPLE_RATE_CARD,
        {},
        rate_card_version_id="v1",
        project_start_date=date(2026, 6, 9),
    )
    assert result.gantt["project_start_date"] == "2026-06-09"
    assert len(result.gantt["tasks"]) == 2
    assert result.estimated_duration_days == float(result.gantt["total_working_days"])


def test_discount_zero_rate_is_no_op():
    items = [
        FeatureItemInput(name="Auth", hours=40, phase="development", role="developer"),
        FeatureItemInput(name="PM work", hours=20, phase="requirement", role="PM"),
    ]
    maintenance = {"monthly_support_hours": 20, "support_role": "developer"}
    baseline = calculate_estimate(items, SAMPLE_RATE_CARD, maintenance, rate_card_version_id="v1")
    unchanged = calculate_estimate(
        items,
        SAMPLE_RATE_CARD,
        maintenance,
        rate_card_version_id="v1",
        discount_rate=0.0,
    )

    assert unchanged.model_dump() == baseline.model_dump()


def test_discount_scales_nrc_items_and_preserves_rc():
    items = [
        FeatureItemInput(name="Auth", hours=40, phase="development", role="developer"),
        FeatureItemInput(name="PM work", hours=20, phase="requirement", role="PM"),
    ]
    maintenance = {"monthly_support_hours": 20, "support_role": "developer"}
    baseline = calculate_estimate(items, SAMPLE_RATE_CARD, maintenance, rate_card_version_id="v1")
    discounted = calculate_estimate(
        items,
        SAMPLE_RATE_CARD,
        maintenance,
        rate_card_version_id="v1",
        discount_rate=0.30,
    )

    multiplier = 0.7
    assert discounted.nrc["labor_jpy"] == int(round(baseline.nrc["labor_jpy"] * multiplier))
    assert discounted.nrc["setup_jpy"] == int(round(baseline.nrc["setup_jpy"] * multiplier))
    assert discounted.nrc["contingency_jpy"] == int(round(baseline.nrc["contingency_jpy"] * multiplier))
    assert discounted.nrc["overhead_jpy"] == int(round(baseline.nrc["overhead_jpy"] * multiplier))
    assert discounted.nrc["total_jpy"] == (
        discounted.nrc["labor_jpy"]
        + discounted.nrc["setup_jpy"]
        + discounted.nrc["contingency_jpy"]
        + discounted.nrc["overhead_jpy"]
    )
    assert discounted.rc["monthly_total_jpy"] == baseline.rc["monthly_total_jpy"]
    assert discounted.rc["annual_total_jpy"] == baseline.rc["annual_total_jpy"]
    assert discounted.first_year_total_jpy == discounted.nrc["total_jpy"] + discounted.rc["annual_total_jpy"]

    for row in discounted.role_breakdown:
        assert row["cost_jpy"] == int(round(row["hours"] * row["rate_jpy"]))


def test_ai_assisted_development_approach_reduces_effort_and_cost():
    ai_card = SAMPLE_RATE_CARD.model_copy(update={"development_approach": DevelopmentApproach.AI_ASSISTED})
    items = [
        FeatureItemInput(name="Auth", hours=40, phase="development", role="developer"),
        FeatureItemInput(name="PM work", hours=20, phase="requirement", role="PM"),
    ]
    baseline = calculate_estimate(items, SAMPLE_RATE_CARD, {}, rate_card_version_id="v1")
    adjusted = calculate_estimate(items, ai_card, {}, rate_card_version_id="v1")

    assert adjusted.development_approach == "ai_assisted"
    assert adjusted.development_approach_effort_multiplier == 0.75
    assert adjusted.total_effort_hours == 45.0
    assert adjusted.nrc["labor_jpy"] == int(18.75 * 6000 + 11.25 * 5000 + 15 * 8000)
    assert adjusted.nrc["labor_jpy"] < baseline.nrc["labor_jpy"]
    assert adjusted.recommended_team_size <= baseline.recommended_team_size
