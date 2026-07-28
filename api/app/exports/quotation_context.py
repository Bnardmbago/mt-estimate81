from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app.config import settings
from app.exports.export_i18n import localize_line_item_name
from app.exports.markdown import format_currency, format_date
from app.exports.pricing_summary import (
    apply_quotation_special_notes,
    build_formal_remarks,
    build_formal_remarks_items,
)
from app.exports.report_context import build_report_context
from app.models.estimate import Estimate
from app.presentation.resolver import PresentationBundle

TEMPLATE_DIR = Path(__file__).parent / "templates"

QUOTATION_LABELS: dict[str, dict[str, str]] = {
    "ja": {
        "title": "見積書",
        "intro": "下記の通りお見積もりいたします。",
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

FORMAL_QUOTATION_LABELS: dict[str, dict[str, str]] = {
    "ja": {
        **QUOTATION_LABELS["ja"],
        "item": "品目",
        "unit": "数量",
        "unit_price": "単価",
        "subtotal_col": "金額",
        "development_cost": "ソフトウェア開発費用",
        "discount_row": "特別割引（{percent}％OFF）",
        "notes_heading": "【備考】",
    },
    "en": {
        **QUOTATION_LABELS["en"],
        "item": "Item",
        "unit": "Qty",
        "unit_price": "Unit Price",
        "subtotal_col": "Amount",
        "development_cost": "Software Development Cost",
        "discount_row": "Special Discount ({percent}% OFF)",
        "notes_heading": "[Notes]",
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

DEFAULT_LOGO_SRC = "assets/BI_logo.svg"


def _resolved_company_contact(
    locale: str,
    *,
    postal_code: str | None = None,
    address: str | None = None,
    tel: str | None = None,
    email: str | None = None,
) -> dict[str, Any]:
    labels = QUOTATION_LABELS[locale]
    resolved_postal = (postal_code or "").strip() or (
        settings.quotation_company_postal_code.strip() or DEFAULT_POSTAL_CODE
    )
    if address is not None and address.strip():
        address_source = address
    else:
        address_source = settings.quotation_company_address
    address_lines = [
        line.strip()
        for line in address_source.splitlines()
        if line.strip()
    ] or list(DEFAULT_ADDRESS_LINES_JA)
    resolved_tel = (tel or "").strip() or (
        settings.quotation_company_tel.strip() or DEFAULT_COMPANY_TEL
    )
    resolved_email = (email or "").strip() or (
        settings.quotation_company_email.strip() or DEFAULT_COMPANY_EMAIL
    )

    if locale == "ja":
        address_body = "\n".join(address_lines)
        contact_block = (
            f"〒{resolved_postal}\n"
            f"{address_body}\n"
            f"\n"
            f"{labels['tel']}：{resolved_tel}\n"
            f"{labels['mail']} ：{resolved_email}"
        )
    else:
        address_text = "\n".join(address_lines)
        contact_block = (
            f"Postal code {resolved_postal}\n"
            f"{address_text}\n"
            f"\n"
            f"{labels['tel']}: {resolved_tel}\n"
            f"{labels['mail']}: {resolved_email}"
        )

    return {
        "postal_code": resolved_postal,
        "address_lines": address_lines,
        "tel": resolved_tel,
        "email": resolved_email,
        "contact_block": contact_block.strip(),
    }


def _build_quotation_base(
    estimate: Estimate,
    locale: str,
    *,
    generated_at: datetime,
    rate_card_name: str | None,
    rate_card_version_number: int | None,
    rate_card_effective_date: datetime | None,
    export_revision: int,
    tax_rate: float | None = None,
    company_config: Any | None = None,
    logo_src: str | None = None,
    logo_bytes: bytes | None = None,
    logo_ext: str | None = None,
    presentation: PresentationBundle | None = None,
    include_cover: bool | None = None,
    cover_values: dict[str, Any] | None = None,
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
        presentation=presentation,
        include_cover=include_cover,
        cover_values=cover_values,
    )

    resolved_tax_rate = tax_rate if tax_rate is not None else DEFAULT_TAX_RATE
    labels = QUOTATION_LABELS[locale]

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

    if company_config is not None:
        configured_bank_details = (
            company_config.bank_details_ja
            if locale == "ja"
            else company_config.bank_details_en
        )
        company_contact = _resolved_company_contact(
            locale,
            postal_code=company_config.postal_code,
            address=company_config.address,
            tel=company_config.tel,
            email=company_config.email,
        )
    else:
        configured_bank_details = (
            settings.quotation_bank_details_ja
            if locale == "ja"
            else settings.quotation_bank_details_en
        )
        company_contact = _resolved_company_contact(locale)

    bank_details = configured_bank_details.strip() or (
        DEFAULT_BANK_DETAILS_JA if locale == "ja" else DEFAULT_BANK_DETAILS_EN
    )

    client_display = report["project_summary"]["client_name"]
    if locale == "ja" and labels["client_suffix"]:
        client_display = f"{client_display}　{labels['client_suffix']}"

    project_name = report["project_summary"]["project_name"]
    validity_note = labels["validity_note"].format(days=validity_days)
    brand = settings.quotation_company_brand.strip() or "Beyond AI"

    return {
        "locale": locale,
        "intro": labels["intro"],
        "issue_date": format_date(generated_at, locale),
        "validity_date": format_date(validity_date, locale),
        "validity_text": _format_validity_text(locale, validity_days),
        "payment_terms": payment_terms,
        "bank_details": bank_details,
        "logo_src": logo_src or DEFAULT_LOGO_SRC,
        "logo_bytes": logo_bytes,
        "logo_ext": logo_ext,
        "client_name": client_display,
        "project_name": project_name,
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
        "subtotal_jpy": subtotal_jpy,
        "tax_jpy": tax_jpy,
        "grand_total_jpy": grand_total_jpy,
        "tax_rate": resolved_tax_rate,
        "tax_with_rate_label": _tax_with_rate_label(resolved_tax_rate, locale),
        "pricing_summary": report.get("pricing_summary") or {},
        "nrc_line_items": report.get("calculation", {}).get("nrc_line_items") or [],
        "template_dir": str(TEMPLATE_DIR),
        "theme": report["theme"],
        "style": report["style"],
        "layout": report["layout"],
        "page": report["page"],
        "include_cover": report["include_cover"],
        "cover": report["cover"],
        "presentation": report["presentation"],
    }


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
    quotation_notes_config: Any | None = None,
    company_config: Any | None = None,
    logo_src: str | None = None,
    logo_bytes: bytes | None = None,
    logo_ext: str | None = None,
    presentation: PresentationBundle | None = None,
    include_cover: bool | None = None,
    cover_values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return build_formal_quotation_context(
        estimate,
        locale,
        generated_at=generated_at,
        rate_card_name=rate_card_name,
        rate_card_version_number=rate_card_version_number,
        rate_card_effective_date=rate_card_effective_date,
        export_revision=export_revision,
        tax_rate=tax_rate,
        quotation_notes_config=quotation_notes_config,
        company_config=company_config,
        logo_src=logo_src,
        logo_bytes=logo_bytes,
        logo_ext=logo_ext,
        presentation=presentation,
        include_cover=include_cover,
        cover_values=cover_values,
        quotation_number="",
        registration_number="",
    )


def _format_validity_text(locale: str, days: int) -> str:
    template = QUOTATION_LABELS[locale]["validity_until"]
    return template.format(days=days)


def _tax_with_rate_label(tax_rate: float, locale: str) -> str:
    pct = int(round(tax_rate * 100))
    if locale == "ja":
        return f"消費税（{pct}%）"
    return f"Consumption Tax ({pct}%)"


def _nrc_display_amounts(
    nrc_line_items: list[dict[str, Any]],
    pricing_summary: dict[str, Any],
) -> list[tuple[dict[str, Any], int]]:
    """Return (source row, display amount) pairs in pre-discount yen when discounted."""
    discounted_total = sum(int(round(float(row.get("cost_jpy") or 0))) for row in nrc_line_items)
    if pricing_summary.get("has_discount"):
        original_total = int(pricing_summary.get("nrc_original_total_jpy") or discounted_total)
    else:
        original_total = discounted_total

    if discounted_total <= 0 or original_total == discounted_total:
        return [
            (row, int(round(float(row.get("cost_jpy") or 0))))
            for row in nrc_line_items
            if int(round(float(row.get("cost_jpy") or 0))) > 0
        ]

    scaled: list[tuple[dict[str, Any], int]] = []
    allocated = 0
    positive_rows = [
        row
        for row in nrc_line_items
        if int(round(float(row.get("cost_jpy") or 0))) > 0
    ]
    for index, row in enumerate(positive_rows):
        cost = int(round(float(row.get("cost_jpy") or 0)))
        if index == len(positive_rows) - 1:
            amount = original_total - allocated
        else:
            amount = int(round(cost * original_total / discounted_total))
            allocated += amount
        if amount > 0:
            scaled.append((row, amount))
    return scaled


def _build_formal_line_items(
    pricing_summary: dict[str, Any],
    locale: str,
    nrc_line_items: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    labels = FORMAL_QUOTATION_LABELS[locale]
    rows: list[dict[str, Any]] = []

    for source, amount in _nrc_display_amounts(nrc_line_items or [], pricing_summary):
        name = str(source.get("item") or source.get("category") or "").strip()
        name = localize_line_item_name(name, locale) if name else labels["development_cost"]
        rows.append(
            {
                "kind": "nrc",
                "name": name,
                "description": "",
                "quantity": 1,
                "unit": "",
                "unit_price_jpy": amount,
                "subtotal_jpy": amount,
                "display_unit_price": True,
                "display_quantity": True,
            }
        )

    if not rows:
        fallback = int(
            pricing_summary.get("nrc_original_total_jpy")
            or pricing_summary.get("nrc_discounted_total_jpy")
            or 0
        )
        if fallback > 0:
            rows.append(
                {
                    "kind": "nrc",
                    "name": labels["development_cost"],
                    "description": "",
                    "quantity": 1,
                    "unit": "",
                    "unit_price_jpy": fallback,
                    "subtotal_jpy": fallback,
                    "display_unit_price": True,
                    "display_quantity": True,
                }
            )

    if pricing_summary.get("has_discount"):
        amount = int(pricing_summary.get("discount_amount_jpy") or 0)
        percent = int(pricing_summary.get("discount_percent_display") or 0)
        if amount > 0:
            discount_label = labels["discount_row"].format(percent=percent)
            rows.append(
                {
                    "kind": "discount",
                    "name": discount_label,
                    "description": "",
                    "quantity": None,
                    "unit": "",
                    "unit_price_jpy": amount,
                    "subtotal_jpy": amount,
                    "display_unit_price": False,
                    "display_quantity": False,
                    "discount_display": f"▲{format_currency(amount)}",
                }
            )

    return rows


def build_formal_quotation_context(
    estimate: Estimate,
    locale: str,
    *,
    generated_at: datetime,
    rate_card_name: str | None,
    rate_card_version_number: int | None,
    rate_card_effective_date: datetime | None,
    export_revision: int,
    tax_rate: float | None = None,
    quotation_notes_config: Any | None = None,
    company_config: Any | None = None,
    logo_src: str | None = None,
    logo_bytes: bytes | None = None,
    logo_ext: str | None = None,
    quotation_number: str = "",
    registration_number: str = "",
    contact_person: str | None = None,
    presentation: PresentationBundle | None = None,
    include_cover: bool | None = None,
    cover_values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if locale not in ("ja", "en"):
        raise ValueError(f"Unsupported locale: {locale}")

    base = _build_quotation_base(
        estimate,
        locale,
        generated_at=generated_at,
        rate_card_name=rate_card_name,
        rate_card_version_number=rate_card_version_number,
        rate_card_effective_date=rate_card_effective_date,
        export_revision=export_revision,
        tax_rate=tax_rate,
        company_config=company_config,
        logo_src=logo_src,
        logo_bytes=logo_bytes,
        logo_ext=logo_ext,
        presentation=presentation,
        include_cover=include_cover,
        cover_values=cover_values,
    )

    labels = FORMAL_QUOTATION_LABELS[locale]
    pricing_summary = base.get("pricing_summary") or {}
    issue_date = base["issue_date"]

    if quotation_notes_config is not None and pricing_summary.get("has_discount"):
        pricing_summary = apply_quotation_special_notes(
            pricing_summary,
            locale,
            issue_date,
            quotation_notes_config,
        )

    remarks_items = build_formal_remarks_items(
        pricing_summary,
        locale,
        issue_date,
        notes_config=quotation_notes_config,
    )
    remarks = build_formal_remarks(
        pricing_summary,
        locale,
        issue_date,
        notes_config=quotation_notes_config,
    )

    formal_context = dict(base)
    company = dict(base["company"])
    if contact_person is not None:
        company["contact_person"] = contact_person
    formal_context.update(
        {
            "labels": labels,
            "remarks": remarks,
            "remarks_items": remarks_items,
            "line_items": _build_formal_line_items(
                pricing_summary,
                locale,
                base.get("nrc_line_items") or [],
            ),
            "quote_number": quotation_number,
            "registration_number": registration_number,
            "company": company,
            "pricing_summary": pricing_summary,
            "variant": "formal",
        }
    )
    return formal_context
