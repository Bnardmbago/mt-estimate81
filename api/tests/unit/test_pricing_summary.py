from app.exports.pricing_summary import build_campaign_terms, build_pricing_summary


def test_build_pricing_summary_without_discount_metadata():
    calculation = {"nrc": {"total_jpy": 700000}}
    summary = build_pricing_summary(calculation, "en", issue_date="June 7, 2026")
    assert summary["has_discount"] is False
    assert summary["nrc_discounted_total_jpy"] == 700000


def test_build_pricing_summary_with_discount_metadata():
    calculation = {
        "nrc": {"total_jpy": 700000},
        "nrc_original_total_jpy": 1000000,
        "discount_rate_applied": 0.30,
        "discount_amount_jpy": 300000,
    }
    summary = build_pricing_summary(calculation, "en", issue_date="June 7, 2026")
    assert summary["has_discount"] is True
    assert summary["nrc_original_total_jpy"] == 1000000
    assert summary["discount_percent_display"] == 30
    assert summary["discount_display"] == "30% OFF (-¥300,000)"
    assert "¥700,000" in summary["campaign_terms"]
    assert "June 7, 2026" in summary["campaign_terms"]


def test_build_campaign_terms_ja():
    terms = build_campaign_terms("ja", 7248984, "2026年6月7日")
    assert "2026年6月7日" in terms
    assert "¥7,248,984" in terms
    assert "1か月" in terms
