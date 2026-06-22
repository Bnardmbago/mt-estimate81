from app.calculation.engine import calculate_estimate
from app.calculation.role_allocation import (
    allocate_role_hours_from_phases,
    resolve_feature_item_role,
)
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


def test_allocate_pm_hours_from_requirement_phase():
    items = [
        FeatureItemInput(name="Dev", hours=390, phase="development", role="developer"),
        FeatureItemInput(name="Test", hours=60, phase="testing", role="QA"),
    ]
    role_hours = {"developer": 390.0, "QA": 60.0}
    allocated = allocate_role_hours_from_phases(items, SAMPLE_RATE_CARD, role_hours, 450.0, 1.0)

    assert allocated["PM"] == 45.0
    assert allocated["QA"] == 112.5
    assert allocated["developer"] == 292.5
    assert sum(allocated.values()) == 450.0


def test_allocate_pm_and_testing_from_single_developer_feature():
    items = [
        FeatureItemInput(name="Dev", hours=40, phase="development", role="developer"),
    ]
    role_hours = {"developer": 40.0}
    allocated = allocate_role_hours_from_phases(items, SAMPLE_RATE_CARD, role_hours, 40.0, 1.0)

    assert allocated["PM"] == 4.0
    assert allocated["QA"] == 10.0
    assert allocated["developer"] == 26.0


def test_calculate_estimate_allocates_pm_when_missing_from_features():
    items = [
        FeatureItemInput(name="Dev", hours=390, phase="development", role="developer"),
        FeatureItemInput(name="Test", hours=60, phase="testing", role="QA"),
    ]
    result = calculate_estimate(items, SAMPLE_RATE_CARD, {}, rate_card_version_id="v1")

    pm_row = next(row for row in result.role_breakdown if row["role"] == "PM")
    assert pm_row["hours"] == 45.0
    assert pm_row["cost_jpy"] == 45 * 8000
    assert result.nrc["labor_jpy"] == int(292.5 * 6000 + 112.5 * 5000 + 45 * 8000)


def test_resolve_feature_item_role_maps_combined_designer_developer():
    role_rates = {"PM": 1, "developer": 1, "QA": 1}
    assert (
        resolve_feature_item_role("designer/developer", role_rates, phase="design-phase")
        == "developer"
    )


def test_resolve_feature_item_role_uses_phase_fallback_for_designer():
    role_rates = {"PM": 1, "developer": 1, "QA": 1}
    assert resolve_feature_item_role("UI Designer", role_rates, phase="design") == "developer"
