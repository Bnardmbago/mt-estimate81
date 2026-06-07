import uuid
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.exports.markdown import (
    format_currency,
    format_effort_days,
    format_hours,
    generate_markdown,
)


@pytest.fixture
def sample_estimate_with_calculation():
    feature_item = SimpleNamespace(
        sort_order=0,
        name="User login & auth",
        description="OAuth and session management",
        phase="development",
        role="developer",
        hours=40,
    )
    return SimpleNamespace(
        project_name="Portal Redesign",
        client_name="ACME Corp",
        locale="en",
        form_data={
            "nature_of_work": "Greenfield web application",
            "main_functional_needs": "User login and dashboard",
            "budget": "¥5,000,000",
        },
        extracted_data={
            "functional_requirements": ["User authentication", "Dashboard"],
            "non_functional_requirements": ["99.9% uptime"],
            "user_roles": ["Admin", "User"],
            "modules": ["Auth", "Dashboard"],
            "external_systems": ["Stripe"],
            "risks": ["Third-party API changes"],
            "gaps": ["Mobile support scope unclear"],
            "confidence_notes": "High confidence on auth module.",
        },
        feature_items=[feature_item],
        calculation_result={
            "total_effort_hours": 40,
            "total_effort_days": 5.0,
            "phase_breakdown": [
                {"phase": "development", "hours": 16.0, "percentage": 0.40},
                {"phase": "testing", "hours": 10.0, "percentage": 0.25},
            ],
            "role_breakdown": [
                {
                    "role": "developer",
                    "hours": 40,
                    "rate_jpy": 6000,
                    "cost_jpy": 240000,
                }
            ],
            "nrc": {
                "labor_jpy": 240000,
                "setup_jpy": 400000,
                "contingency_jpy": 36000,
                "overhead_jpy": 24000,
                "total_jpy": 700000,
            },
            "rc": {
                "monthly_items": [{"name": "hosting", "amount_jpy": 50000}],
                "maintenance_jpy": 120000,
                "monthly_total_jpy": 170000,
                "annual_total_jpy": 2040000,
            },
            "first_year_total_jpy": 2740000,
            "rate_card_version_id": str(uuid.uuid4()),
        },
    )


def test_format_currency():
    assert format_currency(1234567) == "¥1,234,567"
    assert format_currency(0) == "¥0"


def test_format_effort_days():
    assert format_effort_days(40) == "5"
    assert format_effort_days(60) == "7.5"


def test_format_hours():
    assert format_hours(40) == "40"
    assert format_hours(7.5) == "7.5"


def test_markdown_export_contains_nrc_total(sample_estimate_with_calculation):
    md = generate_markdown(sample_estimate_with_calculation, locale="en")
    assert "First Year Total" in md
    assert "¥2,740,000" in md
    assert "¥" in md


def test_markdown_export_contains_effort_summary(sample_estimate_with_calculation):
    md = generate_markdown(sample_estimate_with_calculation, locale="en")
    assert "Total Person-Hours" in md
    assert "Total Effort Days" in md
    assert "| 40 | 5 |" in md


def test_markdown_export_ja_locale(sample_estimate_with_calculation):
    md = generate_markdown(
        sample_estimate_with_calculation,
        locale="ja",
        generated_at=datetime(2026, 6, 7),
    )
    assert "初年度合計" in md
    assert "2026年6月7日" in md
    assert "¥2,740,000" in md


def test_markdown_export_all_report_sections(sample_estimate_with_calculation):
    md = generate_markdown(sample_estimate_with_calculation, locale="en")
    sections = [
        "Project Summary",
        "Input Assumptions",
        "Extracted Requirements",
        "Feature Line Items",
        "Effort Summary",
        "Phase Breakdown",
        "Role Breakdown",
        "NRC Breakdown",
        "RC Breakdown",
        "First Year Total",
        "Risks & Gaps",
        "AI Confidence Notes",
        "Rate Card Reference",
    ]
    for section in sections:
        assert section in md


def test_markdown_export_feature_effort_days(sample_estimate_with_calculation):
    md = generate_markdown(sample_estimate_with_calculation, locale="en")
    assert "User login & auth" in md
    assert "| User login & auth | OAuth and session management | development | developer | 40 | 5 |" in md


def test_markdown_export_rate_card_reference(sample_estimate_with_calculation):
    md = generate_markdown(
        sample_estimate_with_calculation,
        locale="en",
        rate_card_name="2026 Standard Rates",
        rate_card_version_number=2,
    )
    assert "2026 Standard Rates" in md
    assert "| Version | 2 |" in md
