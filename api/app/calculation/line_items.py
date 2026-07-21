from typing import Any

from app.calculation.rc_detailed import (
    build_detailed_rc_breakdown,
    get_markup_rate_from_calculation,
)
from app.calculation.schemas import MonthlyRcItem, SetupCostItem
from app.rate_cards.normalize import line_item_amount


def _role_nrc_category(role: str) -> str:
    """Map role labor into client-facing NRC categories for quotations."""
    normalized = role.strip().lower()
    if normalized in {"pm", "project manager"} or "pm" in normalized or "project" in normalized:
        return "Project Management"
    if "business" in normalized or normalized in {"ba", "analyst"}:
        return "Business Analysis"
    # Fold QA/testing into Development — client quotations highlight delivery work,
    # not a separate QA line item.
    if "devops" in normalized or "sre" in normalized or "infra" in normalized:
        return "DevOps"
    return "Development"


def _setup_nrc_category(name: str) -> str:
    normalized = name.strip().lower()
    if "security" in normalized:
        return "Security Setup"
    if "tool" in normalized or "software" in normalized:
        return "Software Setup"
    if "data" in normalized and "migr" in normalized:
        return "Data Migration"
    # Only dedicated training/enablement — not "AI Model Training Setup".
    if normalized in {"training", "training setup", "user training", "研修"} or (
        "training" in normalized
        and "model" not in normalized
        and "ai" not in normalized
    ):
        return "Training"
    return "Infrastructure Setup"


def _rc_category(name: str) -> str:
    normalized = name.strip().lower()
    if "host" in normalized or "cloud" in normalized:
        return "Cloud Hosting"
    if "database" in normalized or "db" in normalized:
        return "Database"
    if "ai" in normalized or "api" in normalized or "openai" in normalized:
        return "AI API Usage"
    if "monitor" in normalized:
        return "Monitoring"
    if "backup" in normalized:
        return "Backup"
    if "license" in normalized or "software" in normalized:
        return "Software Licenses"
    if "security" in normalized:
        return "Security"
    if "support" in normalized or "maintenance" in normalized:
        return "Maintenance"
    return "Other"


def build_nrc_line_items(
    role_breakdown: list[dict[str, Any]],
    setup_items: list[dict[str, Any] | SetupCostItem],
    contingency_jpy: int,
    overhead_jpy: int,
) -> list[dict[str, Any]]:
    category_totals: dict[str, int] = {}

    for row in role_breakdown:
        category = _role_nrc_category(str(row["role"]))
        category_totals[category] = category_totals.get(category, 0) + int(row["cost_jpy"])

    for item in setup_items:
        if isinstance(item, SetupCostItem):
            name = item.name
            amount = item.amount
        else:
            name = str(item.get("name", "Setup"))
            amount = line_item_amount(item)
        category = _setup_nrc_category(name)
        category_totals[category] = category_totals.get(category, 0) + amount

    line_items = [
        {"category": category, "item": category, "cost_jpy": cost}
        for category, cost in sorted(category_totals.items())
        if cost > 0
    ]

    if contingency_jpy:
        line_items.append(
            {"category": "Contingency", "item": "Contingency", "cost_jpy": contingency_jpy}
        )
    if overhead_jpy:
        line_items.append({"category": "Overhead", "item": "Overhead", "cost_jpy": overhead_jpy})

    return line_items


def build_rc_line_items(
    monthly_items: list[dict[str, Any]],
    maintenance_jpy: int,
) -> list[dict[str, Any]]:
    line_items: list[dict[str, Any]] = []

    for item in monthly_items:
        monthly = line_item_amount(item)
        name = str(item.get("name", "Item"))
        line_items.append(
            {
                "category": _rc_category(name),
                "item": name,
                "monthly_jpy": monthly,
                "annual_jpy": monthly * 12,
            }
        )

    if maintenance_jpy:
        line_items.append(
            {
                "category": "Maintenance",
                "item": "Maintenance and Support",
                "monthly_jpy": maintenance_jpy,
                "annual_jpy": maintenance_jpy * 12,
            }
        )

    return line_items


def _is_maintenance_support_row(row: dict[str, Any]) -> bool:
    if row.get("is_maintenance"):
        return True
    category = str(row.get("category") or "")
    item = str(row.get("item") or "").lower().replace("_", " ")
    return category == "Maintenance" and item in {
        "maintenance support",
        "maintenance and support",
        "maintenance",
    }


def _maintenance_export_row(maintenance_jpy: int) -> dict[str, Any]:
    return {
        "category": "Maintenance",
        "item": "Maintenance and Support",
        "monthly_jpy": maintenance_jpy,
        "annual_jpy": maintenance_jpy * 12,
        "is_maintenance": True,
    }


def _line_items_from_rc_monthly(rc: dict[str, Any]) -> list[dict[str, Any]]:
    line_items: list[dict[str, Any]] = []
    for item in rc.get("monthly_items") or []:
        monthly_jpy = line_item_amount(item)
        name = str(item.get("name", "Item"))
        line_items.append(
            {
                "category": _rc_category(name),
                "item": name,
                "monthly_jpy": monthly_jpy,
                "annual_jpy": monthly_jpy * 12,
                "is_maintenance": False,
            }
        )
    return line_items


def _line_items_from_rc_line_items(rc_line_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    line_items: list[dict[str, Any]] = []
    for row in rc_line_items:
        monthly_jpy = int(row.get("monthly_jpy") or 0)
        line_items.append(
            {
                "category": str(row.get("category") or "Other"),
                "item": str(row.get("item") or "Item"),
                "monthly_jpy": monthly_jpy,
                "annual_jpy": int(row.get("annual_jpy") or monthly_jpy * 12),
                "is_maintenance": _is_maintenance_support_row(row),
            }
        )
    return line_items


def _ensure_maintenance_row(
    line_items: list[dict[str, Any]],
    maintenance_jpy: int,
) -> list[dict[str, Any]]:
    if any(row.get("is_maintenance") for row in line_items):
        return line_items
    return [*line_items, _maintenance_export_row(maintenance_jpy)]


def _line_items_monthly_total(line_items: list[dict[str, Any]]) -> int:
    return sum(int(row.get("monthly_jpy") or 0) for row in line_items)


def build_rc_export_breakdown(
    calculation: dict[str, Any],
    *,
    locale: str = "en",
) -> dict[str, Any]:
    markup_rate = get_markup_rate_from_calculation(calculation)
    return build_detailed_rc_breakdown(
        calculation,
        locale=locale,
        markup_rate=markup_rate,
    )


def enrich_phase_breakdown(phase_breakdown: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for row in phase_breakdown:
        hours = float(row.get("hours", 0))
        enriched.append(
            {
                **row,
                "days": round(hours / 8, 2),
            }
        )
    return enriched


def serialize_jpy_line_item(
    item: dict[str, Any] | SetupCostItem | MonthlyRcItem,
) -> dict[str, Any]:
    if isinstance(item, (SetupCostItem, MonthlyRcItem)):
        amount = int(item.amount or 0)
        name = item.name
    else:
        amount = line_item_amount(item)
        name = str(item.get("name", "Item"))
    return {
        "name": name,
        "amount": amount,
        "amount_jpy": amount,
    }


def normalize_calculation_result(calculation: dict[str, Any] | None) -> dict[str, Any] | None:
    if not calculation:
        return calculation

    normalized = dict(calculation)
    nrc = dict(normalized.get("nrc") or {})
    nrc["setup_items"] = [
        serialize_jpy_line_item(item) for item in nrc.get("setup_items") or []
    ]
    normalized["nrc"] = nrc

    rc = dict(normalized.get("rc") or {})
    rc["monthly_items"] = [
        serialize_jpy_line_item(item) for item in rc.get("monthly_items") or []
    ]
    normalized["rc"] = rc
    return normalized


def sanitize_calculation_result_for_user(
    calculation: dict[str, Any] | None,
    *,
    include_internal_pricing: bool,
) -> dict[str, Any] | None:
    if not calculation:
        return calculation

    if include_internal_pricing:
        return calculation

    sanitized = dict(calculation)
    sanitized.pop("internal_pricing", None)
    return sanitized
