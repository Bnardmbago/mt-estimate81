from __future__ import annotations

from typing import Literal

Region = Literal["japan", "philippines", "usa"]
Currency = Literal["JPY", "USD", "PHP"]

HOURS_PER_DAY = 8

DEFAULT_STANDARD_ROLE_NAMES: tuple[tuple[str, str], ...] = (
    ("Tech Lead", "tech_lead"),
    ("Senior Engineer", "senior_developer"),
    ("Full Stack Engineer", "full_stack_developer"),
    ("Engineer", "developer"),
)

STANDARD_ROLE_COUNT = len(DEFAULT_STANDARD_ROLE_NAMES)

STANDARD_ROLE_HINTS: dict[str, tuple[str, ...]] = {
    "tech_lead": (
        "tech lead",
        "tech_lead",
        "technical lead",
        "pm",
        "project manager",
        "project_manager",
    ),
    "senior_developer": ("senior engineer", "senior_developer", "senior developer"),
    "full_stack_developer": (
        "full stack engineer",
        "full_stack_developer",
        "full stack developer",
        "fullstack developer",
    ),
    "developer": (
        "engineer",
        "developer",
        "dev",
        "programmer",
        "qa",
        "qa engineer",
        "tester",
        "quality assurance",
        "test",
    ),
    "pm": ("pm", "project manager", "project_manager"),
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
    """Normalize rate card roles to the standard four-role set for the region."""
    from app.calculation.role_allocation import resolve_feature_item_role
    from app.rate_cards.defaults import DEFAULT_REGION

    region = settings.get("region") or DEFAULT_REGION
    if region not in REGIONAL_STANDARD_RATES:
        region = DEFAULT_REGION

    defaults = default_roles_for_region(region)  # type: ignore[arg-type]
    standard_rates = {str(role["name"]): 1 for role in defaults}
    best_hourly: dict[str, int] = {}

    for role in settings.get("roles") or []:
        name = str(role.get("name", "")).strip()
        if not name:
            continue
        hourly = int(role.get("hourly_rate") or role.get("hourly_rate_jpy") or 0)
        mapped = resolve_feature_item_role(name, standard_rates)
        if mapped is None or hourly <= 0:
            continue
        prior = best_hourly.get(mapped)
        if prior is None or hourly > prior:
            best_hourly[mapped] = hourly

    consolidated: list[dict[str, int | str]] = []
    for default_role in defaults:
        display = str(default_role["name"])
        hourly = best_hourly.get(display, int(default_role["hourly_rate"]))
        consolidated.append(
            {
                "name": display,
                "hourly_rate": hourly,
                "daily_rate": hourly * HOURS_PER_DAY,
            }
        )

    return {**settings, "roles": consolidated}
