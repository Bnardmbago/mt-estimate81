from decimal import Decimal

import pytest

from app.calculation.schemas import RateCardSettings
from app.rate_cards.regional_profiles import apply_regional_standard, patch_roles_to_regional_standard


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
async def test_apply_philippines_native_to_jpy_converts_from_philippines_table(base_settings):
    fx = FakeFxService({("PHP", "JPY"): Decimal("2.5")})
    updated, roles_updated = await apply_regional_standard(base_settings, "philippines", "JPY", fx)

    pm = next(role for role in updated.roles if role.name == "PM")
    developer = next(role for role in updated.roles if role.name == "developer")
    qa = next(role for role in updated.roles if role.name == "QA")
    assert pm.hourly_rate == 2375
    assert developer.hourly_rate == 1625
    assert qa.hourly_rate == 1250
    assert updated.region == "philippines"
    assert updated.currency == "JPY"
    assert roles_updated == 3


@pytest.mark.asyncio
async def test_apply_philippines_native_to_php_uses_fx(base_settings):
    fx = FakeFxService({("PHP", "JPY"): Decimal("2.5")})
    updated, roles_updated = await apply_regional_standard(base_settings, "philippines", "PHP", fx)

    pm = next(role for role in updated.roles if role.name == "PM")
    developer = next(role for role in updated.roles if role.name == "developer")
    assert pm.hourly_rate == 950
    assert developer.hourly_rate == 650
    assert updated.region == "philippines"
    assert updated.currency == "PHP"
    assert roles_updated == 3


@pytest.mark.asyncio
async def test_apply_matches_common_ai_role_names(base_settings):
    settings = RateCardSettings.model_validate(
        {
            **base_settings.model_dump(),
            "roles": [
                {"name": "Project Manager", "hourly_rate": 0, "daily_rate": 0},
                {"name": "Software Engineer", "hourly_rate": 0, "daily_rate": 0},
                {"name": "Quality Assurance", "hourly_rate": 0, "daily_rate": 0},
            ],
        }
    )
    fx = FakeFxService({("PHP", "JPY"): Decimal("2.5")})
    updated, roles_updated = await apply_regional_standard(settings, "philippines", "JPY", fx)

    assert roles_updated == 3
    assert updated.roles[0].hourly_rate == 2375
    assert updated.roles[1].hourly_rate == 1625
    assert updated.roles[2].hourly_rate == 1250


@pytest.mark.asyncio
async def test_apply_usa_to_usd_keeps_native_amounts(base_settings):
    fx = FakeFxService({})
    updated, roles_updated = await apply_regional_standard(base_settings, "usa", "USD", fx)

    pm = next(role for role in updated.roles if role.name == "PM")
    assert roles_updated == 3
    assert pm.hourly_rate == 120
    assert pm.daily_rate == 960
    assert updated.currency == "USD"


def test_patch_roles_skips_when_region_currency_mismatch():
    settings, count = patch_roles_to_regional_standard(
        {
            "region": "philippines",
            "currency": "JPY",
            "roles": [{"name": "Engineer", "hourly_rate": 5000, "daily_rate": 40000}],
        }
    )
    assert count == 0
    assert settings["roles"][0]["hourly_rate"] == 5000


def test_patch_roles_to_regional_standard_japan_frontend_backend():
    settings, count = patch_roles_to_regional_standard(
        {
            "region": "japan",
            "currency": "JPY",
            "roles": [
                {"name": "Frontend Developer", "hourly_rate": 1719, "daily_rate": 13752},
                {"name": "Backend Developer", "hourly_rate": 1719, "daily_rate": 13752},
            ],
        }
    )

    assert count == 2
    assert settings["roles"][0]["hourly_rate"] == 8500
    assert settings["roles"][1]["hourly_rate"] == 8500


@pytest.mark.asyncio
async def test_apply_japan_frontend_and_backend_developer_rates():
    settings = RateCardSettings.model_validate(
        {
            "roles": [
                {"name": "Frontend Developer", "hourly_rate": 1719, "daily_rate": 13752},
                {"name": "Backend Developer", "hourly_rate": 1719, "daily_rate": 13752},
            ],
            "phases": [{"name": "development", "percentage": 1.0}],
            "development_approach": "traditional",
            "contingency_rate": 0.1,
            "overhead_rate": 0.1,
            "monthly_rc_items": [],
            "productivity": {"hours_per_feature_default": 40},
            "tax_rate": 0.1,
            "region": "japan",
            "currency": "JPY",
        }
    )
    fx = FakeFxService({})
    updated, roles_updated = await apply_regional_standard(settings, "japan", "JPY", fx)

    assert roles_updated == 2
    frontend = next(role for role in updated.roles if role.name == "Frontend Developer")
    backend = next(role for role in updated.roles if role.name == "Backend Developer")
    assert frontend.hourly_rate == 8500
    assert frontend.daily_rate == 68000
    assert backend.hourly_rate == 8500
    assert backend.daily_rate == 68000


@pytest.mark.asyncio
async def test_apply_japan_to_jpy(base_settings):
    fx = FakeFxService({})
    updated, _roles_updated = await apply_regional_standard(base_settings, "japan", "JPY", fx)

    developer = next(role for role in updated.roles if role.name == "developer")
    assert developer.hourly_rate == 8000


@pytest.mark.asyncio
async def test_apply_matches_composite_ai_role_names():
    settings = RateCardSettings.model_validate(
        {
            "roles": [
                {"name": "Project Manager (Research Lead)", "hourly_rate": 0, "daily_rate": 0},
                {"name": "Senior Developer (Architecture / Feasibility Review)", "hourly_rate": 0, "daily_rate": 0},
                {"name": "QA / Data Quality Specialist", "hourly_rate": 0, "daily_rate": 0},
                {"name": "Data Analyst / Taxonomy Specialist", "hourly_rate": 0, "daily_rate": 0},
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
    fx = FakeFxService({("PHP", "JPY"): Decimal("2.5")})
    updated, roles_updated = await apply_regional_standard(settings, "philippines", "JPY", fx)

    assert roles_updated == 4
    assert updated.roles[0].hourly_rate == 2375
    assert updated.roles[1].hourly_rate == 2125
    assert updated.roles[2].hourly_rate == 1250
    assert updated.roles[3].hourly_rate == 1750
