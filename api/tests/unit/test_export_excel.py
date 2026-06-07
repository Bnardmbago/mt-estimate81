import uuid
from io import BytesIO
from types import SimpleNamespace

import pytest
from openpyxl import load_workbook

from app.exports.excel import generate_excel, SHEET_NAMES


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


def _load_workbook_from_bytes(content: bytes):
    return load_workbook(BytesIO(content), data_only=False)


def test_excel_workbook_has_seven_sheets(sample_estimate_with_calculation):
    content = generate_excel(sample_estimate_with_calculation, locale="en")
    wb = _load_workbook_from_bytes(content)

    expected_sheets = list(SHEET_NAMES["en"].values())
    assert wb.sheetnames == expected_sheets
    assert len(wb.sheetnames) == 7


def test_excel_nrc_total_on_nrc_detail_sheet(sample_estimate_with_calculation):
    content = generate_excel(sample_estimate_with_calculation, locale="en")
    wb = _load_workbook_from_bytes(content)

    nrc_sheet = wb[SHEET_NAMES["en"]["nrc"]]
    nrc_total_label = nrc_sheet["A5"].value
    nrc_total_value = nrc_sheet["B5"].value

    assert nrc_total_label == "NRC Total"
    assert nrc_total_value == 700000


def test_excel_role_breakdown_uses_formulas(sample_estimate_with_calculation):
    content = generate_excel(sample_estimate_with_calculation, locale="en")
    wb = _load_workbook_from_bytes(content)

    role_sheet = wb[SHEET_NAMES["en"]["role"]]
    cost_formula = role_sheet["D2"].value

    assert cost_formula == "=B2*C2"


def test_excel_summary_contains_project_name(sample_estimate_with_calculation):
    content = generate_excel(sample_estimate_with_calculation, locale="en")
    wb = _load_workbook_from_bytes(content)

    summary_sheet = wb[SHEET_NAMES["en"]["summary"]]
    assert summary_sheet["B1"].value == "Portal Redesign"
    assert summary_sheet["B2"].value == "ACME Corp"


def test_excel_ja_locale_sheet_names(sample_estimate_with_calculation):
    content = generate_excel(sample_estimate_with_calculation, locale="ja")
    wb = _load_workbook_from_bytes(content)

    assert wb.sheetnames == list(SHEET_NAMES["ja"].values())
