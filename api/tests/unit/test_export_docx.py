from io import BytesIO

from docx import Document

from app.exports.docx import generate_quotation_docx, generate_report_docx
from tests.unit.export_fixtures import sample_quotation_context, sample_report_context


def _cell_text(cell) -> str:
    parts: list[str] = []
    for paragraph in cell.paragraphs:
        if paragraph.text.strip():
            parts.append(paragraph.text)
    for table in cell.tables:
        parts.append(_table_text(table))
    return "\n".join(parts)


def _table_text(table) -> str:
    parts: list[str] = []
    for row in table.rows:
        for cell in row.cells:
            text = _cell_text(cell)
            if text.strip():
                parts.append(text)
    return "\n".join(parts)


def _docx_text(content: bytes) -> str:
    document = Document(BytesIO(content))
    parts: list[str] = []
    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            parts.append(paragraph.text)
    for table in document.tables:
        parts.append(_table_text(table))
    return "\n".join(parts)


def test_report_docx_is_valid_docx_zip():
    content = generate_report_docx(sample_report_context())
    assert content[:2] == b"PK"


def test_report_docx_contains_project_and_cost_sections():
    content = generate_report_docx(sample_report_context())
    text = _docx_text(content)
    assert "Portal Redesign" in text
    assert "ACME Corp" in text
    assert "Development cost" in text
    assert "Development period" in text
    assert "NRC Breakdown (Detailed)" in text
    assert "RC Breakdown (Detailed)" in text


def test_report_docx_excludes_removed_sections():
    content = generate_report_docx(sample_report_context())
    text = _docx_text(content)
    assert "Rate Card Reference" not in text
    assert "AI Confidence" not in text
    assert "Cost Drivers" not in text
    assert "Risks & Gaps" not in text


def test_report_docx_ja_locale():
    content = generate_report_docx(
        sample_report_context(locale="ja", export_user_display_name="山田太郎")
    )
    text = _docx_text(content)
    assert "開発コストの概要" in text
    assert "開発費用" in text
    assert "保守運用費用　月額 /年間" in text
    assert "開発期間" in text
    assert "見積作成者" in text
    assert "山田太郎" in text
    assert "初年度合計コスト" not in text


def test_quotation_docx_contains_title_client_and_totals():
    content = generate_quotation_docx(sample_quotation_context())
    text = _docx_text(content)
    assert "QUOTATION" in text
    assert "ACME Corp" in text
    assert "Portal Redesign" in text
    assert "¥770,000" in text


def test_quotation_docx_quote_number_cell_blank():
    content = generate_quotation_docx(sample_quotation_context())
    text = _docx_text(content)
    assert "Quotation No." in text
    assert "Q003" not in text


def test_quotation_docx_ja_locale():
    content = generate_quotation_docx(sample_quotation_context(locale="ja"))
    text = _docx_text(content)
    assert "見積書" in text
    assert "御中" in text
    assert "式" in text
