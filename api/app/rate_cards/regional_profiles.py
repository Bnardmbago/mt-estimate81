from __future__ import annotations

import re
from decimal import Decimal
from typing import TYPE_CHECKING, Literal

from app.calculation.schemas import RateCardSettings
from app.rate_cards.defaults import DEFAULT_CURRENCY, DEFAULT_REGION, Currency, Region
from app.rate_cards.standard_rates import (
    HOURS_PER_DAY,
    REGIONAL_STANDARD_RATES,
    default_roles_for_region,
    patch_settings_standard_roles_for_region,
)

if TYPE_CHECKING:
    from app.fx.service import FxService

REGIONS: tuple[Region, ...] = ("japan", "philippines", "usa")
CURRENCIES: tuple[Currency, ...] = ("JPY", "USD", "PHP")

REGION_NATIVE_CURRENCY: dict[Region, Currency] = {
    "japan": "JPY",
    "philippines": "PHP",
    "usa": "USD",
}

DEFAULT_STANDARD_ROLE_NAMES = (
    ("Tech Lead", "tech_lead"),
    ("Senior Engineer", "senior_developer"),
    ("Full Stack Engineer", "full_stack_developer"),
    ("Engineer", "developer"),
)


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
    "frontend_dev": "frontend_developer",
    "front_end_developer": "frontend_developer",
    "frontend_engineer": "frontend_developer",
    "ui_developer": "frontend_developer",
    "backend_dev": "backend_developer",
    "back_end_developer": "backend_developer",
    "backend_engineer": "backend_developer",
    "server_developer": "backend_developer",
    "fullstack_developer": "full_stack_developer",
    "full_stack_engineer": "full_stack_developer",
    "quality_assurance": "qa",
    "quality_assurance_engineer": "qa",
    "qa_engineer": "qa",
    "test_engineer": "qa",
    "tester": "qa",
    "ba": "business_analyst",
    "senior_software_engineer": "senior_developer",
    "senior_engineer": "senior_developer",
    "tech_lead": "tech_lead",
    "technical_lead": "tech_lead",
    "lead_developer": "tech_lead",
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


def role_canonical_keys(role_name: str) -> frozenset[str]:
    """Normalized role keys used to match feature labels to rate-card role names."""
    keys: set[str] = set()
    for candidate in _role_name_candidates(role_name):
        key = _normalize_role_key(candidate)
        keys.add(key)
        alias = ROLE_KEY_ALIASES.get(key)
        if alias:
            keys.add(alias)
        for region in REGIONS:
            resolved = _resolve_regional_rate_key(region, key)
            if resolved:
                keys.add(resolved)
    return frozenset(keys)


def standard_rate_region_for_currency(
    region: str | None,
    currency: str | None,
) -> Region | None:
    """Region whose standard rate table applies without FX conversion."""
    currency = currency or DEFAULT_CURRENCY
    if currency == "JPY":
        return "japan"
    if currency == "PHP":
        return "philippines"
    if currency == "USD":
        return "usa"
    if region in REGIONS and currency == REGION_NATIVE_CURRENCY.get(region):
        return region  # type: ignore[return-value]
    return None


JPY_SPECIALIST_ROLE_KEYS = frozenset(
    {"frontend_developer", "backend_developer", "full_stack_developer"}
)


def _japan_specialist_floor_hourly(role_name: str) -> int | None:
    for candidate in _role_name_candidates(role_name):
        key = _normalize_role_key(candidate)
        resolved = _resolve_regional_rate_key("japan", key)
        if resolved in JPY_SPECIALIST_ROLE_KEYS:
            return REGIONAL_STANDARD_RATES["japan"][resolved]
    return None


def patch_jpy_specialist_role_floors(settings: dict) -> tuple[dict, int]:
    """Raise underpriced frontend/backend/full-stack roles to Japan standard rates when billing in JPY."""
    if settings.get("currency") != "JPY":
        return settings, 0

    roles_updated = 0
    patched_roles: list[dict] = []
    for role in settings.get("roles") or []:
        role_copy = dict(role)
        floor = _japan_specialist_floor_hourly(str(role_copy.get("name", "")))
        current = int(role_copy.get("hourly_rate") or 0)
        if floor is not None and current < floor:
            role_copy["hourly_rate"] = floor
            role_copy["daily_rate"] = floor * HOURS_PER_DAY
            role_copy.pop("hourly_rate_jpy", None)
            role_copy.pop("daily_rate_jpy", None)
            roles_updated += 1
        patched_roles.append(role_copy)

    return {**settings, "roles": patched_roles}, roles_updated


def resolve_standard_rate_region(
    region: str | None,
    currency: str | None,
) -> Region | None:
    """Pick which regional rate table applies for silent normalization patches."""
    currency = currency or DEFAULT_CURRENCY
    if region in REGIONS and currency == REGION_NATIVE_CURRENCY.get(region):
        return region  # type: ignore[return-value]
    if region in REGIONS:
        return None
    return standard_rate_region_for_currency(region, currency)


def patch_roles_to_regional_standard(settings: dict) -> tuple[dict, int]:
    """Overwrite matched role hourly rates with regional standards (no FX conversion)."""
    rate_region = resolve_standard_rate_region(
        settings.get("region"),
        settings.get("currency"),
    )
    if rate_region is None:
        return settings, 0

    roles_updated = 0
    patched_roles: list[dict] = []
    for role in settings.get("roles") or []:
        role_copy = dict(role)
        native_hourly = _lookup_regional_hourly(rate_region, str(role_copy.get("name", "")))
        if native_hourly is not None:
            role_copy["hourly_rate"] = native_hourly
            role_copy["daily_rate"] = native_hourly * HOURS_PER_DAY
            role_copy.pop("hourly_rate_jpy", None)
            role_copy.pop("daily_rate_jpy", None)
            roles_updated += 1
        patched_roles.append(role_copy)

    return {**settings, "roles": patched_roles}, roles_updated


async def apply_regional_standard(
    settings: RateCardSettings,
    region: Region,
    target_currency: Currency,
    fx_service: FxService,
) -> tuple[RateCardSettings, int]:
    if region not in REGIONS:
        return settings, 0

    source_currency = REGION_NATIVE_CURRENCY[region]
    updated_roles = []
    roles_updated = 0

    for role in settings.roles:
        native_hourly = _lookup_regional_hourly(region, role.name)
        if native_hourly is None:
            updated_roles.append(role)
            continue

        hourly = native_hourly
        if source_currency != target_currency:
            hourly = await fx_service.convert_amount(
                native_hourly,
                source_currency,
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
