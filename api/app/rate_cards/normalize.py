from typing import Any

from pydantic import BaseModel, Field

HOURS_PER_DAY = 8

LEGACY_SETUP_LABELS = {
    "infrastructure_jpy": "Infrastructure",
    "tooling_jpy": "Tooling",
    "third_party_jpy": "Third party",
}


class SetupCostItem(BaseModel):
    name: str = Field(min_length=1)
    amount_jpy: int = Field(ge=0)


class SetupCosts(BaseModel):
    infrastructure_jpy: int = 0
    tooling_jpy: int = 0
    third_party_jpy: int = 0


def normalize_settings_dict(raw: dict[str, Any]) -> dict[str, Any]:
    settings = dict(raw)

    if not settings.get("development_approach"):
        settings["development_approach"] = "traditional"

    roles = settings.get("roles", [])
    normalized_roles = []
    for role in roles:
        role_copy = dict(role)
        hourly = int(role_copy.get("hourly_rate_jpy", 0))
        if role_copy.get("daily_rate_jpy") is None:
            role_copy["daily_rate_jpy"] = hourly * HOURS_PER_DAY
        else:
            role_copy["daily_rate_jpy"] = int(role_copy["daily_rate_jpy"])
        normalized_roles.append(role_copy)
    settings["roles"] = normalized_roles

    if not settings.get("setup_cost_items"):
        legacy = settings.get("setup_costs")
        if isinstance(legacy, dict):
            settings["setup_cost_items"] = [
                {
                    "name": LEGACY_SETUP_LABELS[key],
                    "amount_jpy": int(legacy.get(key, 0) or 0),
                }
                for key in LEGACY_SETUP_LABELS
            ]

    return settings


def setup_items_total(setup_cost_items: list[SetupCostItem]) -> int:
    return sum(item.amount_jpy for item in setup_cost_items)
