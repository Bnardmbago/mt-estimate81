import pytest

from app.rate_cards.normalize import normalize_settings_dict


def test_normalize_settings_applies_daily_rates():
    raw = {
        "roles": [{"name": "developer", "hourly_rate_jpy": 6000}],
        "setup_costs": {"infrastructure_jpy": 100000, "tooling_jpy": 0, "third_party_jpy": 0},
    }
    normalized = normalize_settings_dict(raw)
    engineer = next(role for role in normalized["roles"] if role["name"] == "Engineer")
    assert engineer["hourly_rate"] == 6000
    assert engineer["daily_rate"] == 48000
    assert normalized["currency"] == "JPY"
    assert normalized["region"] == "japan"
    assert normalized["setup_cost_items"][0]["name"] == "Infrastructure"
    assert normalized["setup_cost_items"][0]["amount"] == 100000


def test_normalize_settings_preserves_custom_daily_rate():
    raw = {
        "roles": [{"name": "developer", "hourly_rate": 6000, "daily_rate": 55000}],
    }
    normalized = normalize_settings_dict(raw)
    engineer = next(role for role in normalized["roles"] if role["name"] == "Engineer")
    assert engineer["hourly_rate"] == 6000
    assert engineer["daily_rate"] == 48000


def test_normalize_settings_preserves_setup_cost_items():
    raw = {
        "roles": [],
        "setup_cost_items": [{"name": "Licenses", "amount": 50000}],
        "region": "philippines",
        "currency": "PHP",
    }
    normalized = normalize_settings_dict(raw)
    assert normalized["setup_cost_items"] == [{"name": "Licenses", "amount": 50000}]
    assert normalized["region"] == "philippines"
    assert normalized["currency"] == "PHP"


def test_normalize_settings_migrates_legacy_line_items():
    raw = {
        "roles": [],
        "monthly_rc_items": [{"name": "hosting", "amount_jpy": 50000}],
    }
    normalized = normalize_settings_dict(raw)
    assert len(normalized["monthly_rc_items"]) == 5
    cloud = next(
        item for item in normalized["monthly_rc_items"] if item["category"] == "cloud_infrastructure"
    )
    assert cloud["amount"] == 50000


def test_normalize_settings_flexible_mode_preserves_custom_rows():
    raw = {
        "roles": [],
        "cost_breakdown_mode": "flexible",
        "monthly_rc_items": [
            {"name": "Custom hosting", "amount": 80000, "service_description": "AWS ECS"},
            {"name": "API gateway", "amount": 15000},
        ],
    }
    normalized = normalize_settings_dict(raw)
    assert len(normalized["monthly_rc_items"]) == 2
    assert normalized["monthly_rc_items"][0]["name"] == "Custom hosting"
    assert normalized["monthly_rc_items"][0]["service_description"] == "AWS ECS"


def test_normalize_settings_defaults_region_and_currency_without_legacy_jpy():
    normalized = normalize_settings_dict({"roles": []})
    assert normalized["region"] == "japan"
    assert normalized["currency"] == "JPY"


def test_normalize_settings_default_maintenance_monthly_jpy():
    normalized = normalize_settings_dict({"roles": []})
    assert normalized["default_maintenance_monthly_jpy"] == 0

    raw = {"roles": [], "default_maintenance_monthly_jpy": 120000}
    normalized = normalize_settings_dict(raw)
    assert normalized["default_maintenance_monthly_jpy"] == 120000


def test_normalize_settings_consolidates_ai_roles_to_standard_four():
    raw = {
        "region": "japan",
        "currency": "JPY",
        "roles": [
            {"name": "Project Manager", "hourly_rate": 12000, "daily_rate": 96000},
            {"name": "Developer", "hourly_rate": 8000, "daily_rate": 64000},
            {"name": "QA Engineer", "hourly_rate": 6500, "daily_rate": 52000},
            {"name": "UX Designer", "hourly_rate": 7500, "daily_rate": 60000},
            {"name": "Business Analyst", "hourly_rate": 9000, "daily_rate": 72000},
            {"name": "DevOps Engineer", "hourly_rate": 9500, "daily_rate": 76000},
            {"name": "Senior Engineer", "hourly_rate": 10000, "daily_rate": 80000},
            {"name": "Full Stack Engineer", "hourly_rate": 9000, "daily_rate": 72000},
        ],
    }
    normalized = normalize_settings_dict(raw)
    assert len(normalized["roles"]) == 4
    names = [role["name"] for role in normalized["roles"]]
    assert names == ["Tech Lead", "Senior Engineer", "Full Stack Engineer", "Engineer"]
    tech_lead = next(role for role in normalized["roles"] if role["name"] == "Tech Lead")
    engineer = next(role for role in normalized["roles"] if role["name"] == "Engineer")
    assert tech_lead["hourly_rate"] == 12000
    assert engineer["hourly_rate"] == 9500


def test_normalize_settings_raises_jpy_frontend_backend_from_php_conversion():
    raw = {
        "region": "philippines",
        "currency": "JPY",
        "roles": [
            {"name": "Frontend Developer", "hourly_rate": 1719, "daily_rate": 13752},
            {"name": "Backend Developer", "hourly_rate": 1719, "daily_rate": 13752},
            {"name": "Project Manager", "hourly_rate": 12000, "daily_rate": 96000},
        ],
    }
    normalized = normalize_settings_dict(raw)
    assert len(normalized["roles"]) == 4
    tech_lead = next(role for role in normalized["roles"] if role["name"] == "Tech Lead")
    full_stack = next(role for role in normalized["roles"] if role["name"] == "Full Stack Engineer")
    engineer = next(role for role in normalized["roles"] if role["name"] == "Engineer")
    assert tech_lead["hourly_rate"] == 12000
    assert full_stack["hourly_rate"] == 8500
    assert engineer["hourly_rate"] == 650


def test_normalize_settings_preserves_rc_category_and_description():
    raw = {
        "roles": [],
        "monthly_rc_items": [
            {
                "name": "Cloud infrastructure",
                "amount": 50000,
                "category": "cloud_infrastructure",
                "service_description": "Server & database usage",
            }
        ],
    }
    normalized = normalize_settings_dict(raw)
    item = normalized["monthly_rc_items"][0]
    assert item["category"] == "cloud_infrastructure"
    assert item["service_description"] == "Server & database usage"
