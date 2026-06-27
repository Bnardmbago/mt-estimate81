import pytest

try:
    from weasyprint import HTML as _WeasyprintHTML
except OSError:
    pytest.skip("WeasyPrint system libraries not available", allow_module_level=True)
else:
    del _WeasyprintHTML

from app.exports.pdf import generate_report_pdf
from tests.unit.export_fixtures import sample_report_context


def test_report_pdf_with_watermark_generates_pdf():
    content = generate_report_pdf(sample_report_context(), show_watermark=True)
    assert content.startswith(b"%PDF")
