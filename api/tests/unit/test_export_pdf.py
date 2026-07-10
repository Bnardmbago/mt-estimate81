from datetime import datetime

import pytest

try:
    from weasyprint import HTML as _WeasyprintHTML
except OSError:
    pytest.skip("WeasyPrint system libraries not available", allow_module_level=True)
else:
    del _WeasyprintHTML

from app.exports.markdown import format_currency
from app.exports.pdf import (
    _build_template_html,
    generate_quotation_formal_pdf,
    generate_quotation_pdf,
    generate_report_pdf,
)
from tests.unit.export_fixtures import (
    sample_estimate_with_discount,
    sample_formal_quotation_context,
    sample_quotation_context,
    sample_report_context,
)


@pytest.fixture
def quotation_context():
    return sample_quotation_context()


@pytest.fixture
def report_context():
    return sample_report_context()


def test_quotation_pdf_starts_with_pdf_magic_bytes(quotation_context):
    content = generate_quotation_pdf(quotation_context)
    assert content.startswith(b"%PDF")


def test_quotation_pdf_html_omits_pricing_summary_block():
    ctx = sample_quotation_context(estimate=sample_estimate_with_discount(), locale="en")
    html = _build_template_html(
        "estimate_quotation_formal.html.j2",
        ctx=ctx,
        format_currency=format_currency,
    )
    assert "pricing-summary" not in html
    assert "*Special Notes" not in html
    assert "Limited-Time Discount" not in html
    assert "Special Discount" in html
    assert "[Notes]" in html


def test_quotation_pdf_ja_locale():
    ctx = sample_quotation_context(locale="ja", generated_at=datetime(2026, 6, 7))
    content = generate_quotation_pdf(ctx)
    assert content.startswith(b"%PDF")
    assert len(content) > 1000


def test_quotation_pdf_en_locale():
    ctx = sample_quotation_context(locale="en", generated_at=datetime(2026, 6, 7))
    content = generate_quotation_pdf(ctx)
    assert content.startswith(b"%PDF")
    assert len(content) > 1000


def test_report_pdf_starts_with_pdf_magic_bytes(report_context):
    content = generate_report_pdf(report_context)
    assert content.startswith(b"%PDF")


def test_report_pdf_ja_locale():
    ctx = sample_report_context(locale="ja", generated_at=datetime(2026, 6, 7))
    content = generate_report_pdf(ctx)
    assert content.startswith(b"%PDF")
    assert len(content) > 5000


def test_report_pdf_en_locale():
    ctx = sample_report_context(locale="en", generated_at=datetime(2026, 6, 7))
    content = generate_report_pdf(ctx)
    assert content.startswith(b"%PDF")
    assert len(content) > 5000


def test_formal_quotation_pdf_html_contains_populated_numbers():
    ctx = sample_formal_quotation_context(locale="ja")
    html = _build_template_html(
        "estimate_quotation_formal.html.j2",
        ctx=ctx,
        format_currency=format_currency,
    )
    assert "BAI-20260629-001" in html
    assert "T9010001234562" in html
    assert "開発" in html
    assert "インフラセットアップ" in html
    assert "【備考】" in html
    assert "*特記事項" not in html
    assert "grand-total-box" in html
    assert "grand-total-row" in html
    assert "header-layout" in html
    assert "company-divider" in html
    assert "下記の通りお見積もりいたします。" in html
    # 【備考】 and 小計 share one totals-layout row
    assert "totals-layout" in html
    assert html.index("summary-notes") < html.index("totals-table")
    assert html.index("notes-heading") < html.index(ctx["labels"]["subtotal"])


def test_formal_quotation_pdf_starts_with_pdf_magic_bytes():
    ctx = sample_formal_quotation_context()
    content = generate_quotation_formal_pdf(ctx)
    assert content.startswith(b"%PDF")
