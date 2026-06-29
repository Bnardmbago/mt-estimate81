from __future__ import annotations

from typing import Literal

Region = Literal["japan", "philippines", "usa"]
Currency = Literal["JPY", "USD", "PHP"]

HOURS_PER_DAY = 8

DEFAULT_STANDARD_ROLE_NAMES: tuple[tuple[str, str], ...] = (
    ("PM", "pm"),
    ("developer", "developer"),
    ("QA", "qa"),
)

STANDARD_ROLE_HINTS: dict[str, tuple[str, ...]] = {
    "pm": ("pm", "project manager", "project_manager"),
    "developer": ("developer", "dev", "engineer", "programmer"),
    "qa": ("qa", "qa engineer", "tester", "quality assurance", "test"),
}

REGIONAL_STANDARD_RATES: dict[Region, dict[str, int]] = {
    "japan": {
        "pm": 12000,
        "project_manager": 12000,
        "developer": 8000,
        "senior_developer": 10000,
        "frontend_developer": 8500,
        "backend_developer": 8500,
        "full_stack_developer": 9000,
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
        "frontend_developer": 650,
        "backend_developer": 650,
        "full_stack_developer": 700,
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
        "frontend_developer": 85,
        "backend_developer": 85,
        "full_stack_developer": 95,
        "qa": 70,
        "qa_engineer": 70,
        "business_analyst": 95,
        "devops": 100,
        "designer": 80,
        "architect": 115,
        "tech_lead": 110,
    },
}


def default_roles_for_region(region: Region) -> list[dict[str, int | str]]:
    rates = REGIONAL_STANDARD_RATES[region]
    roles: list[dict[str, int | str]] = []
    for display_name, rate_key in DEFAULT_STANDARD_ROLE_NAMES:
        hourly = rates[rate_key]
        roles.append(
            {
                "name": display_name,
                "hourly_rate": hourly,
                "daily_rate": hourly * HOURS_PER_DAY,
            }
        )
    return roles


def patch_settings_standard_roles_for_region(
    settings: dict,
    region: Region,
    *,
    currency: Currency | None = None,
) -> dict:
    updated = dict(settings)
    updated["region"] = region
    if currency is not None:
        updated["currency"] = currency

    templates = {
        str(role["name"]).strip().lower(): role for role in default_roles_for_region(region)
    }
    patched_roles: list[dict] = []
    for role in updated.get("roles") or []:
        role_copy = dict(role)
        name_key = str(role_copy.get("name", "")).strip().lower()
        if name_key in templates:
            template = templates[name_key]
            role_copy["hourly_rate"] = template["hourly_rate"]
            role_copy["daily_rate"] = template["daily_rate"]
            role_copy.pop("hourly_rate_jpy", None)
            role_copy.pop("daily_rate_jpy", None)
        patched_roles.append(role_copy)
    updated["roles"] = patched_roles
    return updated


def ensure_standard_roles(settings: dict) -> dict:
    """Add PM, developer, and QA from regional defaults when the rate card omits them."""
    from app.calculation.role_allocation import resolve_rate_card_role
    from app.rate_cards.defaults import DEFAULT_REGION
    from app.rate_cards.regional_profiles import role_canonical_keys

    region = settings.get("region") or DEFAULT_REGION
    if region not in REGIONAL_STANDARD_RATES:
        region = DEFAULT_REGION

    roles = [dict(role) for role in settings.get("roles") or []]
    role_rates = {
        str(role.get("name", "")): 1 for role in roles if str(role.get("name", "")).strip()
    }
    defaults = default_roles_for_region(region)  # type: ignore[arg-type]
    defaults_by_key = {
        rate_key: defaults[index] for index, (_display, rate_key) in enumerate(DEFAULT_STANDARD_ROLE_NAMES)
    }

    for _display, rate_key in DEFAULT_STANDARD_ROLE_NAMES:
        hints = STANDARD_ROLE_HINTS.get(rate_key, (rate_key,))
        if resolve_rate_card_role(role_rates, hints):
            continue
        target_keys = role_canonical_keys(rate_key)
        if any(role_canonical_keys(name) & target_keys for name in role_rates):
            continue
        default_role = dict(defaults_by_key[rate_key])
        roles.append(default_role)
        role_rates[str(default_role["name"])] = 1

    return {**settings, "roles": roles}
