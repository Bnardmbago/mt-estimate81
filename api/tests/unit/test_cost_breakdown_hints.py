from app.rate_cards.cost_breakdown_hints import build_cost_breakdown_hints


def test_build_cost_breakdown_hints_maps_form_and_complexity_signals():
    hints = build_cost_breakdown_hints(
        {
            "integrations": "Stripe, Salesforce",
            "maintenance_support": "12-month warranty with SLA",
            "payment_needed": "yes",
            "expected_user_count": "10,000",
            "non_functional_needs": "99.9% uptime and security compliance",
            "technology_preferences": "AWS cloud SaaS stack",
        },
        {
            "external_systems": ["HubSpot"],
        },
        {
            "nrc_rc_guidance": {
                "setup_categories": ["Data migration"],
                "monthly_categories": ["support retainer"],
                "notes": "Enterprise operations",
            }
        },
    )

    assert "Stripe" in hints["signals"]["integrations"][0] or "Stripe" in str(
        hints["signals"]["integrations"]
    )
    assert any("integration" in item.casefold() for item in hints["setup_suggestions"])
    assert any("maintenance" in item.casefold() for item in hints["monthly_suggestions"])
    assert any("payment" in item.casefold() for item in hints["setup_suggestions"])
    assert any("10000" in item for item in hints["monthly_suggestions"])
    assert any("security" in item.casefold() for item in hints["monthly_suggestions"])
    assert "Data migration" in hints["setup_suggestions"]
    assert "support retainer" in hints["monthly_suggestions"]
    assert hints["signals"]["complexity_notes"] == "Enterprise operations"


def test_build_cost_breakdown_hints_skips_payment_when_not_needed():
    hints = build_cost_breakdown_hints({"payment_needed": "none"}, None, None)
    assert "payment_needed" not in hints["signals"]
    assert not any("payment" in item.casefold() for item in hints["setup_suggestions"])

    legacy_hints = build_cost_breakdown_hints({"payment_needed": "undecided"}, None, None)
    assert "payment_needed" not in legacy_hints["signals"]


def test_build_cost_breakdown_hints_prefers_concurrent_users_for_infra():
    hints = build_cost_breakdown_hints(
        {"expected_user_count": "1000", "concurrent_users": "250"},
        None,
        None,
    )
    assert hints["signals"]["infra_user_count"] == 1000
    assert any("1000 users" in item for item in hints["monthly_suggestions"])

    peak_hints = build_cost_breakdown_hints(
        {"expected_user_count": "100", "concurrent_users": "500"},
        None,
        None,
    )
    assert peak_hints["signals"]["infra_user_count"] == 500
    assert peak_hints["signals"]["concurrent_users"] == "500"


def test_build_cost_breakdown_hints_new_spec_fields():
    hints = build_cost_breakdown_hints(
        {
            "auth_complexity": "sso",
            "data_migration_needed": "yes_major",
            "compliance_level": "regulated",
            "integration_count": "4",
        },
        None,
        None,
    )
    assert hints["signals"]["auth_complexity"] == "sso"
    assert hints["signals"]["integration_count"] == 4
    assert any("Authentication" in item for item in hints["setup_suggestions"])
    assert any("migration" in item.casefold() for item in hints["setup_suggestions"])
    assert any("Compliance" in item for item in hints["setup_suggestions"])
