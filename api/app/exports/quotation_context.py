from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app.config import settings
from app.exports.markdown import format_date
from app.exports.report_context import build_report_context
from app.models.estimate import Estimate

TEMPLATE_DIR = Path(__file__).parent / "templates"
LOGO_PATH = "assets/mtech-logo.png"

QUOTATION_LABELS: dict[str, dict[str, str]] = {
    "ja": {
        "title": "見 積 書",
        "issue_date": "発行日",
        "payment_terms": "お支払条件",
        "validity": "有効期限",
        "total_amount": "合計金額",
        "item": "項目",
        "quantity": "数量",
        "unit": "単位",
        "unit_price": "単価",
        "subtotal_col": "小計",
        "subtotal": "小計",
        "tax": "消費税",
        "grand_total": "計",
        "tax_target": "10%対象",
        "bank_details": "振込先",
        "remarks": "備考",
        "client_suffix": "御中",
        "registration_number": "登録番号",
        "tel": "TEL",
        "unit_lot": "式",
        "validity_until": "発行日より{days}日",
        "validity_note": "見積書有効期限は{days}日間です。",
        "tax_target_note": "（税抜）",
        "subject_prefix": "件名",
        "quote_prefix": "見積番号",
    },
    "en": {
        "title": "QUOTATION",
        "issue_date": "Issue Date",
        "payment_terms": "Payment Terms",
        "validity": "Validity",
        "total_amount": "Total Amount",
        "item": "Item",
        "quantity": "Qty",
        "unit": "Unit",
        "unit_price": "Unit Price",
        "subtotal_col": "Subtotal",
        "subtotal": "Subtotal",
        "tax": "Tax",
        "grand_total": "Total",
        "tax_target": "Taxable (10%)",
        "bank_details": "Bank Transfer",
        "remarks": "Remarks",
        "client_suffix": "",
        "registration_number": "Registration No.",
        "tel": "Tel",
        "unit_lot": "lot",
        "validity_until": "{days} days from issue date",
        "validity_note": "This quotation is valid for {days} days.",
        "tax_target_note": "(excl. tax)",
        "subject_prefix": "Subject",
        "quote_prefix": "Quote No.",
    },
}

DEFAULT_TAX_RATE = 0.10


def _build_line_items(nrc_line_items: list[dict[str, Any]], locale: str) -> list[dict[str, Any]]:
    unit = QUOTATION_LABELS[locale]["unit_lot"]
    rows: list[dict[str, Any]] = []
    for row in nrc_line_items:
        cost = int(row.get("cost_jpy") or 0)
        if cost <= 0:
            continue
        name = str(row.get("item") or row.get("category") or "")
        rows.append(
            {
                "name": name,
                "quantity": 1,
                "unit": unit,
                "unit_price_jpy": cost,
                "subtotal_jpy": cost,
            }
        )
    return rows


def _format_validity_text(locale: str, days: int) -> str:
    template = QUOTATION_LABELS[locale]["validity_until"]
    return template.format(days=days)


def _tax_percent_label(tax_rate: float, locale: str) -> str:
    pct = int(round(tax_rate * 100))
    if locale == "ja":
        return f"{pct}%対象"
    return f"Taxable ({pct}%)"


def build_quotation_context(
    estimate: Estimate,
    locale: str,
    *,
    generated_at: datetime,
    rate_card_name: str | None,
    rate_card_version_number: int | None,
    rate_card_effective_date: datetime | None,
    export_revision: int,
    tax_rate: float | None = None,
) -> dict[str, Any]:
    if locale not in ("ja", "en"):
        raise ValueError(f"Unsupported locale: {locale}")

    report = build_report_context(
        estimate,
        locale,
        generated_at=generated_at,
        rate_card_name=rate_card_name,
        rate_card_version_number=rate_card_version_number,
        rate_card_effective_date=rate_card_effective_date,
        export_revision=export_revision,
    )

    resolved_tax_rate = tax_rate if tax_rate is not None else DEFAULT_TAX_RATE
    labels = QUOTATION_LABELS[locale]
    nrc_line_items = report["calculation"].get("nrc_line_items") or []
    line_items = _build_line_items(nrc_line_items, locale)

    subtotal_jpy = int(report["executive_summary"]["nrc_total_jpy"])
    tax_jpy = int(round(subtotal_jpy * resolved_tax_rate))
    grand_total_jpy = subtotal_jpy + tax_jpy

    validity_days = settings.quotation_validity_days
    validity_date = generated_at + timedelta(days=validity_days)

    payment_terms = (
        settings.quotation_payment_terms_ja
        if locale == "ja"
        else settings.quotation_payment_terms_en
    )
    bank_details = (
        settings.quotation_bank_details_ja
        if locale == "ja"
        else settings.quotation_bank_details_en
    )
    remarks = (
        settings.quotation_remarks_ja if locale == "ja" else settings.quotation_remarks_en
    )

    client_display = report["project_summary"]["client_name"]
    if locale == "ja" and labels["client_suffix"]:
        client_display = f"{client_display}　{labels['client_suffix']}"

    project_name = report["project_summary"]["project_name"]
    subject_line = f"{labels['subject_prefix']}：{project_name}"
    quote_number = f"Q{export_revision:03d}"
    validity_note = labels["validity_note"].format(days=validity_days)

    return {
        "labels": labels,
        "locale": locale,
        "logo_path": LOGO_PATH,
        "issue_date": format_date(generated_at, locale),
        "validity_date": format_date(validity_date, locale),
        "validity_text": _format_validity_text(locale, validity_days),
        "payment_terms": payment_terms,
        "bank_details": bank_details,
        "remarks": remarks,
        "client_name": client_display,
        "project_name": project_name,
        "subject_line": subject_line,
        "quote_number": quote_number,
        "validity_note": validity_note,
        "estimate_id": report["project_summary"]["estimate_id"],
        "export_revision": export_revision,
        "company": {
            "name": settings.quotation_company_name,
            "brand": settings.quotation_company_brand,
            "postal_code": settings.quotation_company_postal_code,
            "address": settings.quotation_company_address,
            "tel": settings.quotation_company_tel,
            "email": settings.quotation_company_email,
            "registration_number": settings.quotation_invoice_registration_number,
        },
        "line_items": line_items,
        "subtotal_jpy": subtotal_jpy,
        "tax_jpy": tax_jpy,
        "grand_total_jpy": grand_total_jpy,
        "tax_rate": resolved_tax_rate,
        "tax_percent_label": _tax_percent_label(resolved_tax_rate, locale),
        "template_dir": str(TEMPLATE_DIR),
        "questionnaire_sections": report.get("questionnaire_sections") or [],
        "questionnaire_appendix_title": report["labels"]["questionnaire_appendix"],
    }
