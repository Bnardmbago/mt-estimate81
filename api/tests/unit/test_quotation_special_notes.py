from app.admin.quotation_notes_config import QuotationNotesConfig
from app.exports.pricing_summary import (
    apply_quotation_special_notes,
    build_pricing_summary,
    render_special_notes,
)


def test_render_special_notes_substitutes_known_placeholders():
    template = "Date: {issue_date}, price: {special_price}, unknown: {missing}"
    result = render_special_notes(
        template,
        {
            "issue_date": "2026年6月29日",
            "special_price": "¥700,000 （税抜）",
        },
    )
    assert result == "Date: 2026年6月29日, price: ¥700,000 （税抜）, unknown: {missing}"


def test_apply_quotation_special_notes_overrides_title_and_body():
    pricing_summary = build_pricing_summary(
        {
            "nrc": {"total_jpy": 700000},
            "nrc_original_total_jpy": 1000000,
            "discount_rate_applied": 0.30,
            "discount_amount_jpy": 300000,
        },
        "ja",
        issue_date="2026年6月29日",
    )
    notes_config = QuotationNotesConfig(
        title_ja="特記事項",
        title_en="Special Notes",
        body_ja="発行日 {issue_date}、特別価格 {special_price}。追加メモ。",
        body_en="Issue {issue_date}, price {special_price}.",
    )

    updated = apply_quotation_special_notes(
        pricing_summary,
        "ja",
        "2026年6月29日",
        notes_config,
    )

    assert updated["campaign_terms_title"] == "特記事項"
    assert "2026年6月29日" in updated["campaign_terms"]
    assert "¥700,000" in updated["campaign_terms"]
    assert "追加メモ。" in updated["campaign_terms"]


def test_apply_quotation_special_notes_no_op_without_discount():
    pricing_summary = {"has_discount": False, "nrc_discounted_total_jpy": 700000}
    notes_config = QuotationNotesConfig(
        title_ja="特記事項",
        title_en="Special Notes",
        body_ja="ignored",
        body_en="ignored",
    )

    updated = apply_quotation_special_notes(
        pricing_summary,
        "ja",
        "2026年6月29日",
        notes_config,
    )

    assert updated == pricing_summary
