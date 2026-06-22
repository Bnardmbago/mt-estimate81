from datetime import datetime

from tests.unit.export_fixtures import sample_estimate_with_calculation, sample_preliminary_context


def test_preliminary_role_summary_matches_role_breakdown():
    ctx = sample_preliminary_context()
    role_subtotal = ctx["role_subtotal_jpy"]
    calculation_roles = sample_estimate_with_calculation().calculation_result["role_breakdown"]
    expected = sum(int(row["cost_jpy"]) for row in calculation_roles)
    assert role_subtotal == expected


def test_preliminary_tax_inclusive_total():
    ctx = sample_preliminary_context(tax_rate=0.10)
    assert ctx["grand_total_jpy"] == ctx["subtotal_jpy"] + ctx["tax_jpy"]
    assert ctx["tax_jpy"] == int(round(ctx["subtotal_jpy"] * 0.10))


def test_preliminary_phase_rows_present():
    ctx = sample_preliminary_context()
    assert len(ctx["phase_rows"]) == 5
    assert ctx["total_effort_days"] > 0


def test_preliminary_feature_sections_include_headers():
    ctx = sample_preliminary_context()
    section_types = [section["type"] for section in ctx["feature_sections"]]
    assert "header" in section_types
    assert "subheader" in section_types


def test_preliminary_assumptions_count():
    ctx = sample_preliminary_context(locale="ja")
    assert len(ctx["assumptions"]) == 5
    assert ctx["assumptions"][0]["number"] == "3.1"


def test_preliminary_ja_labels():
    ctx = sample_preliminary_context(locale="ja")
    assert ctx["labels"]["title"] == "概算見積書（テンプレート）"
    assert "様" in ctx["client_name"]


def test_preliminary_en_labels():
    ctx = sample_preliminary_context(locale="en")
    assert ctx["labels"]["title"] == "Preliminary Estimate (Template)"
    assert "様" not in ctx["client_name"]


def test_preliminary_issue_date_formatted():
    ctx = sample_preliminary_context(
        locale="ja",
        generated_at=datetime(2026, 6, 7),
    )
    assert ctx["issue_date"]


def test_preliminary_includes_questionnaire_appendix_context():
    ctx = sample_preliminary_context(locale="ja")
    assert ctx["questionnaire_appendix_title"] == "プロジェクト質問票（別紙）"
    assert ctx["questionnaire_sections"]
