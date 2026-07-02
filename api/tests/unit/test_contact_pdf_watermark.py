import pytest

try:
    from weasyprint import HTML as _WeasyprintHTML
except OSError:
    pytest.skip("WeasyPrint system libraries not available", allow_module_level=True)
else:
    del _WeasyprintHTML

from app.exports.markdown import format_currency, format_effort_days, format_hours, format_person_days
from app.exports.pdf import (
    CONTACT_EXPORT_WATERMARK_TEXT,
    _build_template_html,
    generate_report_pdf,
)
from tests.unit.export_fixtures import sample_report_context


def test_contact_export_watermark_text_constant():
    assert CONTACT_EXPORT_WATERMARK_TEXT == "Draft Estimate"


def test_report_html_includes_watermark_text():
    html = _build_template_html(
        "estimate_report.html.j2",
        show_watermark=True,
        ctx=sample_report_context(),
        format_currency=format_currency,
        format_hours=format_hours,
        format_effort_days=format_effort_days,
        format_person_days=format_person_days,
    )
    assert f">{CONTACT_EXPORT_WATERMARK_TEXT}</div>" in html


def test_report_pdf_with_watermark_generates_pdf():
    content = generate_report_pdf(sample_report_context(), show_watermark=True)
    assert content.startswith(b"%PDF")
