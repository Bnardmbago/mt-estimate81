import uuid
from datetime import datetime
from types import SimpleNamespace

import pytest

try:
    from weasyprint import HTML as _WeasyprintHTML
except OSError:
    pytest.skip("WeasyPrint system libraries not available", allow_module_level=True)
else:
    del _WeasyprintHTML

from app.exports.pdf import generate_pdf


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


def test_pdf_export_starts_with_pdf_magic_bytes(sample_estimate_with_calculation):
    content = generate_pdf(sample_estimate_with_calculation, locale="en")
    assert content.startswith(b"%PDF")


def test_pdf_export_ja_locale(sample_estimate_with_calculation):
    content = generate_pdf(
        sample_estimate_with_calculation,
        locale="ja",
        generated_at=datetime(2026, 6, 7),
    )
    assert content.startswith(b"%PDF")
    assert len(content) > 1000
