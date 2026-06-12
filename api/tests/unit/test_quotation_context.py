from datetime import datetime

from app.config import settings
from tests.unit.export_fixtures import sample_estimate_with_calculation, sample_quotation_context


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
    assert ctx["client_name"].endswith("御中")


def test_quotation_quote_number_and_subject():
    ctx = sample_quotation_context(export_revision=3)
    assert ctx["quote_number"] == "Q003"
    assert "Portal Redesign" in ctx["subject_line"]
    assert "30" in ctx["validity_note"]


def test_quotation_en_labels():
    ctx = sample_quotation_context(locale="en")
    assert ctx["labels"]["title"] == "QUOTATION"
    assert "御中" not in ctx["client_name"]
