from app.rate_cards.maintenance import (
    apply_default_maintenance_to_settings,
    derive_default_maintenance_monthly_jpy,
)


def test_derive_default_maintenance_monthly_jpy():
    settings = {
        "roles": [
            {"name": "PM", "hourly_rate_jpy": 8000},
            {"name": "developer", "hourly_rate_jpy": 6000},
        ],
    }
    assumptions = {"monthly_support_hours": 20, "support_role": "developer"}
    assert derive_default_maintenance_monthly_jpy(assumptions, settings) == 120_000


def test_derive_default_maintenance_uses_support_role():
    settings = {"roles": [{"name": "PM", "hourly_rate_jpy": 8000}]}
    assumptions = {"monthly_support_hours": 10, "support_role": "PM"}
    assert derive_default_maintenance_monthly_jpy(assumptions, settings) == 80_000


def test_apply_default_maintenance_to_settings():
    settings = {
        "roles": [{"name": "developer", "hourly_rate_jpy": 5000}],
        "monthly_rc_items": [{"name": "hosting", "amount": 30000}],
    }
    updated = apply_default_maintenance_to_settings(
        settings,
        {"monthly_support_hours": 12, "support_role": "developer"},
    )
    assert updated["default_maintenance_monthly_jpy"] == 60_000
    assert updated["monthly_rc_items"] == settings["monthly_rc_items"]
