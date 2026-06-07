from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.exports.markdown import (
    LABELS,
    _build_feature_rows,
    _build_form_fields,
    format_currency,
    format_date,
    format_effort_days,
    format_hours,
)
from app.models.estimate import Estimate

TEMPLATE_DIR = Path(__file__).parent / "templates"


def generate_pdf(
    estimate: Estimate,
    locale: str,
    *,
    rate_card_name: str | None = None,
    rate_card_version_number: int | None = None,
    generated_at: datetime | None = None,
) -> bytes:
    if locale not in ("ja", "en"):
        raise ValueError(f"Unsupported locale: {locale}")

    calculation = estimate.calculation_result or {}
    extracted = estimate.extracted_data or {}
    form_data = estimate.form_data or {}
    generated_at = generated_at or datetime.utcnow()

    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("estimate.html.j2")

    html = template.render(
        labels=LABELS[locale],
        locale=locale,
        project_name=estimate.project_name,
        client_name=estimate.client_name,
        generated_date=format_date(generated_at, locale),
        form_fields=_build_form_fields(form_data, locale),
        extracted=extracted,
        feature_items=_build_feature_rows(estimate),
        calculation=calculation,
        rate_card_name=rate_card_name,
        rate_card_version_number=rate_card_version_number,
        format_currency=format_currency,
        format_hours=format_hours,
        format_effort_days=format_effort_days,
    )

    from weasyprint import HTML

    return HTML(string=html).write_pdf()
