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
    assert any("10,000" in item for item in hints["monthly_suggestions"])
    assert any("security" in item.casefold() for item in hints["monthly_suggestions"])
    assert "Data migration" in hints["setup_suggestions"]
    assert "support retainer" in hints["monthly_suggestions"]
    assert hints["signals"]["complexity_notes"] == "Enterprise operations"
