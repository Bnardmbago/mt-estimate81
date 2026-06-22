from io import BytesIO
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from openpyxl import load_workbook

from app.exports.excel import SHEET_NAMES, generate_excel
from app.exports.markdown import (
    format_currency,
    format_currency_yen,
    format_effort_days,
    format_hours,
    format_person_days,
    format_person_months,
)
from app.exports.theme import BLUE_PRIMARY, YELLOW_SECTION
from tests.unit.export_fixtures import (
    sample_estimate_with_calculation,
    sample_preliminary_context,
    sample_quotation_context,
    sample_report_context,
)

TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "app" / "exports" / "templates"


def _render_template(template_name: str, **context) -> str:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(template_name)
    return template.render(**context)


def test_preliminary_template_includes_export_theme_css():
    html = _render_template(
        "estimate_preliminary.html.j2",
        ctx=sample_preliminary_context(),
        format_currency=format_currency_yen,
        format_hours=format_hours,
        format_effort_days=format_effort_days,
        format_person_days=format_person_days,
        format_person_months=format_person_months,
    )
    assert "--export-blue-primary: #4A76A8" in html
    assert "--export-yellow-section: #FFF4CC" in html
    assert "var(--export-blue-primary)" in html
    assert "var(--export-yellow-total)" in html


def test_report_template_includes_export_theme_css():
    html = _render_template(
        "estimate_report.html.j2",
        ctx=sample_report_context(),
        format_currency=format_currency,
        format_hours=format_hours,
        format_effort_days=format_effort_days,
    )
    assert "--export-blue-primary: #4A76A8" in html
    assert "var(--export-yellow-section)" in html


def test_quotation_template_includes_export_theme_css():
    html = _render_template(
        "estimate_quotation.html.j2",
        ctx=sample_quotation_context(),
        format_currency=format_currency,
    )
    assert "--export-blue-primary: #4A76A8" in html
    assert "var(--export-yellow-total)" in html


def test_excel_table_headers_use_blue_theme():
    content = generate_excel(
        sample_report_context(),
        sample_estimate_with_calculation(),
    )
    wb = load_workbook(BytesIO(content), data_only=False)
    features_sheet = wb[SHEET_NAMES["en"]["features"]]
    header_fill = features_sheet["A1"].fill.fgColor.rgb
    assert header_fill in {BLUE_PRIMARY, f"00{BLUE_PRIMARY}"}


def test_excel_section_titles_use_yellow_theme():
    content = generate_excel(
        sample_report_context(),
        sample_estimate_with_calculation(),
    )
    wb = load_workbook(BytesIO(content), data_only=False)
    executive_sheet = wb[SHEET_NAMES["en"]["executive"]]
    section_fill = executive_sheet["A8"].fill.fgColor.rgb
    assert section_fill in {YELLOW_SECTION, f"00{YELLOW_SECTION}"}
