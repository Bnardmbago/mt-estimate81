from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.exports.markdown import format_currency, format_effort_days, format_hours, format_person_days

TEMPLATE_DIR = Path(__file__).parent / "templates"

CONTACT_EXPORT_WATERMARK_TEXT = "Draft Estimate"
INTERNAL_DOSSIER_WATERMARK_TEXT = "INTERNAL — DO NOT DISTRIBUTE"


def _build_template_html(
    template_name: str,
    *,
    show_watermark: bool = False,
    watermark_text: str | None = None,
    **context: Any,
) -> str:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(template_name)
    return template.render(
        show_watermark=show_watermark,
        watermark_text=watermark_text or CONTACT_EXPORT_WATERMARK_TEXT,
        **context,
    )


def _render_template(
    template_name: str,
    *,
    show_watermark: bool = False,
    watermark_text: str | None = None,
    **context: Any,
) -> bytes:
    html = _build_template_html(
        template_name,
        show_watermark=show_watermark,
        watermark_text=watermark_text,
        **context,
    )

    from weasyprint import HTML

    return HTML(string=html, base_url=str(TEMPLATE_DIR)).write_pdf()


def generate_quotation_pdf(quotation_context: dict[str, Any], *, show_watermark: bool = False) -> bytes:
    """Backward-compatible alias for unified formal quotation PDF generation."""
    return generate_quotation_formal_pdf(quotation_context, show_watermark=show_watermark)


def generate_quotation_formal_pdf(
    quotation_context: dict[str, Any],
    *,
    show_watermark: bool = False,
) -> bytes:
    return _render_template(
        "estimate_quotation_formal.html.j2",
        show_watermark=show_watermark,
        ctx=quotation_context,
        format_currency=format_currency,
    )


def generate_report_pdf(report_context: dict[str, Any], *, show_watermark: bool = False) -> bytes:
    return _render_template(
        "estimate_report.html.j2",
        show_watermark=show_watermark,
        ctx=report_context,
        format_currency=format_currency,
        format_hours=format_hours,
        format_effort_days=format_effort_days,
        format_person_days=format_person_days,
    )


def generate_pdf(quotation_context: dict[str, Any]) -> bytes:
    """Backward-compatible alias for quotation PDF generation."""
    return generate_quotation_pdf(quotation_context)


def build_internal_dossier_html(ctx: dict[str, Any]) -> str:
    return _build_template_html(
        "estimate_internal_dossier.html.j2",
        show_watermark=True,
        watermark_text=INTERNAL_DOSSIER_WATERMARK_TEXT,
        ctx=ctx,
        format_currency=format_currency,
        format_hours=format_hours,
        format_effort_days=format_effort_days,
        format_person_days=format_person_days,
    )


def generate_internal_dossier_pdf(ctx: dict[str, Any]) -> bytes:
    html = build_internal_dossier_html(ctx)

    from weasyprint import HTML

    return HTML(string=html, base_url=str(TEMPLATE_DIR)).write_pdf()
