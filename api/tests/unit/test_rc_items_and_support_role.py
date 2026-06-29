from app.calculation.engine import calculate_estimate
from app.calculation.role_allocation import resolve_support_role_hourly_rate
from app.calculation.schemas import FeatureItemInput, RateCardSettings
from app.rate_cards.rc_items import allocate_rc_item_amounts, ensure_standard_monthly_rc_items
from tests.unit.test_calculation_engine import SAMPLE_RATE_CARD


def test_resolve_support_role_hourly_rate_matches_title_case_role():
    role_rates = {"Developer": 8000, "Project Manager": 12000}
    role_name, hourly = resolve_support_role_hourly_rate(role_rates, "developer")
    assert role_name == "Developer"
    assert hourly == 8000


def test_resolve_support_role_hourly_rate_falls_back_to_developer_alias():
    role_rates = {"Backend Developer": 8500, "Project Manager": 12000}
    role_name, hourly = resolve_support_role_hourly_rate(role_rates, "developer")
    assert role_name == "Backend Developer"
    assert hourly == 8500


def test_allocate_rc_item_amounts_splits_monitoring_and_support():
    allocations = allocate_rc_item_amounts(
        {"name": "Monitoring and Support", "amount": 50000}
    )
    assert allocations == [
        ("system_monitoring", 25000),
        ("maintenance_support", 25000),
    ]


def test_ensure_standard_monthly_rc_items_merges_into_five_rows():
    merged = ensure_standard_monthly_rc_items(
        [
            {"name": "Hosting", "amount": 100000},
            {"name": "Monitoring and Support", "amount": 50000},
            {"name": "Security Operations", "amount": 75000},
            {"name": "SaaS Subscriptions", "amount": 60000},
        ]
    )

    assert len(merged) == 5
    by_category = {item["category"]: item["amount"] for item in merged}
    assert by_category["cloud_infrastructure"] == 160000
    assert by_category["system_monitoring"] == 25000
    assert by_category["maintenance_support"] == 25000
    assert by_category["security"] == 75000
    assert by_category["backup"] == 0


def test_maintenance_jpy_uses_title_case_developer_rate():
    rate_card = RateCardSettings(
        **SAMPLE_RATE_CARD.model_dump()
        | {
            "roles": [
                {"name": "Developer", "hourly_rate": 8000, "daily_rate": 64000},
                {"name": "PM", "hourly_rate": 12000, "daily_rate": 96000},
                {"name": "QA", "hourly_rate": 6500, "daily_rate": 52000},
            ]
        }
    )
    items = [FeatureItemInput(name="Login", hours=40, phase="development", role="developer")]
    maintenance = {"monthly_support_hours": 20}

    result = calculate_estimate(items, rate_card, maintenance, rate_card_version_id="v1")

    assert result.rc["maintenance_jpy"] == 160000
