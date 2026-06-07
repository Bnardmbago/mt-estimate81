import pytest

from app.calculation.engine import CalculationError, calculate_estimate
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
    assert result.nrc["labor_jpy"] == 40 * 6000 + 20 * 8000  # 400000
    assert result.nrc["contingency_jpy"] == int(result.nrc["labor_jpy"] * 0.15)
    assert result.nrc["overhead_jpy"] == int(result.nrc["labor_jpy"] * 0.10)
    assert result.nrc["setup_jpy"] == 400000
    assert result.nrc["total_jpy"] == (
        result.nrc["labor_jpy"]
        + result.nrc["setup_jpy"]
        + result.nrc["contingency_jpy"]
        + result.nrc["overhead_jpy"]
    )
    assert result.rc["monthly_total_jpy"] == 50000 + 20 * 6000


def test_unknown_role_raises():
    items = [FeatureItemInput(name="Bad", hours=10, phase="development", role="unknown")]
    with pytest.raises(CalculationError) as exc:
        calculate_estimate(items, SAMPLE_RATE_CARD, {}, "v1")
    assert "unknown" in str(exc.value).lower()
    assert exc.value.feature_item_name == "Bad"


def test_zero_hour_item():
    items = [
        FeatureItemInput(name="Placeholder", hours=0, phase="development", role="developer"),
        FeatureItemInput(name="Auth", hours=40, phase="development", role="developer"),
    ]
    result = calculate_estimate(items, SAMPLE_RATE_CARD, {}, rate_card_version_id="v1")
    assert result.total_effort_hours == 40
    assert result.total_effort_days == 5.0
    assert result.nrc["labor_jpy"] == 40 * 6000
    assert len(result.role_breakdown) == 1
    assert result.role_breakdown[0]["role"] == "developer"
    assert result.role_breakdown[0]["hours"] == 40


def test_maintenance_rc():
    items = [FeatureItemInput(name="Auth", hours=10, phase="development", role="developer")]
    maintenance = {"monthly_support_hours": 30, "support_role": "PM"}
    result = calculate_estimate(items, SAMPLE_RATE_CARD, maintenance, rate_card_version_id="v1")
    assert result.rc["maintenance_jpy"] == 30 * 8000
    assert result.rc["monthly_total_jpy"] == 50000 + 30 * 8000
    assert result.rc["annual_total_jpy"] == result.rc["monthly_total_jpy"] * 12
    assert result.first_year_total_jpy == result.nrc["total_jpy"] + result.rc["annual_total_jpy"]
