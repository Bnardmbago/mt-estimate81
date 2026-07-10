from datetime import datetime

from app.config import settings
from tests.unit.export_fixtures import (
    sample_estimate_with_calculation,
    sample_estimate_with_discount,
    sample_formal_quotation_context,
    sample_quotation_context,
)


def test_quotation_line_items_use_nrc_breakdown():
    estimate = sample_estimate_with_calculation()
    ctx = sample_quotation_context(estimate=estimate)
    assert len(ctx["line_items"]) == 4
    assert [row["name"] for row in ctx["line_items"]] == [
        "Development",
        "Infrastructure Setup",
        "Contingency",
        "Overhead",
    ]
    assert sum(row["subtotal_jpy"] for row in ctx["line_items"]) == 700000
    assert all(row["kind"] == "nrc" for row in ctx["line_items"])
    assert all(row["quantity"] == 1 for row in ctx["line_items"])


def test_quotation_tax_math():
    ctx = sample_quotation_context(tax_rate=0.10)
    assert ctx["subtotal_jpy"] == 700000
    assert ctx["tax_jpy"] == 70000
    assert ctx["grand_total_jpy"] == 770000


def test_quotation_validity_date():
    generated_at = datetime(2026, 6, 7)
    ctx = sample_quotation_context(generated_at=generated_at, locale="ja")
    assert ctx["validity_date"] == "2026年7月7日"


def test_quotation_validity_date_en():
    generated_at = datetime(2026, 6, 7)
    ctx = sample_quotation_context(generated_at=generated_at, locale="en")
    assert ctx["validity_date"] == "July 7, 2026"


def test_quotation_company_from_settings():
    ctx = sample_quotation_context()
    assert ctx["company"]["name"] == settings.quotation_company_name


def test_quotation_ja_client_suffix():
    ctx = sample_quotation_context(locale="ja")
    assert ctx["labels"]["client"] == "お客様名"
    assert ctx["client_name"].endswith("御中")


def test_quotation_quote_number_and_project():
    ctx = sample_quotation_context(export_revision=3)
    assert ctx["quote_number"] == ""
    assert "Portal Redesign" in ctx["project_name"]
    assert "30" in ctx["validity_note"]


def test_quotation_en_labels():
    ctx = sample_quotation_context(locale="en")
    assert ctx["labels"]["title"] == "QUOTATION"
    assert "御中" not in ctx["client_name"]


def test_quotation_intro_and_tax_labels():
    ctx_ja = sample_quotation_context(locale="ja")
    assert ctx_ja["intro"] == "下記の通りお見積もりいたします。"
    assert ctx_ja["tax_with_rate_label"] == "消費税（10%）"
    assert ctx_ja["company"]["brand"] == "Beyond AI"
    assert ctx_ja["company"]["name"] == "株式会社 Beyond AI"
    assert "〒103-0027" in ctx_ja["company"]["contact_block"]
    assert "アーバンネット日本橋二丁目ビル 10階" in ctx_ja["company"]["contact_block"]
    assert "TEL：03-6262-0742" in ctx_ja["company"]["contact_block"]
    assert "MAIL ：ai@beyondai.co.jp" in ctx_ja["company"]["contact_block"]

    ctx_en = sample_quotation_context(locale="en")
    assert ctx_en["intro"] == "We are pleased to provide the following quotation."
    assert ctx_en["tax_with_rate_label"] == "Consumption Tax (10%)"


def test_quotation_excludes_questionnaire_appendix():
    ctx = sample_quotation_context()
    assert "questionnaire_appendix_title" not in ctx
    assert "questionnaire_sections" not in ctx


def test_quotation_company_contact_defaults_when_settings_empty(monkeypatch):
    monkeypatch.setattr(settings, "quotation_company_postal_code", "")
    monkeypatch.setattr(settings, "quotation_company_address", "")
    monkeypatch.setattr(settings, "quotation_company_tel", "")
    monkeypatch.setattr(settings, "quotation_company_email", "")
    ctx = sample_quotation_context(locale="ja")
    assert "〒103-0027" in ctx["company"]["contact_block"]
    assert "TEL：03-6262-0742" in ctx["company"]["contact_block"]


def test_quotation_bank_details_default_when_setting_empty(monkeypatch):
    monkeypatch.setattr(settings, "quotation_bank_details_ja", "")
    ctx = sample_quotation_context(locale="ja")
    assert "株式会社Beyond AI" in ctx["bank_details"]
    assert "住信SBIネット銀行 法人第一支店（ 106） 普通口座 2112728" in ctx["bank_details"]


def test_quotation_includes_special_notes_when_discount_present():
    estimate = sample_estimate_with_discount()
    ctx = sample_quotation_context(estimate=estimate, locale="en")
    assert ctx["pricing_summary"]["has_discount"] is True
    assert "special discounted price" in ctx["remarks"]
    assert "¥700,000" in ctx["remarks"]
    assert "Limited-Time Discount" not in ctx["remarks"]


def test_quotation_ja_special_notes_in_remarks():
    estimate = sample_estimate_with_discount()
    ctx = sample_quotation_context(estimate=estimate, locale="ja")
    assert "1か月以内" in ctx["remarks"]
    assert "特記事項" not in ctx["remarks"]


def test_formal_quotation_detailed_line_items_with_discount():
    estimate = sample_estimate_with_discount()
    ctx = sample_formal_quotation_context(estimate=estimate, locale="ja")
    assert len(ctx["line_items"]) == 5
    assert [row["name"] for row in ctx["line_items"][:-1]] == [
        "開発",
        "インフラセットアップ",
        "予備費",
        "間接費",
    ]
    assert sum(row["subtotal_jpy"] for row in ctx["line_items"][:-1]) == 1_000_000
    assert ctx["line_items"][-1]["kind"] == "discount"
    assert "30" in ctx["line_items"][-1]["name"]
    assert "▲" in ctx["line_items"][-1]["discount_display"]


def test_formal_quotation_remarks_use_notes_heading():
    estimate = sample_estimate_with_discount()
    ctx = sample_formal_quotation_context(estimate=estimate, locale="ja")
    assert ctx["labels"]["notes_heading"] == "【備考】"
    assert ctx["remarks_items"]
    assert all(not item.startswith(("・", "*", "-", "•")) for item in ctx["remarks_items"])
    assert len(ctx["remarks_items"]) == len(set(ctx["remarks_items"]))
    assert "*" not in ctx["remarks"]
    assert "・" in ctx["remarks"]
    assert "1か月以内" in ctx["remarks"] or "特別価格" in ctx["remarks"]
    assert "特記事項" not in ctx["remarks"]
    # 【備考】 must come only from Admin Quotation Body text — no hardcoded static bullets.
    assert "本見積価格には" not in ctx["remarks"]
    assert "月額保守・運用サービス" not in ctx["remarks"]


def test_formal_remarks_only_admin_body_text_when_discounted():
    from app.admin.quotation_notes_config import QuotationNotesConfig
    from app.exports.pricing_summary import build_formal_remarks_items

    notes = QuotationNotesConfig(
        title_ja="特記事項",
        title_en="Special Notes",
        body_ja=(
            "本見積書の発行日（{issue_date}）から1か月以内にご発注いただいた場合、"
            "特別割引価格 {special_price}（税抜）が適用されます。\n"
            "1か月を過ぎた場合は、通常の開発費用が適用されます。"
        ),
        body_en="Order within one month for {special_price}.",
    )
    items = build_formal_remarks_items(
        {
            "has_discount": True,
            "nrc_discounted_total_jpy": 225400,
            "nrc_original_total_jpy": 300000,
            "discount_percent_display": 25,
            "discount_amount_jpy": 74600,
        },
        "ja",
        "2026年7月8日",
        notes_config=notes,
    )
    assert items == [
        "本見積書の発行日（2026年7月8日）から1か月以内にご発注いただいた場合、"
        "特別割引価格 ¥225,400（税抜）が適用されます。",
        "1か月を過ぎた場合は、通常の開発費用が適用されます。",
    ]


def test_formal_remarks_empty_without_discount():
    from app.exports.pricing_summary import build_formal_remarks_items

    items = build_formal_remarks_items(
        {
            "has_discount": False,
            "nrc_discounted_total_jpy": 700000,
        },
        "ja",
        "2026年7月8日",
    )
    assert items == []


def test_formal_remarks_dedupe_prefixed_and_duplicate_lines():
    from app.exports.pricing_summary import build_formal_remarks_items

    items = build_formal_remarks_items(
        {
            "has_discount": False,
            "nrc_discounted_total_jpy": 700000,
        },
        "ja",
        "2026年7月8日",
        static_remarks=(
            "・本見積価格には、要件定義・設計・開発・テスト・公開作業が含まれます。\n"
            "* 月額保守・運用サービスはシステム公開後より開始となります。\n"
            "本見積価格には、要件定義・設計・開発・テスト・公開作業が含まれます。\n"
            "開発内容に変更が生じた場合は、別途お見積りとなります。"
        ),
    )

    assert items == [
        "本見積価格には、要件定義・設計・開発・テスト・公開作業が含まれます。",
        "月額保守・運用サービスはシステム公開後より開始となります。",
        "開発内容に変更が生じた場合は、別途お見積りとなります。",
    ]
    assert all("*" not in item for item in items)


def test_formal_quotation_populated_numbers():
    ctx = sample_formal_quotation_context()
    assert ctx["quote_number"] == "BAI-20260629-001"
    assert ctx["registration_number"] == "T9010001234562"


def test_formal_quotation_en_labels():
    ctx = sample_formal_quotation_context(locale="en")
    assert ctx["labels"]["item"] == "Item"
    assert ctx["labels"]["unit"] == "Qty"
    assert ctx["labels"]["development_cost"] == "Software Development Cost"


def test_formal_quotation_uses_company_config_overrides():
    from datetime import datetime
    from types import SimpleNamespace

    from app.exports.quotation_context import build_formal_quotation_context
    from tests.unit.export_fixtures import sample_estimate_with_calculation

    company = SimpleNamespace(
        postal_code="100-0001",
        address="東京都千代田区1-1\nテストビル",
        tel="03-9999-0000",
        email="ops@example.com",
        bank_details_ja="カスタム銀行\n普通 999",
        bank_details_en="Custom Bank\nOrdinary 999",
    )
    ctx = build_formal_quotation_context(
        sample_estimate_with_calculation(),
        "ja",
        generated_at=datetime(2026, 6, 29),
        rate_card_name="Rate Card Default",
        rate_card_version_number=2,
        rate_card_effective_date=datetime(2026, 1, 1),
        export_revision=1,
        company_config=company,
        logo_src="data:image/png;base64,abc",
        logo_bytes=b"png",
        logo_ext="png",
        quotation_number="BAI-20260629-001",
        registration_number="T9010001234562",
    )
    assert ctx["company"]["postal_code"] == "100-0001"
    assert ctx["company"]["tel"] == "03-9999-0000"
    assert ctx["company"]["email"] == "ops@example.com"
    assert "テストビル" in ctx["company"]["address_lines"]
    assert ctx["bank_details"] == "カスタム銀行\n普通 999"
    assert ctx["logo_src"].startswith("data:image/png")
    assert ctx["logo_ext"] == "png"
