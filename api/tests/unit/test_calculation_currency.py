import pytest

from app.calculation.currency import rate_card_settings_to_jpy
from app.calculation.engine import calculate_estimate
from app.calculation.schemas import FeatureItemInput, RateCardSettings


class FakeFxService:
    async def build_snapshot(self):
        return {"USD_JPY": 150.0, "fetched_at": "2026-06-19T00:00:00+00:00"}

    async def convert_amount(self, amount: int, from_ccy: str, to_ccy: str) -> int:
        if from_ccy == to_ccy:
            return amount
        if from_ccy == "USD" and to_ccy == "JPY":
            return amount * 150
        raise ValueError(f"Unsupported pair {from_ccy}->{to_ccy}")


@pytest.mark.asyncio
async def test_rate_card_settings_to_jpy_for_usd_card():
    settings = RateCardSettings.model_validate(
        {
            "roles": [{"name": "developer", "hourly_rate": 100, "daily_rate": 800}],
            "phases": [{"name": "development", "percentage": 1.0}],
            "development_approach": "traditional",
            "contingency_rate": 0.0,
            "overhead_rate": 0.0,
            "monthly_rc_items": [{"name": "hosting", "amount": 10}],
            "setup_cost_items": [{"name": "Infra", "amount": 20}],
            "productivity": {"hours_per_feature_default": 40},
            "tax_rate": 0.1,
            "currency": "USD",
            "region": "usa",
        }
    )

    jpy_settings, snapshot = await rate_card_settings_to_jpy(settings, FakeFxService())
    assert jpy_settings.currency == "JPY"
    assert jpy_settings.roles[0].hourly_rate == 15000
    assert jpy_settings.monthly_rc_items[0].amount == 1500
    assert snapshot["USD_JPY"] == 150.0

    result = calculate_estimate(
        [FeatureItemInput(name="Auth", hours=10, phase="development", role="developer")],
        jpy_settings,
        {},
        rate_card_version_id="v1",
    )
    assert result.nrc["labor_jpy"] == 10 * 15000
