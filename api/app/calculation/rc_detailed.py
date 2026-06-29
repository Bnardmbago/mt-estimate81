from __future__ import annotations

from typing import Any

RC_CATEGORY_KEYS = (
    "cloud_infrastructure",
    "system_monitoring",
    "maintenance_support",
    "security",
    "backup",
)

RC_CATEGORY_CONTENT: dict[str, dict[str, dict[str, str]]] = {
    "en": {
        "cloud_infrastructure": {
            "category": "Cloud Infrastructure",
            "service_description": "Server & database usage",
        },
        "system_monitoring": {
            "category": "System Monitoring",
            "service_description": "24/7 monitoring & incident response",
        },
        "maintenance_support": {
            "category": "Maintenance and Support",
            "service_description": "Minor fixes & inquiry support",
        },
        "security": {
            "category": "Security",
            "service_description": "Security updates & vulnerability management",
        },
        "backup": {
            "category": "Backup",
            "service_description": "Data backup & restoration",
        },
    },
    "ja": {
        "cloud_infrastructure": {
            "category": "クラウドインフラ",
            "service_description": "サーバー・データベース利用",
        },
        "system_monitoring": {
            "category": "システム監視",
            "service_description": "24時間365日の監視・障害対応",
        },
        "maintenance_support": {
            "category": "メンテナンスとサポート",
            "service_description": "軽微な修正・問い合わせ対応",
        },
        "security": {
            "category": "セキュリティ",
            "service_description": "セキュリティ更新・脆弱性管理",
        },
        "backup": {
            "category": "バックアップ",
            "service_description": "データバックアップ・復旧",
        },
    },
}

_CATEGORY_ALIASES: dict[str, str] = {
    "cloud infrastructure": "cloud_infrastructure",
    "cloud hosting": "cloud_infrastructure",
    "cloud_infrastructure": "cloud_infrastructure",
    "infrastructure": "cloud_infrastructure",
    "hosting": "cloud_infrastructure",
    "database": "cloud_infrastructure",
    "system monitoring": "system_monitoring",
    "monitoring": "system_monitoring",
    "system_monitoring": "system_monitoring",
    "maintenance support": "maintenance_support",
    "maintenance and support": "maintenance_support",
    "maintenance": "maintenance_support",
    "maintenance_support": "maintenance_support",
    "support": "maintenance_support",
    "security": "security",
    "backup": "backup",
    "other": "cloud_infrastructure",
}


def _normalize_category_key(value: str) -> str:
    return value.strip().lower().replace("_", " ")


def resolve_rc_category_key(item: dict[str, Any]) -> str:
    explicit = item.get("category")
    if explicit:
        normalized = _normalize_category_key(str(explicit))
        if normalized in _CATEGORY_ALIASES:
            return _CATEGORY_ALIASES[normalized]
        compact = normalized.replace(" ", "_")
        if compact in RC_CATEGORY_KEYS:
            return compact

    name = str(item.get("name") or "").lower()
    if "monitor" in name:
        return "system_monitoring"
    if "backup" in name:
        return "backup"
    if "security" in name:
        return "security"
    if "support" in name or "maintenance" in name:
        return "maintenance_support"
    if any(token in name for token in ("host", "cloud", "infra", "gcp", "server", "database", "db")):
        return "cloud_infrastructure"
    return "cloud_infrastructure"


def _allocate_rc_buckets(calculation: dict[str, Any]) -> dict[str, int]:
    from app.rate_cards.rc_items import allocate_rc_item_amounts

    buckets = {key: 0 for key in RC_CATEGORY_KEYS}
    rc = calculation.get("rc") or {}
    maintenance_jpy = int(rc.get("maintenance_jpy") or 0)
    buckets["maintenance_support"] = maintenance_jpy

    for item in rc.get("monthly_items") or []:
        for bucket, amount in allocate_rc_item_amounts(item):
            if bucket == "maintenance_support" and maintenance_jpy > 0:
                buckets["maintenance_support"] += amount
            else:
                buckets[bucket] += amount

    return buckets


def _scale_jpy(value: int, multiplier: float) -> int:
    return int(round(float(value) * multiplier))


def _apply_markup_to_buckets(
    buckets: dict[str, int],
    *,
    markup_rate: float,
    monthly_total_at_cost: int,
) -> dict[str, int]:
    if markup_rate <= 0:
        return dict(buckets)

    multiplier = 1.0 + markup_rate
    marked = {key: _scale_jpy(amount, multiplier) for key, amount in buckets.items()}
    target_total = _scale_jpy(monthly_total_at_cost, multiplier)
    current_total = sum(marked.values())
    if current_total != target_total:
        diff = target_total - current_total
        adjust_key = "maintenance_support" if marked.get("maintenance_support", 0) > 0 else max(
            marked,
            key=lambda key: marked[key],
        )
        marked[adjust_key] = max(0, marked[adjust_key] + diff)
    return marked


def build_detailed_rc_breakdown(
    calculation: dict[str, Any],
    *,
    locale: str = "en",
    markup_rate: float = 0.0,
) -> dict[str, Any]:
    content_locale = locale if locale in RC_CATEGORY_CONTENT else "en"
    rc = calculation.get("rc") or {}
    monthly_total_at_cost = int(round(float(rc.get("monthly_total_jpy") or 0)))
    annual_total_at_cost = int(round(float(rc.get("annual_total_jpy") or 0)))

    buckets_at_cost = _allocate_rc_buckets(calculation)
    buckets = _apply_markup_to_buckets(
        buckets_at_cost,
        markup_rate=markup_rate,
        monthly_total_at_cost=monthly_total_at_cost,
    )

    multiplier = 1.0 + markup_rate if markup_rate > 0 else 1.0
    monthly_total_jpy = _scale_jpy(monthly_total_at_cost, multiplier)
    annual_total_jpy = monthly_total_jpy * 12

    line_items: list[dict[str, Any]] = []
    labels = RC_CATEGORY_CONTENT[content_locale]
    rc_monthly_items = rc.get("monthly_items") or []
    for key in RC_CATEGORY_KEYS:
        monthly_jpy = buckets[key]
        meta = labels[key]
        service_description = meta["service_description"]
        for monthly_item in rc_monthly_items:
            if resolve_rc_category_key(monthly_item) == key and monthly_item.get("service_description"):
                service_description = str(monthly_item["service_description"])
                break

        line_items.append(
            {
                "category_key": key,
                "category": meta["category"],
                "service_description": service_description,
                "item": meta["category"],
                "monthly_jpy": monthly_jpy,
                "monthly_jpy_at_cost": buckets_at_cost[key],
                "annual_jpy": monthly_jpy * 12,
                "is_maintenance": key == "maintenance_support",
            }
        )

    return {
        "line_items": line_items,
        "monthly_total_jpy": monthly_total_jpy,
        "annual_total_jpy": annual_total_jpy,
        "monthly_total_at_cost_jpy": monthly_total_at_cost,
        "annual_total_at_cost_jpy": annual_total_at_cost,
        "markup_rate_applied": markup_rate,
    }


def get_markup_rate_from_calculation(calculation: dict[str, Any]) -> float:
    detailed = calculation.get("rc_detailed_breakdown") or {}
    if detailed.get("markup_rate_applied") is not None:
        return float(detailed["markup_rate_applied"])
    internal = calculation.get("internal_pricing") or {}
    if internal.get("markup_rate_applied") is not None:
        return float(internal["markup_rate_applied"])
    return 0.0
