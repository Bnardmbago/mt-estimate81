from app.calculation.engine import calculate_estimate
from app.calculation.markup import compute_internal_pricing
from app.calculation.line_items import sanitize_calculation_result_for_user
from tests.unit.test_calculation_engine import SAMPLE_RATE_CARD
from app.calculation.schemas import FeatureItemInput


def test_compute_internal_pricing_scales_each_line_item():
    items = [FeatureItemInput(name="Auth", hours=40, phase="development", role="developer")]
    maintenance = {"monthly_support_hours": 20, "support_role": "developer"}
    result = calculate_estimate(
        items,
        SAMPLE_RATE_CARD,
        maintenance,
        rate_card_version_id="v1",
        discount_rate=0.30,
    )

    internal = compute_internal_pricing(result, 0.30)
    assert internal is not None
    assert internal["markup_rate_applied"] == 0.30
    visible_nrc = result.nrc["total_jpy"]
    visible_rc_monthly = result.rc["monthly_total_jpy"]
    assert internal["nrc_total_jpy"] == int(round(visible_nrc * 1.3))
    assert internal["rc_monthly_total_jpy"] == int(round(visible_rc_monthly * 1.3))
    assert internal["first_year_total_jpy"] == (
        internal["nrc_total_jpy"] + internal["rc_annual_total_jpy"]
    )


def test_compute_internal_pricing_returns_none_when_rate_zero():
    items = [FeatureItemInput(name="Auth", hours=40, phase="development", role="developer")]
    result = calculate_estimate(items, SAMPLE_RATE_CARD, {}, rate_card_version_id="v1")
    assert compute_internal_pricing(result, 0.0) is None


def test_compute_internal_pricing_does_not_mutate_visible_result():
    items = [FeatureItemInput(name="Auth", hours=40, phase="development", role="developer")]
    result = calculate_estimate(items, SAMPLE_RATE_CARD, {}, rate_card_version_id="v1")
    visible_total = result.nrc["total_jpy"]
    compute_internal_pricing(result, 0.30)
    assert result.nrc["total_jpy"] == visible_total


def test_sanitize_calculation_result_strips_internal_pricing_for_non_admin():
    payload = {
        "nrc": {"total_jpy": 100},
        "internal_pricing": {"nrc_total_jpy": 130},
    }
    sanitized = sanitize_calculation_result_for_user(payload, include_internal_pricing=False)
    assert "internal_pricing" not in sanitized
    assert sanitized["nrc"]["total_jpy"] == 100


def test_sanitize_calculation_result_keeps_internal_pricing_for_admin():
    payload = {
        "nrc": {"total_jpy": 100},
        "internal_pricing": {"nrc_total_jpy": 130},
    }
    sanitized = sanitize_calculation_result_for_user(payload, include_internal_pricing=True)
    assert sanitized["internal_pricing"]["nrc_total_jpy"] == 130
