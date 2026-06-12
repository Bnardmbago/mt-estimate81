import pytest

from app.rate_cards.normalize import normalize_settings_dict


def test_normalize_settings_applies_daily_rates():
    raw = {
        "roles": [{"name": "developer", "hourly_rate_jpy": 6000}],
        "setup_costs": {"infrastructure_jpy": 100000, "tooling_jpy": 0, "third_party_jpy": 0},
    }
    normalized = normalize_settings_dict(raw)
    assert normalized["roles"][0]["daily_rate_jpy"] == 48000
    assert normalized["setup_cost_items"][0]["name"] == "Infrastructure"


def test_normalize_settings_preserves_custom_daily_rate():
    raw = {
        "roles": [{"name": "developer", "hourly_rate_jpy": 6000, "daily_rate_jpy": 55000}],
    }
    normalized = normalize_settings_dict(raw)
    assert normalized["roles"][0]["daily_rate_jpy"] == 55000


def test_normalize_settings_preserves_setup_cost_items():
    raw = {
        "roles": [],
        "setup_cost_items": [{"name": "Licenses", "amount_jpy": 50000}],
    }
    normalized = normalize_settings_dict(raw)
    assert normalized["setup_cost_items"] == [{"name": "Licenses", "amount_jpy": 50000}]
