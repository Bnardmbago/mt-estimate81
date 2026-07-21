from datetime import datetime

import pytest

from app.exports.markdown import (
    format_currency,
    format_currency_yen,
    format_effort_days,
    format_hours,
    format_person_days,
    format_person_months,
    generate_markdown,
)
from tests.unit.export_fixtures import sample_estimate_with_discount, sample_report_context


@pytest.fixture
def report_context():
    return sample_report_context()


def test_format_currency():
    assert format_currency(1234567) == "¥1,234,567"
    assert format_currency(0) == "¥0"
    assert format_currency(1234.6) == "¥1,235"


def test_format_currency_yen():
    assert format_currency_yen(1234567) == "1,234,567円"
    assert format_currency_yen(0) == "0円"


def test_format_person_days():
    assert format_person_days(5) == "5"
    assert format_person_days(7.5) == "7.5"


def test_format_person_months():
    assert format_person_months(2) == "2"
    assert format_person_months(1.25) == "1.25"


def test_format_effort_days():
    assert format_effort_days(40) == "5"
    assert format_effort_days(60) == "7.5"


def test_format_hours():
    assert format_hours(40) == "40"
    assert format_hours(7.5) == "7.5"


def test_markdown_export_contains_first_year_total(report_context):
    md = generate_markdown(report_context)
    assert "Development cost" in md
    assert "Maintenance & operations (monthly / annual)" in md
    assert "Development period" in md
    assert "¥700,000" in md
    assert "¥" in md


def test_markdown_export_contains_effort_summary(report_context):
    md = generate_markdown(report_context)
    assert "Total Person-Hours" in md
    assert "Total Effort Days" in md
    assert "| 40 | 5 |" in md


def test_markdown_export_ja_locale():
    ctx = sample_report_context(
        locale="ja",
        generated_at=datetime(2026, 6, 7),
        export_user_display_name="山田太郎",
    )
    md = generate_markdown(ctx)
    assert "開発コストの概要" in md
    assert "開発費用" in md
    assert "保守運用費用　月額 /年間" in md
    assert "開発期間" in md
    assert "見積作成者" in md
    assert "山田太郎" in md
    assert "2026年6月7日" in md
    assert "¥700,000" in md
    assert "初年度合計コスト" not in md
    assert "エグゼクティブコストサマリー" not in md
    assert "抽出要件" not in md
    assert "## 機能要件" in md
    assert "## 機能詳細" in md
    assert "推奨チーム人数" not in md
    assert "フェーズ内訳" not in md
    assert "ロール内訳" not in md
    assert "## 非経常費用  内訳" in md
    assert "## ランニングコスト  内訳" in md
    assert "（NRC）" not in md
    assert "（RC）" not in md
    assert ".0 日" not in md
    assert "Rate Card Reference" not in md
    assert "AI Confidence" not in md
    assert "Cost Drivers" not in md
    assert "リスク・ギャップ" not in md
    assert "| 実装 |" in md
    assert "| 開発者 |" in md


def test_markdown_export_all_report_sections(report_context):
    md = generate_markdown(report_context)
    sections = [
        "Project Summary",
        "Development Cost Summary",
        "Functional Requirements",
        "Feature Line Items",
        "Effort Summary",
        "Project Timeline (Gantt)",
        "NRC Breakdown (Detailed)",
        "RC Breakdown (Detailed)",
        "Estimate Exclusions",
        "Approval",
    ]
    for section in sections:
        assert section in md
    removed = [
        "Role Breakdown",
        "Phase Breakdown",
        "Cost Drivers",
        "Risks & Gaps",
        "AI Confidence Notes",
        "Rate Card Reference",
    ]
    for section in removed:
        assert section not in md


def test_markdown_export_gantt_omits_task_table(report_context):
    md = generate_markdown(report_context)
    assert "Project Timeline (Gantt)" in md
    assert "Project start" in md
    assert "2026-06-09" in md
    assert "2026-06-09 | 2026-06-13 |" not in md


def test_markdown_export_feature_effort_days(report_context):
    md = generate_markdown(report_context)
    assert "User login & auth" in md
    assert "| User login & auth | OAuth and session management | development | developer | 40 | 5 |" in md


def test_markdown_export_omits_internal_sections():
    ctx = sample_report_context(
        rate_card_name="Rate Card Default",
        rate_card_version_number=2,
    )
    md = generate_markdown(ctx)
    assert "Rate Card Default" not in md
    assert "Rate Card Reference" not in md
    assert "Cost Drivers" not in md


def test_markdown_export_includes_discount_pricing_when_present():
    ctx = sample_report_context(estimate=sample_estimate_with_discount())
    md = generate_markdown(ctx)
    assert "Development Cost" in md
    assert "Limited-Time Discount" in md
    assert "Special Price" in md
    assert "Campaign Terms" in md
    assert "¥1,000,000" in md
    assert "30% OFF" in md


def test_markdown_export_rc_breakdown_includes_monthly_and_annual_totals(report_context):
    md = generate_markdown(report_context)
    assert "Monthly RC Total" in md
    assert "Annual RC Total" in md
    assert "| Monthly RC Total | | ¥170,000 | |" in md
    assert "| Annual RC Total | | | ¥2,040,000 |" in md
    assert "Cloud Infrastructure" in md
    assert "Server & database usage" in md
    assert "Maintenance and Support" in md
