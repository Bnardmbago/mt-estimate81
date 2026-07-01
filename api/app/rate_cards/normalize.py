from typing import Any, Literal

from pydantic import BaseModel, Field

from app.rate_cards.defaults import DEFAULT_CURRENCY, DEFAULT_REGION

HOURS_PER_DAY = 8

CostBreakdownMode = Literal["standard", "flexible"]

LEGACY_SETUP_LABELS = {
    "infrastructure_jpy": "Infrastructure",
    "tooling_jpy": "Tooling",
    "third_party_jpy": "Third party",
}


class SetupCostItem(BaseModel):
    name: str = Field(min_length=1)
    amount: int = Field(ge=0)


class SetupCosts(BaseModel):
    infrastructure_jpy: int = 0
    tooling_jpy: int = 0
    third_party_jpy: int = 0


def _migrate_role(role: dict[str, Any]) -> dict[str, Any]:
    role_copy = dict(role)
    if "hourly_rate" not in role_copy and role_copy.get("hourly_rate_jpy") is not None:
        role_copy["hourly_rate"] = int(role_copy["hourly_rate_jpy"])
    if "daily_rate" not in role_copy and role_copy.get("daily_rate_jpy") is not None:
        role_copy["daily_rate"] = int(role_copy["daily_rate_jpy"])

    hourly = int(role_copy.get("hourly_rate", 0) or 0)
    if role_copy.get("daily_rate") is None:
        role_copy["daily_rate"] = hourly * HOURS_PER_DAY
    else:
        role_copy["daily_rate"] = int(role_copy["daily_rate"])
    role_copy["hourly_rate"] = hourly
    return role_copy


def _migrate_line_item(item: dict[str, Any]) -> dict[str, Any]:
    item_copy = dict(item)
    if "amount" not in item_copy and item_copy.get("amount_jpy") is not None:
        item_copy["amount"] = int(item_copy["amount_jpy"])
    item_copy["amount"] = int(item_copy.get("amount", 0) or 0)
    if item_copy.get("category") is not None:
        item_copy["category"] = str(item_copy["category"]).strip() or None
    if item_copy.get("service_description") is not None:
        item_copy["service_description"] = str(item_copy["service_description"]).strip() or None
    return item_copy


def is_flexible_cost_breakdown(settings: dict[str, Any]) -> bool:
    return settings.get("cost_breakdown_mode") == "flexible"


def normalize_settings_dict(raw: dict[str, Any]) -> dict[str, Any]:
    settings = dict(raw)
    has_legacy_jpy = any(
        key.endswith("_jpy")
        for key in settings.keys()
        if key not in {"setup_costs"}
    ) or any(
        isinstance(role, dict) and ("hourly_rate_jpy" in role or "daily_rate_jpy" in role)
        for role in settings.get("roles", [])
    ) or any(
        isinstance(item, dict) and "amount_jpy" in item
        for collection in ("setup_cost_items", "monthly_rc_items")
        for item in settings.get(collection, [])
    )

    if not settings.get("development_approach"):
        settings["development_approach"] = "ai_assisted"

    if "region" not in settings:
        settings["region"] = "japan" if has_legacy_jpy else DEFAULT_REGION
    if "currency" not in settings:
        settings["currency"] = "JPY"

    settings["roles"] = [_migrate_role(role) for role in settings.get("roles", [])]

    if not settings.get("setup_cost_items"):
        legacy = settings.get("setup_costs")
        if isinstance(legacy, dict):
            settings["setup_cost_items"] = [
                {
                    "name": LEGACY_SETUP_LABELS[key],
                    "amount": int(legacy.get(key, 0) or 0),
                }
                for key in LEGACY_SETUP_LABELS
            ]

    settings["setup_cost_items"] = [
        _migrate_line_item(item) for item in settings.get("setup_cost_items", [])
    ]
    settings["monthly_rc_items"] = [
        _migrate_line_item(item) for item in settings.get("monthly_rc_items", [])
    ]
    for item in settings["monthly_rc_items"]:
        if str(item.get("name", "")).strip().lower() == "maintenance support":
            item["name"] = "Maintenance and Support"
    if settings["monthly_rc_items"] and not is_flexible_cost_breakdown(settings):
        from app.rate_cards.rc_items import ensure_standard_monthly_rc_items

        settings["monthly_rc_items"] = ensure_standard_monthly_rc_items(
            settings["monthly_rc_items"]
        )
    if "default_maintenance_monthly_jpy" not in settings:
        settings["default_maintenance_monthly_jpy"] = 0
    else:
        settings["default_maintenance_monthly_jpy"] = int(
            settings.get("default_maintenance_monthly_jpy") or 0
        )

    from app.rate_cards.regional_profiles import patch_jpy_specialist_role_floors
    from app.rate_cards.standard_rates import ensure_standard_roles

    settings, _ = patch_jpy_specialist_role_floors(settings)
    settings = ensure_standard_roles(settings)

    return settings


def setup_items_total(setup_cost_items: list[SetupCostItem]) -> int:
    return sum(item.amount for item in setup_cost_items)


def line_item_amount(item: dict[str, Any] | SetupCostItem) -> int:
    if isinstance(item, SetupCostItem):
        return item.amount
    if item.get("amount") is not None:
        return int(item["amount"])
    return int(item.get("amount_jpy", 0) or 0)


def role_hourly_rate(role: dict[str, Any]) -> int:
    if role.get("hourly_rate") is not None:
        return int(role["hourly_rate"])
    return int(role.get("hourly_rate_jpy", 0) or 0)
