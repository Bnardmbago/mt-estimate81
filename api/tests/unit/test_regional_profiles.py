from decimal import Decimal

import pytest

from app.calculation.schemas import RateCardSettings
from app.rate_cards.regional_profiles import apply_regional_standard


class FakeFxService:
    def __init__(self, rates: dict[tuple[str, str], Decimal]):
        self.rates = rates

    async def convert_amount(self, amount: int, from_ccy: str, to_ccy: str) -> int:
        if from_ccy == to_ccy:
            return amount
        rate = self.rates[(from_ccy, to_ccy)]
        return int(Decimal(amount) * rate)


@pytest.fixture
def base_settings() -> RateCardSettings:
    return RateCardSettings.model_validate(
        {
            "roles": [
                {"name": "PM", "hourly_rate": 0, "daily_rate": 0},
                {"name": "developer", "hourly_rate": 0, "daily_rate": 0},
                {"name": "QA", "hourly_rate": 0, "daily_rate": 0},
            ],
            "phases": [{"name": "development", "percentage": 1.0}],
            "development_approach": "traditional",
            "contingency_rate": 0.1,
            "overhead_rate": 0.1,
            "monthly_rc_items": [],
            "productivity": {"hours_per_feature_default": 40},
            "tax_rate": 0.1,
            "region": "philippines",
            "currency": "JPY",
        }
    )


@pytest.mark.asyncio
async def test_apply_philippines_native_to_jpy(base_settings):
    fx = FakeFxService({("PHP", "JPY"): Decimal("2.5")})
    updated = await apply_regional_standard(base_settings, "philippines", "JPY", fx)

    pm = next(role for role in updated.roles if role.name == "PM")
    developer = next(role for role in updated.roles if role.name == "developer")
    assert pm.hourly_rate == int(950 * 2.5)
    assert developer.hourly_rate == int(650 * 2.5)
    assert updated.region == "philippines"
    assert updated.currency == "JPY"


@pytest.mark.asyncio
async def test_apply_usa_to_usd_keeps_native_amounts(base_settings):
    fx = FakeFxService({})
    updated = await apply_regional_standard(base_settings, "usa", "USD", fx)

    pm = next(role for role in updated.roles if role.name == "PM")
    assert pm.hourly_rate == 120
    assert pm.daily_rate == 960
    assert updated.currency == "USD"


@pytest.mark.asyncio
async def test_apply_japan_to_jpy(base_settings):
    fx = FakeFxService({})
    updated = await apply_regional_standard(base_settings, "japan", "JPY", fx)

    developer = next(role for role in updated.roles if role.name == "developer")
    assert developer.hourly_rate == 8000
