from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Literal

from app.calculation.schemas import RateCardSettings
from app.rate_cards.defaults import DEFAULT_CURRENCY, DEFAULT_REGION, Currency, Region

if TYPE_CHECKING:
    from app.fx.service import FxService

REGIONS: tuple[Region, ...] = ("japan", "philippines", "usa")
CURRENCIES: tuple[Currency, ...] = ("JPY", "USD", "PHP")

REGION_NATIVE_CURRENCY: dict[Region, Currency] = {
    "japan": "JPY",
    "philippines": "PHP",
    "usa": "USD",
}

HOURS_PER_DAY = 8

# Midpoint hourly rates per standard role in the region's native currency.
REGIONAL_STANDARD_RATES: dict[Region, dict[str, int]] = {
    "japan": {
        "pm": 12000,
        "project_manager": 12000,
        "developer": 8000,
        "senior_developer": 10000,
        "qa": 6500,
        "qa_engineer": 6500,
        "business_analyst": 9000,
        "devops": 9500,
        "designer": 7500,
        "architect": 11000,
        "tech_lead": 10500,
    },
    "philippines": {
        "pm": 950,
        "project_manager": 950,
        "developer": 650,
        "senior_developer": 850,
        "qa": 500,
        "qa_engineer": 500,
        "business_analyst": 700,
        "devops": 750,
        "designer": 550,
        "architect": 900,
        "tech_lead": 850,
    },
    "usa": {
        "pm": 120,
        "project_manager": 120,
        "developer": 85,
        "senior_developer": 110,
        "qa": 70,
        "qa_engineer": 70,
        "business_analyst": 95,
        "devops": 100,
        "designer": 80,
        "architect": 115,
        "tech_lead": 110,
    },
}


def _normalize_role_key(name: str) -> str:
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def _lookup_regional_hourly(region: Region, role_name: str) -> int | None:
    rates = REGIONAL_STANDARD_RATES[region]
    key = _normalize_role_key(role_name)
    if key in rates:
        return rates[key]
    if key == "ba" and "business_analyst" in rates:
        return rates["business_analyst"]
    return None


async def apply_regional_standard(
    settings: RateCardSettings,
    region: Region,
    target_currency: Currency,
    fx_service: FxService,
) -> RateCardSettings:
    native_currency = REGION_NATIVE_CURRENCY[region]
    updated_roles = []

    for role in settings.roles:
        native_hourly = _lookup_regional_hourly(region, role.name)
        if native_hourly is None:
            updated_roles.append(role)
            continue

        hourly = native_hourly
        if native_currency != target_currency:
            hourly = await fx_service.convert_amount(
                native_hourly,
                native_currency,
                target_currency,
            )

        updated_roles.append(
            role.model_copy(
                update={
                    "hourly_rate": hourly,
                    "daily_rate": hourly * HOURS_PER_DAY,
                }
            )
        )

    return settings.model_copy(
        update={
            "roles": updated_roles,
            "region": region,
            "currency": target_currency,
        }
    )
