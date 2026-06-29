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

    pm = next(role for role in DEFAULT_RATE_CARD_SETTINGS["roles"] if role["name"] == "PM")
    developer = next(role for role in DEFAULT_RATE_CARD_SETTINGS["roles"] if role["name"] == "developer")
    qa = next(role for role in DEFAULT_RATE_CARD_SETTINGS["roles"] if role["name"] == "QA")
    assert pm["hourly_rate"] == 12000
    assert developer["hourly_rate"] == 8000
    assert qa["hourly_rate"] == 6500


def test_patch_settings_standard_roles_for_region_updates_system_card():
    settings = {
        "region": "philippines",
        "currency": "JPY",
        "roles": [
            {"name": "PM", "hourly_rate": 8000, "daily_rate": 64000},
            {"name": "developer", "hourly_rate": 6000, "daily_rate": 48000},
            {"name": "QA", "hourly_rate": 5000, "daily_rate": 40000},
            {"name": "DevOps", "hourly_rate": 7500, "daily_rate": 60000},
        ],
    }
    patched = patch_settings_standard_roles_for_region(settings, "japan", currency="JPY")

    assert patched["region"] == "japan"
    assert patched["currency"] == "JPY"
    pm = next(role for role in patched["roles"] if role["name"] == "PM")
    devops = next(role for role in patched["roles"] if role["name"] == "DevOps")
    assert pm["hourly_rate"] == 12000
    assert devops["hourly_rate"] == 7500
