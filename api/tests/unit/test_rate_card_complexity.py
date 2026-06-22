from app.rate_cards.complexity import score_project_complexity


def test_low_complexity_simple_project():
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

    assert profile.level == "low"
    assert profile.feature_count == 2
    assert profile.overall_score < 35
    assert profile.phase_guidance["development"] >= 0.40


def test_medium_complexity_project():
    profile = score_project_complexity(
        feature_items=[{"name": f"Feature {index}", "hours": 20} for index in range(8)],
        extracted_data={
            "external_systems": ["Stripe", "SendGrid"],
            "non_functional_requirements": ["99.9% uptime", "SSO"],
            "modules": ["Billing", "Notifications", "Admin"],
            "risks": ["Legacy data format"],
            "gaps": [],
            "cost_drivers": [{"name": "Payment gateway", "impact_jpy": 80000}],
        },
        form_data={
            "data_complexity": "moderate",
            "ui_complexity": "moderate",
            "integrations": "Stripe, SendGrid",
        },
    )

    assert profile.level == "medium"
    assert profile.integration_count >= 2
    assert profile.non_functional_count == 2
    assert profile.nrc_rc_guidance["relative_scale"] == "moderate"


def test_negative_cost_driver_impact_does_not_fail_validation():
    profile = score_project_complexity(
        feature_items=[{"name": "Feature", "hours": 20}],
        extracted_data={
            "external_systems": [],
            "non_functional_requirements": [],
            "modules": [],
            "risks": [],
            "gaps": [],
            "cost_drivers": [{"name": "Reuse existing platform", "impact_jpy": -100000}],
        },
        form_data={},
    )

    assert profile.cost_driver_impact_jpy == 0
    assert profile.cost_driver_count == 1


def test_high_complexity_project():
    profile = score_project_complexity(
        feature_items=[{"name": f"Feature {index}", "hours": 40} for index in range(25)],
        extracted_data={
            "external_systems": ["SAP", "Salesforce", "Okta", "Snowflake", "Kafka"],
            "non_functional_requirements": [
                "SOC2",
                "HIPAA",
                "Multi-region DR",
                "Sub-second latency",
                "Audit logging",
            ],
            "modules": [f"Module {index}" for index in range(8)],
            "risks": ["Regulatory review", "Data residency"],
            "gaps": ["Unknown SLA"],
            "cost_drivers": [
                {"name": "Enterprise licenses", "impact_jpy": 500000},
                {"name": "Security audit", "impact_jpy": 300000},
            ],
        },
        form_data={
            "data_complexity": "high",
            "ui_complexity": "high",
            "integrations": "SAP; Salesforce; Okta",
        },
    )

    assert profile.level == "high"
    assert profile.overall_score > 65
    assert profile.phase_guidance["testing"] >= 0.25
    assert "Security audit" in profile.nrc_rc_guidance["setup_categories"]
