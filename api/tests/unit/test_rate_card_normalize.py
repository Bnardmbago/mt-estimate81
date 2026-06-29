import pytest

from app.rate_cards.normalize import normalize_settings_dict


def test_normalize_settings_applies_daily_rates():
    raw = {
        "roles": [{"name": "developer", "hourly_rate_jpy": 6000}],
        "setup_costs": {"infrastructure_jpy": 100000, "tooling_jpy": 0, "third_party_jpy": 0},
    }
    normalized = normalize_settings_dict(raw)
    assert normalized["roles"][0]["hourly_rate"] == 6000
    assert normalized["roles"][0]["daily_rate"] == 48000
    assert normalized["currency"] == "JPY"
    assert normalized["region"] == "japan"
    assert normalized["setup_cost_items"][0]["name"] == "Infrastructure"
    assert normalized["setup_cost_items"][0]["amount"] == 100000


def test_normalize_settings_preserves_custom_daily_rate():
    raw = {
        "roles": [{"name": "developer", "hourly_rate": 6000, "daily_rate": 55000}],
    }
    normalized = normalize_settings_dict(raw)
    assert normalized["roles"][0]["daily_rate"] == 55000


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
    frontend = next(role for role in normalized["roles"] if role["name"] == "Frontend Developer")
    backend = next(role for role in normalized["roles"] if role["name"] == "Backend Developer")
    pm = next(role for role in normalized["roles"] if role["name"] == "Project Manager")
    assert frontend["hourly_rate"] == 8500
    assert backend["hourly_rate"] == 8500
    assert pm["hourly_rate"] == 12000


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
