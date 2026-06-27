from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app.config import settings
from app.exports.markdown import format_date
from app.exports.report_context import build_report_context
from app.models.estimate import Estimate

TEMPLATE_DIR = Path(__file__).parent / "templates"

QUOTATION_LABELS: dict[str, dict[str, str]] = {
    "ja": {
        "title": "見積書",
        "intro": "下記の通りお見積りいたします。",
        "issue_date": "発行日",
        "quote_number": "見積書番号",
        "registration_number": "登録番号",
        "project_name": "プロジェクト名",
        "client": "お客様名",
        "contact_person": "担当者",
        "tel": "TEL",
        "mail": "MAIL",
        "total_amount_label": "合計金額",
        "item": "項目",
        "unit": "単位",
        "unit_price": "単価",
        "subtotal_col": "小計",
        "subtotal": "小計",
        "grand_total": "合計",
        "bank_details": "振込先",
        "payment_due": "支払期日",
        "notes_heading": "【備考】",
        "client_suffix": "御中",
        "unit_lot": "式",
        "validity_until": "発行日より{days}日",
        "validity_note": "見積書有効期限は{days}日間です。",
    },
    "en": {
        "title": "QUOTATION",
        "intro": "We are pleased to provide the following quotation.",
        "issue_date": "Issue Date",
        "quote_number": "Quotation No.",
        "registration_number": "Registration No.",
        "project_name": "Project Name",
        "client": "Client",
        "contact_person": "Person in Charge",
        "tel": "TEL",
        "mail": "MAIL",
        "total_amount_label": "Total Amount",
        "item": "Item",
        "unit": "Unit",
        "unit_price": "Unit Price",
        "subtotal_col": "Subtotal",
        "subtotal": "Subtotal",
        "grand_total": "Total",
        "bank_details": "Bank Transfer",
        "payment_due": "Payment Due",
        "notes_heading": "[Notes]",
        "client_suffix": "",
        "unit_lot": "lot",
        "validity_until": "{days} days from issue date",
        "validity_note": "This quotation is valid for {days} days.",
    },
}

DEFAULT_TAX_RATE = 0.10

DEFAULT_BANK_DETAILS_JA = (
    "株式会社Beyond AI\n"
    "住信SBIネット銀行 法人第一支店（ 106） 普通口座 2112728"
)
DEFAULT_BANK_DETAILS_EN = (
    "Beyond AI Co., Ltd.\n"
    "SBI Sumishin Net Bank, Corporate First Branch (106), Ordinary Account 2112728"
)

DEFAULT_POSTAL_CODE = "103-0027"
DEFAULT_ADDRESS_LINES_JA = [
    "東京都中央区日本橋 2丁目1番3号",
    "アーバンネット日本橋二丁目ビル 10階",
]
DEFAULT_COMPANY_TEL = "03-6262-0742"
DEFAULT_COMPANY_EMAIL = "ai@beyondai.co.jp"

DEFAULT_PAYMENT_TERMS_JA = "納品後7日以内"
DEFAULT_PAYMENT_TERMS_EN = "Within 7 days after delivery"


def _resolved_company_contact(locale: str) -> dict[str, Any]:
    labels = QUOTATION_LABELS[locale]
    postal_code = settings.quotation_company_postal_code.strip() or DEFAULT_POSTAL_CODE
    address_lines = [
        line.strip()
        for line in settings.quotation_company_address.splitlines()
        if line.strip()
    ] or list(DEFAULT_ADDRESS_LINES_JA)
    tel = settings.quotation_company_tel.strip() or DEFAULT_COMPANY_TEL
    email = settings.quotation_company_email.strip() or DEFAULT_COMPANY_EMAIL

    if locale == "ja":
        address_body = "\n".join(address_lines)
        contact_block = (
            f"〒{postal_code}\n"
            f"{address_body}\n"
            f"\n"
            f"{labels['tel']}：{tel}\n"
            f"{labels['mail']} ：{email}"
        )
    else:
        address_text = "\n".join(address_lines)
        contact_block = (
            f"Postal code {postal_code}\n"
            f"{address_text}\n"
            f"\n"
            f"{labels['tel']}: {tel}\n"
            f"{labels['mail']}: {email}"
        )

    return {
        "postal_code": postal_code,
        "address_lines": address_lines,
        "tel": tel,
        "email": email,
        "contact_block": contact_block.strip(),
    }


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
                "unit_price_jpy": int(round(float(cost))),
                "subtotal_jpy": int(round(float(cost))),
            }
        )
    return rows


def _format_validity_text(locale: str, days: int) -> str:
    template = QUOTATION_LABELS[locale]["validity_until"]
    return template.format(days=days)


def _tax_with_rate_label(tax_rate: float, locale: str) -> str:
    pct = int(round(tax_rate * 100))
    if locale == "ja":
        return f"消費税（{pct}%）"
    return f"Consumption Tax ({pct}%)"


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

    subtotal_jpy = int(round(float(report["executive_summary"]["nrc_total_jpy"])))
    tax_jpy = int(round(subtotal_jpy * resolved_tax_rate))
    grand_total_jpy = subtotal_jpy + tax_jpy

    validity_days = settings.quotation_validity_days
    validity_date = generated_at + timedelta(days=validity_days)

    configured_payment_terms = (
        settings.quotation_payment_terms_ja
        if locale == "ja"
        else settings.quotation_payment_terms_en
    )
    payment_terms = configured_payment_terms.strip() or (
        DEFAULT_PAYMENT_TERMS_JA if locale == "ja" else DEFAULT_PAYMENT_TERMS_EN
    )
    configured_bank_details = (
        settings.quotation_bank_details_ja
        if locale == "ja"
        else settings.quotation_bank_details_en
    )
    bank_details = configured_bank_details.strip() or (
        DEFAULT_BANK_DETAILS_JA if locale == "ja" else DEFAULT_BANK_DETAILS_EN
    )
    remarks = (
        settings.quotation_remarks_ja if locale == "ja" else settings.quotation_remarks_en
    )

    client_display = report["project_summary"]["client_name"]
    if locale == "ja" and labels["client_suffix"]:
        client_display = f"{client_display}　{labels['client_suffix']}"

    project_name = report["project_summary"]["project_name"]
    quote_number = f"Q{export_revision:03d}"
    validity_note = labels["validity_note"].format(days=validity_days)
    brand = settings.quotation_company_brand.strip() or "Beyond AI"
    company_contact = _resolved_company_contact(locale)

    return {
        "labels": labels,
        "locale": locale,
        "intro": labels["intro"],
        "issue_date": format_date(generated_at, locale),
        "validity_date": format_date(validity_date, locale),
        "validity_text": _format_validity_text(locale, validity_days),
        "payment_terms": payment_terms,
        "bank_details": bank_details,
        "remarks": remarks,
        "client_name": client_display,
        "project_name": project_name,
        "quote_number": quote_number,
        "validity_note": validity_note,
        "estimate_id": report["project_summary"]["estimate_id"],
        "export_revision": export_revision,
        "company": {
            "name": settings.quotation_company_name,
            "brand": brand,
            "postal_code": company_contact["postal_code"],
            "address_lines": company_contact["address_lines"],
            "tel": company_contact["tel"],
            "email": company_contact["email"],
            "contact_block": company_contact["contact_block"],
            "registration_number": settings.quotation_invoice_registration_number,
            "contact_person": settings.quotation_contact_person,
        },
        "line_items": line_items,
        "subtotal_jpy": subtotal_jpy,
        "tax_jpy": tax_jpy,
        "grand_total_jpy": grand_total_jpy,
        "tax_rate": resolved_tax_rate,
        "tax_with_rate_label": _tax_with_rate_label(resolved_tax_rate, locale),
        "template_dir": str(TEMPLATE_DIR),
    }
