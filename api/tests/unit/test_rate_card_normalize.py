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
    assert normalized["monthly_rc_items"][0]["amount"] == 50000
