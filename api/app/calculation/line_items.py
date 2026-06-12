from typing import Any

from app.calculation.schemas import RateCardSettings, SetupCostItem


def _role_nrc_category(role: str) -> str:
    normalized = role.strip().lower()
    if normalized in {"pm", "project manager"} or "pm" in normalized or "project" in normalized:
        return "Project Management"
    if "business" in normalized or normalized in {"ba", "analyst"}:
        return "Business Analysis"
    if "qa" in normalized or "test" in normalized or "quality" in normalized:
        return "QA"
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
    if "train" in normalized:
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
            amount = item.amount_jpy
        else:
            name = str(item.get("name", "Setup"))
            amount = int(item.get("amount_jpy", 0))
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
        monthly = int(item.get("amount_jpy", 0))
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
                "item": "Maintenance support",
                "monthly_jpy": maintenance_jpy,
                "annual_jpy": maintenance_jpy * 12,
            }
        )

    return line_items


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
