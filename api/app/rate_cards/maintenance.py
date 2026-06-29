from __future__ import annotations

from typing import Any

from app.calculation.role_allocation import resolve_support_role_hourly_rate
from app.rate_cards.normalize import role_hourly_rate


def derive_default_maintenance_monthly_jpy(
    maintenance_assumptions: dict[str, Any] | None,
    settings: dict[str, Any],
) -> int:
    assumptions = maintenance_assumptions or {}
    hours = float(assumptions.get("monthly_support_hours") or 0)
    role_rates = {
        str(role.get("name", "")): role_hourly_rate(role)
        for role in settings.get("roles") or []
    }
    _, hourly = resolve_support_role_hourly_rate(
        role_rates,
        str(assumptions.get("support_role") or "developer"),
    )
    return int(hours * hourly)


def apply_default_maintenance_to_settings(
    settings: dict[str, Any],
    maintenance_assumptions: dict[str, Any] | None,
) -> dict[str, Any]:
    updated = dict(settings)
    updated["default_maintenance_monthly_jpy"] = derive_default_maintenance_monthly_jpy(
        maintenance_assumptions,
        updated,
    )
    return updated
