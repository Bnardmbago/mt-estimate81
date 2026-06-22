import uuid
from datetime import datetime

import pytest

from app.exports.report_context import build_report_context
from app.i18n.localized_content import store_localized_dict
from tests.unit.export_fixtures import sample_estimate_with_calculation


def test_report_context_executive_totals_match_calculation():
    estimate = sample_estimate_with_calculation()
    ctx = build_report_context(
        estimate,
        "en",
        generated_at=datetime(2026, 6, 7),
        rate_card_name="Standard",
        rate_card_version_number=1,
        rate_card_effective_date=datetime(2026, 1, 1),
        export_revision=1,
    )

    executive = ctx["executive_summary"]
    calc = estimate.calculation_result
    assert executive["nrc_total_jpy"] == calc["nrc"]["total_jpy"]
    assert executive["monthly_rc_jpy"] == calc["rc"]["monthly_total_jpy"]
    assert executive["annual_rc_jpy"] == calc["rc"]["annual_total_jpy"]
    assert executive["first_year_total_jpy"] == calc["first_year_total_jpy"]


def test_report_context_enriches_role_breakdown_developers():
    estimate = sample_estimate_with_calculation()
    estimate.calculation_result["role_breakdown"] = [
        {
            "role": "developer",
            "hours": 160,
            "rate_jpy": 6000,
            "cost_jpy": 960000,
        }
    ]

    ctx = build_report_context(
        estimate,
        "en",
        generated_at=datetime(2026, 6, 7),
        rate_card_name="Standard",
        rate_card_version_number=1,
        rate_card_effective_date=datetime(2026, 1, 1),
        export_revision=1,
    )

    row = ctx["calculation"]["role_breakdown"][0]
    assert row["personnel_count"] == 4


def test_report_context_includes_gantt_chart_svg():
    estimate = sample_estimate_with_calculation()
    ctx = build_report_context(
        estimate,
        "en",
        generated_at=datetime(2026, 6, 7),
        rate_card_name="Standard",
        rate_card_version_number=1,
        rate_card_effective_date=datetime(2026, 1, 1),
        export_revision=1,
    )

    assert ctx["gantt_chart_svg"].startswith("<svg")


def test_report_context_legacy_extracted_data_fallbacks():
    estimate = sample_estimate_with_calculation()
    estimate.extracted_data = {
        "functional_requirements": ["Login"],
        "gaps": ["Budget unclear", "Timeline unclear"],
        "risks": ["Scope creep"],
    }

    ctx = build_report_context(
        estimate,
        "en",
        generated_at=datetime(2026, 6, 7),
        rate_card_name=None,
        rate_card_version_number=None,
        rate_card_effective_date=None,
        export_revision=1,
    )

    assert ctx["extracted"]["confidence_score"] == 60.0
    assert ctx["extracted"]["accuracy_level"] == "medium"
    assert ctx["extracted"]["estimate_exclusions"] == []
    assert ctx["rate_card_reference"]["name"] == "None"


def test_report_context_project_summary_fields():
    estimate_id = uuid.uuid4()
    estimate = sample_estimate_with_calculation(estimate_id=estimate_id)
    ctx = build_report_context(
        estimate,
        "en",
        generated_at=datetime(2026, 6, 7),
        rate_card_name="RC",
        rate_card_version_number=3,
        rate_card_effective_date=datetime(2026, 3, 1),
        export_revision=2,
    )

    summary = ctx["project_summary"]
    assert summary["estimate_id"] == str(estimate_id)
    assert summary["export_revision"] == 2
    assert summary["estimate_type"] == "Web Application"


def test_report_context_questionnaire_sections_from_form():
    estimate = sample_estimate_with_calculation()
    ctx = build_report_context(
        estimate,
        "en",
        generated_at=datetime(2026, 6, 7),
        rate_card_name="RC",
        rate_card_version_number=1,
        rate_card_effective_date=datetime(2026, 1, 1),
        export_revision=1,
    )

    sections = ctx["questionnaire_sections"]
    assert sections
    spec = next(section for section in sections if section["id"] == "specification")
    labels = [field["label"] for field in spec["fields"]]
    assert "Development approach" in labels
    assert "key_assumptions" not in ctx


def test_report_context_resolves_i18n_form_data():
    estimate = sample_estimate_with_calculation()
    estimate.form_data = store_localized_dict(
        None,
        "ja",
        {
            "desired_system": "顧客ポータル",
            "development_approach": "アジャイル",
        },
    )
    estimate.form_data = store_localized_dict(
        estimate.form_data,
        "en",
        {
            "desired_system": "Customer portal",
            "development_approach": "Agile",
            "usage_platform": "web_browser",
        },
    )

    ctx_en = build_report_context(
        estimate,
        "en",
        generated_at=datetime(2026, 6, 7),
        rate_card_name="RC",
        rate_card_version_number=1,
        rate_card_effective_date=datetime(2026, 1, 1),
        export_revision=1,
    )
    ctx_ja = build_report_context(
        estimate,
        "ja",
        generated_at=datetime(2026, 6, 7),
        rate_card_name="RC",
        rate_card_version_number=1,
        rate_card_effective_date=datetime(2026, 1, 1),
        export_revision=1,
    )

    header_en = next(
        section for section in ctx_en["questionnaire_sections"] if section["id"] == "header"
    )
    header_ja = next(
        section for section in ctx_ja["questionnaire_sections"] if section["id"] == "header"
    )
    en_values = {field["label"]: field["value"] for field in header_en["fields"]}
    ja_values = {field["label"]: field["value"] for field in header_ja["fields"]}
    assert en_values["What kind of system do you want to build?"] == "Customer portal"
    assert ja_values["どのようなシステムを作りたいですか？"] == "顧客ポータル"
    assert en_values["Where will it be used?"] == "Web browser"


def test_report_context_resolves_i18n_extracted_data():
    estimate = sample_estimate_with_calculation()
    estimate.extracted_data = store_localized_dict(
        None,
        "en",
        {
            "functional_requirements": ["Login"],
            "confidence_score": 80,
            "accuracy_level": "high",
            "estimate_type": "Web Application",
        },
    )
    estimate.extracted_data = store_localized_dict(
        estimate.extracted_data,
        "ja",
        {
            "functional_requirements": ["ログイン"],
            "confidence_score": 80,
            "accuracy_level": "high",
            "estimate_type": "Webアプリ",
        },
    )

    ctx_ja = build_report_context(
        estimate,
        "ja",
        generated_at=datetime(2026, 6, 7),
        rate_card_name="RC",
        rate_card_version_number=1,
        rate_card_effective_date=datetime(2026, 1, 1),
        export_revision=1,
    )

    assert ctx_ja["extracted"]["functional_requirements"] == ["ログイン"]
    assert ctx_ja["project_summary"]["estimate_type"] == "Webアプリ"
