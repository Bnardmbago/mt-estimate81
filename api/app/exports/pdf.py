from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.exports.markdown import format_currency, format_effort_days, format_hours

TEMPLATE_DIR = Path(__file__).parent / "templates"


def _render_template(template_name: str, **context: Any) -> bytes:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(template_name)
    html = template.render(**context)

    from weasyprint import HTML

    return HTML(string=html, base_url=str(TEMPLATE_DIR)).write_pdf()


def generate_quotation_pdf(quotation_context: dict[str, Any]) -> bytes:
    return _render_template(
        "estimate_quotation.html.j2",
        ctx=quotation_context,
        format_currency=format_currency,
    )


def generate_report_pdf(report_context: dict[str, Any]) -> bytes:
    return _render_template(
        "estimate_report.html.j2",
        ctx=report_context,
        format_currency=format_currency,
        format_hours=format_hours,
        format_effort_days=format_effort_days,
    )


def generate_preliminary_pdf(preliminary_context: dict[str, Any]) -> bytes:
    return _render_template(
        "estimate_preliminary.html.j2",
        ctx=preliminary_context,
        format_currency=format_currency,
        format_hours=format_hours,
        format_effort_days=format_effort_days,
    )


def generate_pdf(quotation_context: dict[str, Any]) -> bytes:
    """Backward-compatible alias for quotation PDF generation."""
    return generate_quotation_pdf(quotation_context)
