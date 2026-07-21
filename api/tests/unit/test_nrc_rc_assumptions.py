from app.estimates.nrc_rc_assumptions import (
    derive_nrc_rc_assumptions,
    estimate_labor_jpy,
    prefer_rate_card_nrc_rc_after_extract,
    resolve_nrc_rc_assumptions,
)
from app.rate_cards.complexity import score_project_complexity


def _low_complexity_profile() -> dict:
    profile = score_project_complexity(
        feature_items=[
            {"name": "Login", "hours": 16, "phase": "development", "role": "developer"},
            {"name": "Dashboard", "hours": 24, "phase": "development", "role": "developer"},
        ],
        extracted_data={
            "external_systems": [],
            "non_functional_requirements": [],
            "modules": ["Auth"],
            "risks": [],
            "gaps": [],
            "cost_drivers": [],
        },
        form_data={"data_complexity": "low", "ui_complexity": "low"},
    )
    return profile.model_dump()


def test_derive_low_complexity_near_zero_defaults():
    assumptions = derive_nrc_rc_assumptions(
        complexity_profile=_low_complexity_profile(),
        form_data={"data_complexity": "low", "ui_complexity": "low"},
        extracted_data={"external_systems": []},
        labor_jpy=estimate_labor_jpy(
            [
                {"name": "Login", "hours": 16},
                {"name": "Dashboard", "hours": 24},
            ]
        ),
    )

    setup_total = sum(item["amount"] for item in assumptions["setup_cost_items"])
    monthly_total = sum(item["amount"] for item in assumptions["monthly_rc_items"])

    assert assumptions["complexity_level"] == "low"
    assert assumptions["source"] == "derived"
    assert setup_total <= 100_000
    assert monthly_total <= 15_000


def test_derive_high_complexity_uses_higher_baseline():
    profile = score_project_complexity(
        feature_items=[{"name": f"Feature {index}", "hours": 40} for index in range(25)],
        extracted_data={
            "external_systems": ["SAP", "Salesforce", "Okta", "Snowflake", "Kafka"],
            "non_functional_requirements": ["SOC2", "HIPAA", "Multi-region DR"],
            "modules": [f"Module {index}" for index in range(8)],
            "risks": ["Regulatory review"],
            "gaps": [],
            "cost_drivers": [],
        },
        form_data={"data_complexity": "high", "ui_complexity": "high"},
    )
    assumptions = derive_nrc_rc_assumptions(
        complexity_profile=profile.model_dump(),
        form_data={"data_complexity": "high"},
        extracted_data=profile.model_dump(),
    )

    setup_total = sum(item["amount"] for item in assumptions["setup_cost_items"])
    monthly_total = sum(item["amount"] for item in assumptions["monthly_rc_items"])

    assert assumptions["complexity_level"] == "high"
    assert setup_total >= 300_000
    assert monthly_total >= 50_000


def test_integration_hint_increases_setup_for_payment():
    profile = _low_complexity_profile()
    without = derive_nrc_rc_assumptions(
        complexity_profile=profile,
        form_data={"data_complexity": "low"},
        extracted_data={"external_systems": []},
    )
    with_payment = derive_nrc_rc_assumptions(
        complexity_profile=profile,
        form_data={"data_complexity": "low", "payment_needed": "yes"},
        extracted_data={"external_systems": []},
    )

    setup_without = sum(item["amount"] for item in without["setup_cost_items"])
    setup_with = sum(item["amount"] for item in with_payment["setup_cost_items"])
    assert setup_with > setup_without


def test_resolve_prefers_stored_assumptions():
    from types import SimpleNamespace

    estimate = SimpleNamespace(
        nrc_rc_assumptions={
            "setup_cost_items": [{"name": "Custom setup", "amount": 12345}],
            "monthly_rc_items": [{"name": "Custom monthly", "amount": 678}],
            "source": "manual",
            "complexity_level": "low",
        },
        extracted_data=None,
        form_data={},
        feature_items=[],
        locale="ja",
        status="review",
    )
    resolved = resolve_nrc_rc_assumptions(estimate)
    assert resolved["source"] == "manual"
    assert resolved["setup_cost_items"][0]["amount"] == 12345


def test_prefer_rate_card_nrc_rc_after_extract_uses_card_over_derived():
    """Re-extract must pick up rate-card NRC/RC edits, not keep complexity tiers."""
    derived = derive_nrc_rc_assumptions(
        complexity_profile=_low_complexity_profile(),
        form_data={"data_complexity": "low"},
        extracted_data={"external_systems": []},
        labor_jpy=50_000,
    )
    rate_card_settings = {
        "setup_cost_items": [
            {"name": "SharePoint Integration", "amount": 1_000_000},
            {"name": "AI Model Training", "amount": 1_200_000},
        ],
        "monthly_rc_items": [
            {"name": "Cloud Hosting", "amount": 100_000, "category": "cloud_infrastructure"},
            {"name": "AI API Usage", "amount": 50_000},
        ],
    }
    preferred = prefer_rate_card_nrc_rc_after_extract(
        derived=derived,
        rate_card_settings=rate_card_settings,
        complexity_level="medium",
    )
    assert preferred["source"] == "rate_card"
    assert preferred["complexity_level"] == "medium"
    assert [item["name"] for item in preferred["setup_cost_items"]] == [
        "SharePoint Integration",
        "AI Model Training",
    ]
    assert preferred["setup_cost_items"][0]["amount"] == 1_000_000
    assert preferred["monthly_rc_items"][0]["amount"] == 100_000


def test_prefer_rate_card_nrc_rc_keeps_derived_when_card_has_no_cost_items():
    derived = derive_nrc_rc_assumptions(
        complexity_profile=_low_complexity_profile(),
        form_data={"data_complexity": "low"},
        extracted_data={"external_systems": []},
    )
    preferred = prefer_rate_card_nrc_rc_after_extract(
        derived=derived,
        rate_card_settings={"roles": [{"name": "Engineer", "hourly_rate": 8000}], "setup_cost_items": [], "monthly_rc_items": []},
        complexity_level="low",
    )
    assert preferred is derived
    assert preferred["source"] == "derived"
