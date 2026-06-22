from datetime import datetime

import pytest

from app.exports.preliminary_context import build_preliminary_context
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
    assert len(ctx["phase_rows"]) == 2
    assert ctx["total_effort_days"] > 0


def test_preliminary_phase_rows_skip_zero_hours():
    ctx = sample_preliminary_context()
    for row in ctx["phase_rows"]:
        assert row["effort_days"] > 0


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
    assert ctx["labels"]["title"] == "概算見積書"
    assert "様" in ctx["client_name"]
    assert ctx["locale"] == "ja"


def test_preliminary_en_locale_still_uses_ja_labels():
    ctx = sample_preliminary_context(locale="en")
    assert ctx["labels"]["title"] == "概算見積書"
    assert "様" in ctx["client_name"]


def test_preliminary_shows_role_columns_when_data_exists():
    ctx = sample_preliminary_context()
    assert ctx["show_role_unit_rate"] is True
    assert ctx["show_role_headcount"] is True
    assert ctx["show_role_months"] is True


def test_preliminary_project_rows_use_currency():
    ctx = sample_preliminary_context()
    total_row = next(row for row in ctx["project_rows"] if "value_jpy" in row)
    assert total_row["value_jpy"] == ctx["grand_total_jpy"]


def test_preliminary_requires_calculation():
    estimate = sample_estimate_with_calculation()
    estimate.calculation_result = None
    import pytest

    with pytest.raises(ValueError, match="Calculation result is required"):
        build_preliminary_context(
            estimate,
            "ja",
            generated_at=datetime(2026, 6, 7),
            rate_card_name=None,
            rate_card_version_number=None,
            rate_card_effective_date=None,
            export_revision=1,
        )


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
