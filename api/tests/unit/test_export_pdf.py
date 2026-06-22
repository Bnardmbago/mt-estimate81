from datetime import datetime

import pytest

try:
    from weasyprint import HTML as _WeasyprintHTML
except OSError:
    pytest.skip("WeasyPrint system libraries not available", allow_module_level=True)
else:
    del _WeasyprintHTML

from app.exports.pdf import generate_preliminary_pdf, generate_quotation_pdf, generate_report_pdf
from tests.unit.export_fixtures import (
    sample_preliminary_context,
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


@pytest.fixture
def preliminary_context():
    return sample_preliminary_context()


def test_preliminary_pdf_starts_with_pdf_magic_bytes(preliminary_context):
    content = generate_preliminary_pdf(preliminary_context)
    assert content.startswith(b"%PDF")


def test_preliminary_pdf_ja_locale():
    ctx = sample_preliminary_context(locale="ja", generated_at=datetime(2026, 6, 7))
    content = generate_preliminary_pdf(ctx)
    assert content.startswith(b"%PDF")
    assert len(content) > 1000


def test_preliminary_pdf_en_locale():
    ctx = sample_preliminary_context(locale="en", generated_at=datetime(2026, 6, 7))
    content = generate_preliminary_pdf(ctx)
    assert content.startswith(b"%PDF")
    assert len(content) > 1000
