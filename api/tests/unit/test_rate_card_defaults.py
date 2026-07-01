from app.rate_cards.defaults import DEFAULT_RATE_CARD_SETTINGS, DEFAULT_REGION
from app.rate_cards.regional_profiles import (
    default_roles_for_region,
    patch_settings_standard_roles_for_region,
)


def test_default_region_is_japan():
    assert DEFAULT_REGION == "japan"
    assert DEFAULT_RATE_CARD_SETTINGS["region"] == "japan"
    assert DEFAULT_RATE_CARD_SETTINGS["currency"] == "JPY"


def test_default_rate_card_roles_match_japan_standard():
    expected = default_roles_for_region("japan")
    assert DEFAULT_RATE_CARD_SETTINGS["roles"] == expected
    assert len(DEFAULT_RATE_CARD_SETTINGS["roles"]) == 4

    tech_lead = next(role for role in DEFAULT_RATE_CARD_SETTINGS["roles"] if role["name"] == "Tech Lead")
    senior = next(
        role for role in DEFAULT_RATE_CARD_SETTINGS["roles"] if role["name"] == "Senior Engineer"
    )
    full_stack = next(
        role for role in DEFAULT_RATE_CARD_SETTINGS["roles"] if role["name"] == "Full Stack Engineer"
    )
    engineer = next(role for role in DEFAULT_RATE_CARD_SETTINGS["roles"] if role["name"] == "Engineer")
    assert tech_lead["hourly_rate"] == 10500
    assert senior["hourly_rate"] == 10000
    assert full_stack["hourly_rate"] == 9000
    assert engineer["hourly_rate"] == 8000


def test_default_development_approach_is_ai_assisted():
    assert DEFAULT_RATE_CARD_SETTINGS["development_approach"] == "ai_assisted"


def test_default_cost_breakdown_mode_is_flexible():
    assert DEFAULT_RATE_CARD_SETTINGS["cost_breakdown_mode"] == "flexible"


def test_patch_settings_standard_roles_for_region_updates_system_card():
    settings = {
        "region": "philippines",
        "currency": "JPY",
        "roles": [
            {"name": "Tech Lead", "hourly_rate": 8000, "daily_rate": 64000},
            {"name": "Engineer", "hourly_rate": 6000, "daily_rate": 48000},
            {"name": "DevOps", "hourly_rate": 7500, "daily_rate": 60000},
        ],
    }
    patched = patch_settings_standard_roles_for_region(settings, "japan", currency="JPY")

    assert patched["region"] == "japan"
    assert patched["currency"] == "JPY"
    tech_lead = next(role for role in patched["roles"] if role["name"] == "Tech Lead")
    devops = next(role for role in patched["roles"] if role["name"] == "DevOps")
    assert tech_lead["hourly_rate"] == 10500
    assert devops["hourly_rate"] == 7500
