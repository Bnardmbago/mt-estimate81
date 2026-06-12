from datetime import datetime

import pytest

from app.exports.markdown import (
    format_currency,
    format_effort_days,
    format_hours,
    generate_markdown,
)
from tests.unit.export_fixtures import sample_report_context


@pytest.fixture
def report_context():
    return sample_report_context()


def test_format_currency():
    assert format_currency(1234567) == "¥1,234,567"
    assert format_currency(0) == "¥0"


def test_format_effort_days():
    assert format_effort_days(40) == "5"
    assert format_effort_days(60) == "7.5"


def test_format_hours():
    assert format_hours(40) == "40"
    assert format_hours(7.5) == "7.5"


def test_markdown_export_contains_first_year_total(report_context):
    md = generate_markdown(report_context)
    assert "Total Development Cost (deployment and Delivery acceptance)" in md
    assert "First Year Total Cost" in md
    assert "Developers" in md
    assert "¥2,740,000" in md
    assert "¥" in md


def test_markdown_export_contains_effort_summary(report_context):
    md = generate_markdown(report_context)
    assert "Total Person-Hours" in md
    assert "Total Effort Days" in md
    assert "| 40 | 5 |" in md


def test_markdown_export_ja_locale():
    ctx = sample_report_context(locale="ja", generated_at=datetime(2026, 6, 7))
    md = generate_markdown(ctx)
    assert "初年度合計コスト" in md
    assert "2026年6月7日" in md
    assert "¥2,740,000" in md


def test_markdown_export_all_report_sections(report_context):
    md = generate_markdown(report_context)
    sections = [
        "Project Summary",
        "Executive Cost Summary",
        "Key Assumptions",
        "Input Assumptions",
        "Extracted Requirements",
        "Feature Line Items",
        "Effort Summary",
        "Phase Breakdown",
        "Project Timeline (Gantt)",
        "Role Breakdown",
        "NRC Breakdown (Detailed)",
        "RC Breakdown (Detailed)",
        "Cost Drivers",
        "Risks & Gaps",
        "Estimate Exclusions",
        "AI Confidence Notes",
        "Rate Card Reference",
        "Approval",
    ]
    for section in sections:
        assert section in md


def test_markdown_export_feature_effort_days(report_context):
    md = generate_markdown(report_context)
    assert "User login & auth" in md
    assert "| User login & auth | OAuth and session management | development | developer | 40 | 5 |" in md


def test_markdown_export_rate_card_reference():
    ctx = sample_report_context(
        rate_card_name="2026 Standard Rates",
        rate_card_version_number=2,
    )
    md = generate_markdown(ctx)
    assert "2026 Standard Rates" in md
    assert "| Version | 2 |" in md
