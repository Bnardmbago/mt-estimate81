from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.i18n.localized_content import resolve_localized_dict
from app.models.estimate import Estimate, EstimateStatus
from app.rate_cards.complexity import (
    ComplexityLevel,
    NRC_RC_TIER_BASE_AMOUNTS,
    ProjectComplexityProfile,
    score_project_complexity,
)
from app.rate_cards.cost_breakdown_hints import build_cost_breakdown_hints
from app.rate_cards.rc_items import STANDARD_RC_TEMPLATES
from app.rate_cards.normalize import line_item_amount

NrcRcSource = Literal["derived", "rate_card_tune", "manual", "rate_card"]


class NrcRcLineItem(BaseModel):
    name: str = Field(min_length=1)
    amount: int = Field(default=0, ge=0)
    category: str | None = None
    service_description: str | None = None


class NrcRcAssumptions(BaseModel):
    setup_cost_items: list[NrcRcLineItem] = Field(default_factory=list)
    monthly_rc_items: list[NrcRcLineItem] = Field(default_factory=list)
    source: NrcRcSource = "derived"
    complexity_level: ComplexityLevel | None = None


def _coerce_level(profile: dict[str, Any] | ProjectComplexityProfile | None) -> ComplexityLevel:
    if profile is None:
        return "medium"
    if isinstance(profile, ProjectComplexityProfile):
        return profile.level
    level = profile.get("level")
    if level in ("low", "medium", "high"):
        return level
    return "medium"


def _monthly_from_tier(level: ComplexityLevel) -> list[dict[str, Any]]:
    tier_monthly = NRC_RC_TIER_BASE_AMOUNTS[level]["monthly_rc_items"]
    items: list[dict[str, Any]] = []
    for template in STANDARD_RC_TEMPLATES:
        category_key = str(template["category"])
        row = dict(template)
        row["amount"] = int(tier_monthly.get(category_key, 0))
        items.append(row)
    return items


def _setup_from_tier(level: ComplexityLevel) -> list[dict[str, Any]]:
    return [dict(item) for item in NRC_RC_TIER_BASE_AMOUNTS[level]["setup_cost_items"]]


def _hint_targets_setup(hint: str) -> tuple[str | None, int]:
    lowered = hint.casefold()
    if any(token in lowered for token in ("integration", "third-party", "third party", "pci", "payment")):
        return "Third party", 1
    if any(token in lowered for token in ("migration", "data", "compliance", "security", "audit", "identity", "auth")):
        return "Infrastructure", 1
    if any(token in lowered for token in ("tool", "environment", "license", "software")):
        return "Tooling", 1
    return "Infrastructure", 0


def _hint_targets_monthly_category(hint: str) -> str:
    lowered = hint.casefold()
    if "monitor" in lowered or "incident" in lowered or "uptime" in lowered:
        return "system_monitoring"
    if "backup" in lowered or "disaster" in lowered or "recovery" in lowered:
        return "backup"
    if "security" in lowered or "compliance" in lowered or "vulnerab" in lowered:
        return "security"
    if "support" in lowered or "maintenance" in lowered:
        return "maintenance_support"
    if any(token in lowered for token in ("host", "cloud", "infra", "server", "database", "api", "saas", "license", "subscription", "payment", "gateway")):
        return "cloud_infrastructure"
    return "cloud_infrastructure"


def _bump_setup_item(items: list[dict[str, Any]], name: str, amount: int) -> None:
    for item in items:
        if str(item.get("name", "")).strip().casefold() == name.casefold():
            item["amount"] = int(item.get("amount", 0)) + amount
            return
    items.append({"name": name, "amount": amount})


def _bump_monthly_category(items: list[dict[str, Any]], category_key: str, amount: int) -> None:
    for item in items:
        if str(item.get("category", "")).strip() == category_key:
            item["amount"] = int(item.get("amount", 0)) + amount
            return
    for template in STANDARD_RC_TEMPLATES:
        if str(template.get("category")) == category_key:
            row = dict(template)
            row["amount"] = amount
            items.append(row)
            return
    items.append({"name": category_key.replace("_", " ").title(), "amount": amount, "category": category_key})


def _apply_labor_setup_cap(
    setup_items: list[dict[str, Any]],
    *,
    level: ComplexityLevel,
    labor_jpy: int | None,
) -> list[dict[str, Any]]:
    cap_ratio = NRC_RC_TIER_BASE_AMOUNTS[level].get("labor_setup_cap_ratio")
    if cap_ratio is None or labor_jpy is None or labor_jpy <= 0:
        return setup_items

    cap = int(labor_jpy * float(cap_ratio))
    total = sum(line_item_amount(item) for item in setup_items)
    if total <= cap:
        return setup_items

    if cap <= 0:
        return [{"name": item["name"], "amount": 0} for item in setup_items]

    scale = cap / total
    scaled: list[dict[str, Any]] = []
    remainder = cap
    for index, item in enumerate(setup_items):
        amount = int(line_item_amount(item))
        if index == len(setup_items) - 1:
            scaled_amount = remainder
        else:
            scaled_amount = int(round(amount * scale))
            remainder -= scaled_amount
        row = {"name": str(item.get("name", "Item")), "amount": max(0, scaled_amount)}
        scaled.append(row)
    return scaled


def derive_nrc_rc_assumptions(
    *,
    complexity_profile: dict[str, Any] | ProjectComplexityProfile,
    form_data: dict[str, Any] | None = None,
    extracted_data: dict[str, Any] | None = None,
    labor_jpy: int | None = None,
) -> dict[str, Any]:
    level = _coerce_level(complexity_profile)
    tier = NRC_RC_TIER_BASE_AMOUNTS[level]
    setup_items = _setup_from_tier(level)
    monthly_items = _monthly_from_tier(level)

    hints = build_cost_breakdown_hints(
        form_data or {},
        extracted_data,
        complexity_profile if isinstance(complexity_profile, dict) else complexity_profile.model_dump(),
    )
    setup_increment = int(tier["hint_setup_increment"])
    monthly_increment = int(tier["hint_monthly_increment"])

    for hint in hints.get("setup_suggestions") or []:
        target_name, priority = _hint_targets_setup(str(hint))
        if target_name is None:
            continue
        amount = setup_increment if priority else setup_increment // 2
        _bump_setup_item(setup_items, target_name, amount)

    for hint in hints.get("monthly_suggestions") or []:
        category_key = _hint_targets_monthly_category(str(hint))
        _bump_monthly_category(monthly_items, category_key, monthly_increment)

    setup_items = _apply_labor_setup_cap(setup_items, level=level, labor_jpy=labor_jpy)

    assumptions = NrcRcAssumptions(
        setup_cost_items=[NrcRcLineItem.model_validate(item) for item in setup_items],
        monthly_rc_items=[NrcRcLineItem.model_validate(item) for item in monthly_items],
        source="derived",
        complexity_level=level,
    )
    return assumptions.model_dump()


def assumptions_from_rate_card_settings(
    settings: dict[str, Any],
    *,
    source: NrcRcSource = "rate_card_tune",
    complexity_level: ComplexityLevel | None = None,
) -> dict[str, Any]:
    setup_items = [
        NrcRcLineItem(
            name=str(item.get("name", "Item")),
            amount=line_item_amount(item),
        )
        for item in settings.get("setup_cost_items") or []
        if str(item.get("name", "")).strip()
    ]
    monthly_items = [
        NrcRcLineItem(
            name=str(item.get("name", "Item")),
            amount=line_item_amount(item),
            category=item.get("category"),
            service_description=item.get("service_description"),
        )
        for item in settings.get("monthly_rc_items") or []
        if str(item.get("name", "")).strip()
    ]
    return NrcRcAssumptions(
        setup_cost_items=setup_items,
        monthly_rc_items=monthly_items,
        source=source,
        complexity_level=complexity_level,
    ).model_dump()


def prefer_rate_card_nrc_rc_after_extract(
    *,
    derived: dict[str, Any],
    rate_card_settings: dict[str, Any] | None,
    complexity_level: ComplexityLevel | None = None,
) -> dict[str, Any]:
    """Use the linked rate card's NRC/RC when present (including on re-extract).

    Saving a rate card disables auto-tune, so re-extract previously kept complexity
    tiers and ignored card edits. Prefer the card whenever it has cost line items.
    """
    if not rate_card_settings:
        return derived
    setup = rate_card_settings.get("setup_cost_items") or []
    monthly = rate_card_settings.get("monthly_rc_items") or []
    if not setup and not monthly:
        return derived
    return assumptions_from_rate_card_settings(
        rate_card_settings,
        source="rate_card",
        complexity_level=complexity_level,
    )


def _has_assumption_items(assumptions: dict[str, Any] | None) -> bool:
    if not assumptions:
        return False
    setup = assumptions.get("setup_cost_items") or []
    monthly = assumptions.get("monthly_rc_items") or []
    return bool(setup or monthly)


def estimate_labor_jpy(feature_items: list[dict[str, Any]], hourly_rate: int = 8000) -> int:
    total_hours = sum(float(item.get("hours", 0) or 0) for item in feature_items)
    return int(total_hours * hourly_rate)


def resolve_nrc_rc_assumptions(
    estimate: Estimate,
    *,
    feature_items: list[dict[str, Any]] | None = None,
    form_data: dict[str, Any] | None = None,
    extracted_data: dict[str, Any] | None = None,
    rate_card_settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stored = dict(estimate.nrc_rc_assumptions or {})
    if _has_assumption_items(stored):
        return stored

    locale = estimate.locale or "ja"
    resolved_extracted = extracted_data
    if resolved_extracted is None and estimate.extracted_data is not None:
        resolved_extracted = resolve_localized_dict(estimate.extracted_data, locale, locale)

    resolved_form = form_data or {}
    if not resolved_form and estimate.form_data is not None:
        resolved_form = resolve_localized_dict(estimate.form_data, locale, locale)

    items = feature_items
    if items is None:
        items = [
            {
                "name": item.name,
                "hours": float(item.hours),
                "phase": item.phase,
                "role": item.role,
            }
            for item in estimate.feature_items
        ]

    profile_dict: dict[str, Any] | None = None
    if isinstance(resolved_extracted, dict):
        profile_dict = resolved_extracted.get("complexity_profile")
        if isinstance(profile_dict, dict):
            pass
        else:
            profile_dict = None

    if profile_dict is None and items:
        profile = score_project_complexity(
            feature_items=items,
            extracted_data=resolved_extracted or {},
            form_data=resolved_form,
        )
        profile_dict = profile.model_dump()
    elif profile_dict is None:
        profile_dict = {"level": "medium"}

    labor_jpy = estimate_labor_jpy(items) if items else None
    if estimate.status in (
        EstimateStatus.REVIEW.value,
        EstimateStatus.CALCULATED.value,
        EstimateStatus.EXPORTED.value,
        EstimateStatus.COMPLETED.value,
    ):
        return derive_nrc_rc_assumptions(
            complexity_profile=profile_dict,
            form_data=resolved_form,
            extracted_data=resolved_extracted,
            labor_jpy=labor_jpy,
        )

    if rate_card_settings:
        return assumptions_from_rate_card_settings(
            rate_card_settings,
            source="rate_card",
            complexity_level=_coerce_level(profile_dict),
        )

    return derive_nrc_rc_assumptions(
        complexity_profile=profile_dict,
        form_data=resolved_form,
        extracted_data=resolved_extracted,
        labor_jpy=labor_jpy,
    )


def apply_nrc_rc_assumptions_to_settings(
    settings: dict[str, Any],
    assumptions: dict[str, Any],
) -> dict[str, Any]:
    updated = dict(settings)
    updated["setup_cost_items"] = [
        item.model_dump() if isinstance(item, NrcRcLineItem) else dict(item)
        for item in (assumptions.get("setup_cost_items") or [])
    ]
    updated["monthly_rc_items"] = [
        item.model_dump() if isinstance(item, NrcRcLineItem) else dict(item)
        for item in (assumptions.get("monthly_rc_items") or [])
    ]
    return updated
