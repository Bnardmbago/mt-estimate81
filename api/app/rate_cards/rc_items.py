from __future__ import annotations

from typing import Any

from app.calculation.rc_detailed import RC_CATEGORY_KEYS, resolve_rc_category_key
from app.rate_cards.defaults import DEFAULT_RATE_CARD_SETTINGS
from app.rate_cards.normalize import line_item_amount

STANDARD_RC_TEMPLATES: tuple[dict[str, Any], ...] = tuple(
    dict(item) for item in DEFAULT_RATE_CARD_SETTINGS["monthly_rc_items"]
)


def allocate_rc_item_amounts(item: dict[str, Any]) -> list[tuple[str, int]]:
    """Map a monthly RC line item to one or more category buckets and amounts."""
    amount = line_item_amount(item)
    if amount <= 0:
        return []

    explicit = item.get("category")
    if explicit:
        return [(resolve_rc_category_key(item), amount)]

    name = str(item.get("name") or "").lower()
    has_monitor = "monitor" in name
    has_support = "support" in name or "maintenance" in name

    if has_monitor and has_support:
        monitoring = amount // 2
        return [
            ("system_monitoring", monitoring),
            ("maintenance_support", amount - monitoring),
        ]

    return [(resolve_rc_category_key(item), amount)]


def ensure_standard_monthly_rc_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge arbitrary RC line items into the five standard category rows."""
    amounts = {key: 0 for key in RC_CATEGORY_KEYS}
    descriptions: dict[str, str] = {}

    for item in items:
        for category_key, amount in allocate_rc_item_amounts(item):
            if category_key not in amounts:
                category_key = "cloud_infrastructure"
            amounts[category_key] += amount
            if item.get("service_description") and category_key not in descriptions:
                descriptions[category_key] = str(item["service_description"])

    merged: list[dict[str, Any]] = []
    for template in STANDARD_RC_TEMPLATES:
        category_key = str(template["category"])
        row = dict(template)
        row["amount"] = amounts.get(category_key, 0)
        if category_key in descriptions:
            row["service_description"] = descriptions[category_key]
        merged.append(row)

    return merged
