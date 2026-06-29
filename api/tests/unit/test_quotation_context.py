from datetime import datetime

from app.config import settings
from tests.unit.export_fixtures import (
    sample_estimate_with_calculation,
    sample_estimate_with_discount,
    sample_quotation_context,
)


def test_quotation_line_items_match_nrc_line_items():
    estimate = sample_estimate_with_calculation()
    ctx = sample_quotation_context(estimate=estimate)
    nrc_count = len(estimate.calculation_result["nrc_line_items"])
    assert len(ctx["line_items"]) == nrc_count
    assert ctx["line_items"][0]["quantity"] == 1
    assert ctx["line_items"][0]["subtotal_jpy"] == 240000


def test_quotation_tax_math():
    ctx = sample_quotation_context(tax_rate=0.10)
    assert ctx["subtotal_jpy"] == 700000
    assert ctx["tax_jpy"] == 70000
    assert ctx["grand_total_jpy"] == 770000


def test_quotation_validity_date():
    generated_at = datetime(2026, 6, 7)
    ctx = sample_quotation_context(generated_at=generated_at, locale="ja")
    assert ctx["validity_date"] == "2026年7月7日"


def test_quotation_validity_date_en():
    generated_at = datetime(2026, 6, 7)
    ctx = sample_quotation_context(generated_at=generated_at, locale="en")
    assert ctx["validity_date"] == "July 7, 2026"


def test_quotation_company_from_settings():
    ctx = sample_quotation_context()
    assert ctx["company"]["name"] == settings.quotation_company_name


def test_quotation_ja_client_suffix():
    ctx = sample_quotation_context(locale="ja")
    assert ctx["labels"]["client"] == "お客様名"
    assert ctx["client_name"].endswith("御中")


def test_quotation_quote_number_and_project():
    ctx = sample_quotation_context(export_revision=3)
    assert ctx["quote_number"] == "Q003"
    assert "Portal Redesign" in ctx["project_name"]
    assert "30" in ctx["validity_note"]


def test_quotation_en_labels():
    ctx = sample_quotation_context(locale="en")
    assert ctx["labels"]["title"] == "QUOTATION"
    assert "御中" not in ctx["client_name"]


def test_quotation_intro_and_tax_labels():
    ctx_ja = sample_quotation_context(locale="ja")
    assert ctx_ja["intro"] == "下記の通りお見積りいたします。"
    assert ctx_ja["tax_with_rate_label"] == "消費税（10%）"
    assert ctx_ja["company"]["brand"] == "Beyond AI"
    assert ctx_ja["company"]["name"] == "株式会社 Beyond AI"
    assert "〒103-0027" in ctx_ja["company"]["contact_block"]
    assert "アーバンネット日本橋二丁目ビル 10階" in ctx_ja["company"]["contact_block"]
    assert "TEL：03-6262-0742" in ctx_ja["company"]["contact_block"]
    assert "MAIL ：ai@beyondai.co.jp" in ctx_ja["company"]["contact_block"]

    ctx_en = sample_quotation_context(locale="en")
    assert ctx_en["intro"] == "We are pleased to provide the following quotation."
    assert ctx_en["tax_with_rate_label"] == "Consumption Tax (10%)"


def test_quotation_excludes_questionnaire_appendix():
    ctx = sample_quotation_context()
    assert "questionnaire_appendix_title" not in ctx
    assert "questionnaire_sections" not in ctx


def test_quotation_company_contact_defaults_when_settings_empty(monkeypatch):
    monkeypatch.setattr(settings, "quotation_company_postal_code", "")
    monkeypatch.setattr(settings, "quotation_company_address", "")
    monkeypatch.setattr(settings, "quotation_company_tel", "")
    monkeypatch.setattr(settings, "quotation_company_email", "")
    ctx = sample_quotation_context(locale="ja")
    assert "〒103-0027" in ctx["company"]["contact_block"]
    assert "TEL：03-6262-0742" in ctx["company"]["contact_block"]


def test_quotation_bank_details_default_when_setting_empty(monkeypatch):
    monkeypatch.setattr(settings, "quotation_bank_details_ja", "")
    ctx = sample_quotation_context(locale="ja")
    assert "株式会社Beyond AI" in ctx["bank_details"]
    assert "住信SBIネット銀行 法人第一支店（ 106） 普通口座 2112728" in ctx["bank_details"]


def test_quotation_includes_campaign_terms_when_discount_present():
    estimate = sample_estimate_with_discount()
    ctx = sample_quotation_context(estimate=estimate, locale="en")
    assert ctx["pricing_summary"]["has_discount"] is True
    assert "special discounted price" in ctx["pricing_summary"]["campaign_terms"]
    assert "¥700,000" in ctx["pricing_summary"]["campaign_terms"]
