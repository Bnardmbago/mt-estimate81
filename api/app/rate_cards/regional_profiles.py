from __future__ import annotations

import re
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


# Maps normalized role labels to keys in REGIONAL_STANDARD_RATES.
ROLE_KEY_ALIASES: dict[str, str] = {
    "project_manager": "pm",
    "program_manager": "pm",
    "software_engineer": "developer",
    "software_developer": "developer",
    "sw_engineer": "developer",
    "programmer": "developer",
    "engineer": "developer",
    "dev": "developer",
    "quality_assurance": "qa",
    "quality_assurance_engineer": "qa",
    "qa_engineer": "qa",
    "test_engineer": "qa",
    "tester": "qa",
    "ba": "business_analyst",
    "senior_software_engineer": "senior_developer",
    "lead_developer": "tech_lead",
    "technical_lead": "tech_lead",
    "ui_designer": "designer",
    "ux_designer": "designer",
    "ui_ux_designer": "designer",
    "devops_engineer": "devops",
    "solutions_architect": "architect",
    "data_analyst": "business_analyst",
    "market_research_analyst": "business_analyst",
    "research_analyst": "business_analyst",
    "research_lead": "pm",
    "data_quality_specialist": "qa",
    "legal_specialist": "business_analyst",
    "compliance_specialist": "business_analyst",
    "taxonomy_specialist": "business_analyst",
}


def _strip_parenthetical(name: str) -> str:
    return re.sub(r"\s*\([^)]*\)", "", name).strip()


def _role_name_candidates(role_name: str) -> list[str]:
    """Expand AI-generated labels like 'PM (Lead)' or 'QA / Data Quality'."""
    name = role_name.strip()
    candidates: list[str] = []

    def add(raw: str) -> None:
        raw = raw.strip()
        if not raw:
            return
        if raw not in candidates:
            candidates.append(raw)
        stripped = _strip_parenthetical(raw)
        if stripped and stripped not in candidates:
            candidates.append(stripped)

    add(name)
    for segment in re.split(r"[/,&]|(?:\s+and\s+)", name):
        add(segment)
    stripped_name = _strip_parenthetical(name)
    if stripped_name != name:
        for segment in re.split(r"[/,&]|(?:\s+and\s+)", stripped_name):
            add(segment)
    return candidates


def _normalize_role_key(name: str) -> str:
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def _resolve_regional_rate_key(region: Region, role_key: str) -> str | None:
    rates = REGIONAL_STANDARD_RATES[region]
    if role_key in rates:
        return role_key
    alias = ROLE_KEY_ALIASES.get(role_key)
    if alias and alias in rates:
        return alias
    return None


def _lookup_regional_hourly(region: Region, role_name: str) -> int | None:
    for candidate in _role_name_candidates(role_name):
        key = _normalize_role_key(candidate)
        resolved = _resolve_regional_rate_key(region, key)
        if resolved is not None:
            return REGIONAL_STANDARD_RATES[region][resolved]
    return None


async def apply_regional_standard(
    settings: RateCardSettings,
    region: Region,
    target_currency: Currency,
    fx_service: FxService,
) -> tuple[RateCardSettings, int]:
    native_currency = REGION_NATIVE_CURRENCY[region]
    updated_roles = []
    roles_updated = 0

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

        roles_updated += 1
        updated_roles.append(
            role.model_copy(
                update={
                    "hourly_rate": hourly,
                    "daily_rate": hourly * HOURS_PER_DAY,
                }
            )
        )

    updated = settings.model_copy(
        update={
            "roles": updated_roles,
            "region": region,
            "currency": target_currency,
        }
    )
    return updated, roles_updated
