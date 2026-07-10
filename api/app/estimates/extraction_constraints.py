from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol

from app.ai.schemas import FeatureItemSuggestion
from app.calculation.engine import HOURS_PER_EFFORT_DAY
from app.estimates.budget_comparison import _parse_client_budget_jpy
from app.estimates.delivery_schedule import delivery_schedule_target_working_days

BindingConstraint = Literal["budget", "schedule"]

LABOR_SHARE_OF_BUDGET = 0.65
DEFAULT_BLENDED_HOURLY_RATE_JPY = 8000
MIN_FEATURE_HOURS = 0.5

DELIVERY_SCHEDULE_LABELS: dict[str, dict[str, str]] = {
    "asap": {"en": "ASAP", "ja": "できるだけ早く"},
    "within_1_3_months": {"en": "Within 1–3 months", "ja": "1〜3か月以内"},
    "within_3_6_months": {"en": "Within 3–6 months", "ja": "3〜6か月以内"},
    "within_6_12_months": {"en": "Within 6–12 months", "ja": "6〜12か月以内"},
    "over_12_months": {"en": "Over 12 months", "ja": "12か月以上"},
    "flexible": {"en": "Flexible", "ja": "未定・相談したい"},
}


class _HasSuggestedHours(Protocol):
    suggested_hours: float


@dataclass(frozen=True)
class ExtractionConstraints:
    client_budget_jpy: int | None
    max_labor_jpy: int | None
    blended_hourly_rate_jpy: int
    max_hours_budget: float | None
    delivery_schedule: str | None
    target_working_days: int | None
    max_hours_schedule: float | None
    max_hours: float
    binding_constraint: BindingConstraint | None


@dataclass(frozen=True)
class ConstraintFeasibility:
    requires_confirmation: bool
    budget_below_minimum: bool
    schedule_below_minimum: bool
    original_total_hours: float
    max_hours_cap: float
    binding_constraint: BindingConstraint | None


def _blended_hourly_rate_jpy(rate_card_roles: list[dict[str, Any]] | None) -> int:
    if not rate_card_roles:
        return DEFAULT_BLENDED_HOURLY_RATE_JPY

    rates: list[int] = []
    for role in rate_card_roles:
        hourly = role.get("hourly_rate")
        if hourly is not None:
            try:
                parsed = int(hourly)
                if parsed > 0:
                    rates.append(parsed)
                    continue
            except (TypeError, ValueError):
                pass
        daily = role.get("daily_rate")
        if daily is not None:
            try:
                parsed_daily = int(daily)
                if parsed_daily > 0:
                    rates.append(parsed_daily // HOURS_PER_EFFORT_DAY)
            except (TypeError, ValueError):
                pass

    if not rates:
        return DEFAULT_BLENDED_HOURLY_RATE_JPY
    return int(sum(rates) / len(rates))


def parse_extraction_constraints(
    form_data: dict[str, Any],
    rate_card_roles: list[dict[str, Any]] | None,
) -> ExtractionConstraints | None:
    client_budget_jpy = _parse_client_budget_jpy(form_data.get("client_budget"))
    blended_rate = _blended_hourly_rate_jpy(rate_card_roles)

    max_labor_jpy: int | None = None
    max_hours_budget: float | None = None
    if client_budget_jpy is not None:
        max_labor_jpy = int(client_budget_jpy * LABOR_SHARE_OF_BUDGET)
        max_hours_budget = max_labor_jpy / blended_rate

    delivery_schedule_raw = form_data.get("delivery_schedule")
    delivery_schedule = str(delivery_schedule_raw).strip() if delivery_schedule_raw else None
    if delivery_schedule == "":
        delivery_schedule = None

    target_working_days = delivery_schedule_target_working_days(delivery_schedule)
    max_hours_schedule: float | None = None
    if target_working_days is not None:
        max_hours_schedule = float(target_working_days * HOURS_PER_EFFORT_DAY)

    caps: list[tuple[float, BindingConstraint]] = []
    if max_hours_budget is not None:
        caps.append((max_hours_budget, "budget"))
    if max_hours_schedule is not None:
        caps.append((max_hours_schedule, "schedule"))

    if not caps:
        return None

    max_hours, binding = min(caps, key=lambda item: item[0])
    return ExtractionConstraints(
        client_budget_jpy=client_budget_jpy,
        max_labor_jpy=max_labor_jpy,
        blended_hourly_rate_jpy=blended_rate,
        max_hours_budget=max_hours_budget,
        delivery_schedule=delivery_schedule,
        target_working_days=target_working_days,
        max_hours_schedule=max_hours_schedule,
        max_hours=max_hours,
        binding_constraint=binding,
    )


def _schedule_label(slug: str | None, locale: Literal["ja", "en"]) -> str:
    if not slug:
        return ""
    labels = DELIVERY_SCHEDULE_LABELS.get(slug, {})
    return labels.get(locale) or labels.get("en") or slug


def _binding_constraint_label(
    constraints: ExtractionConstraints,
    locale: Literal["ja", "en"],
) -> str:
    if constraints.binding_constraint == "budget":
        return "予算" if locale == "ja" else "budget"
    if constraints.binding_constraint == "schedule":
        return "納期" if locale == "ja" else "delivery schedule"
    return ""


def _constraint_template_context(
    constraints: ExtractionConstraints,
    locale: Literal["ja", "en"],
) -> dict[str, str]:
    budget_section = ""
    if constraints.client_budget_jpy is not None and constraints.max_hours_budget is not None:
        if locale == "ja":
            budget_section = (
                f"- 予算: ¥{constraints.client_budget_jpy:,} "
                f"(想定労務費上限 ¥{constraints.max_labor_jpy:,}、"
                f"平均単価 ¥{constraints.blended_hourly_rate_jpy:,}/h → "
                f"最大 {constraints.max_hours_budget:.1f} 時間)\n"
            )
        else:
            budget_section = (
                f"- Budget: ¥{constraints.client_budget_jpy:,} "
                f"(target labor cap ¥{constraints.max_labor_jpy:,} at "
                f"¥{constraints.blended_hourly_rate_jpy:,}/h blended rate → "
                f"max {constraints.max_hours_budget:.1f} hours)\n"
            )

    schedule_section = ""
    if constraints.delivery_schedule and constraints.target_working_days is not None:
        label = _schedule_label(constraints.delivery_schedule, locale)
        if locale == "ja":
            schedule_section = (
                f"- 希望納期: {label} ({constraints.target_working_days} 稼働日 → "
                f"最大 {constraints.max_hours_schedule:.1f} 時間、順次作業の上限)\n"
            )
        else:
            schedule_section = (
                f"- Delivery schedule: {label} ({constraints.target_working_days} working days → "
                f"max {constraints.max_hours_schedule:.1f} hours, sequential upper bound)\n"
            )

    return {
        "client_budget_jpy": f"{constraints.client_budget_jpy:,}"
        if constraints.client_budget_jpy is not None
        else "",
        "max_labor_jpy": f"{constraints.max_labor_jpy:,}"
        if constraints.max_labor_jpy is not None
        else "",
        "blended_hourly_rate_jpy": f"{constraints.blended_hourly_rate_jpy:,}",
        "max_hours_budget": f"{constraints.max_hours_budget:.1f}"
        if constraints.max_hours_budget is not None
        else "",
        "delivery_schedule_label": _schedule_label(constraints.delivery_schedule, locale),
        "target_working_days": str(constraints.target_working_days or ""),
        "max_hours_schedule": f"{constraints.max_hours_schedule:.1f}"
        if constraints.max_hours_schedule is not None
        else "",
        "max_hours": f"{constraints.max_hours:.1f}",
        "binding_constraint_label": _binding_constraint_label(constraints, locale),
        "budget_section": budget_section,
        "schedule_section": schedule_section,
    }


def format_constraints_for_prompt(
    constraints: ExtractionConstraints,
    locale: Literal["ja", "en"],
    *,
    template: str | None = None,
) -> str:
    from app.ai.extraction_constraint_prompts import get_default_constraint_user_prompt_template

    resolved_template = template or get_default_constraint_user_prompt_template(locale)
    context = _constraint_template_context(constraints, locale)
    try:
        return resolved_template.format(**context)
    except KeyError:
        return resolved_template


def assess_constraint_feasibility(
    items: list[_HasSuggestedHours],
    constraints: ExtractionConstraints | None,
) -> ConstraintFeasibility | None:
    if constraints is None:
        return None

    original_total = sum(float(item.suggested_hours) for item in items)
    budget_below = (
        constraints.max_hours_budget is not None
        and original_total > constraints.max_hours_budget
    )
    schedule_below = (
        constraints.max_hours_schedule is not None
        and original_total > constraints.max_hours_schedule
    )
    requires_confirmation = original_total > constraints.max_hours

    return ConstraintFeasibility(
        requires_confirmation=requires_confirmation,
        budget_below_minimum=budget_below,
        schedule_below_minimum=schedule_below,
        original_total_hours=round(original_total, 2),
        max_hours_cap=round(constraints.max_hours, 2),
        binding_constraint=constraints.binding_constraint,
    )


def constraints_to_dict(constraints: ExtractionConstraints) -> dict[str, Any]:
    return {
        "client_budget_jpy": constraints.client_budget_jpy,
        "max_labor_jpy": constraints.max_labor_jpy,
        "blended_hourly_rate_jpy": constraints.blended_hourly_rate_jpy,
        "max_hours_budget": constraints.max_hours_budget,
        "delivery_schedule": constraints.delivery_schedule,
        "target_working_days": constraints.target_working_days,
        "max_hours_schedule": constraints.max_hours_schedule,
        "max_hours": constraints.max_hours,
        "binding_constraint": constraints.binding_constraint,
    }


def constraints_from_dict(data: dict[str, Any]) -> ExtractionConstraints:
    return ExtractionConstraints(
        client_budget_jpy=data.get("client_budget_jpy"),
        max_labor_jpy=data.get("max_labor_jpy"),
        blended_hourly_rate_jpy=int(data["blended_hourly_rate_jpy"]),
        max_hours_budget=data.get("max_hours_budget"),
        delivery_schedule=data.get("delivery_schedule"),
        target_working_days=data.get("target_working_days"),
        max_hours_schedule=data.get("max_hours_schedule"),
        max_hours=float(data["max_hours"]),
        binding_constraint=data.get("binding_constraint"),
    )


def _constraint_warning(
    constraints: ExtractionConstraints,
    original_hours: float,
    adjusted_hours: float,
    scale: float,
    locale: Literal["ja", "en"],
) -> str:
    if locale == "ja":
        binding = "予算" if constraints.binding_constraint == "budget" else "納期"
        return (
            f"クライアントの{binding}制約のため、抽出工数を {original_hours:.1f}h から "
            f"{adjusted_hours:.1f}h に調整しました (係数 {scale:.2f})。"
        )
    binding = "budget" if constraints.binding_constraint == "budget" else "delivery schedule"
    return (
        f"Feature hours were scaled from {original_hours:.1f}h to {adjusted_hours:.1f}h "
        f"(factor {scale:.2f}) to respect the client {binding} constraint."
    )


def apply_extraction_constraints(
    items: list[_HasSuggestedHours],
    constraints: ExtractionConstraints,
    *,
    locale: Literal["ja", "en"] = "en",
) -> tuple[list[_HasSuggestedHours], dict[str, Any]]:
    if not items:
        return items, {
            "client_budget_jpy": constraints.client_budget_jpy,
            "delivery_schedule": constraints.delivery_schedule,
            "target_working_days": constraints.target_working_days,
            "max_hours_cap": round(constraints.max_hours, 2),
            "original_total_hours": 0.0,
            "adjusted_total_hours": 0.0,
            "budget_limited": constraints.max_hours_budget is not None,
            "schedule_limited": constraints.max_hours_schedule is not None,
            "binding_constraint": constraints.binding_constraint,
            "applied_scale_factor": 1.0,
            "hours_scaled": False,
        }

    original_total = sum(float(item.suggested_hours) for item in items)
    if original_total <= constraints.max_hours:
        return items, {
            "client_budget_jpy": constraints.client_budget_jpy,
            "delivery_schedule": constraints.delivery_schedule,
            "target_working_days": constraints.target_working_days,
            "max_hours_cap": round(constraints.max_hours, 2),
            "original_total_hours": round(original_total, 2),
            "adjusted_total_hours": round(original_total, 2),
            "budget_limited": constraints.max_hours_budget is not None,
            "schedule_limited": constraints.max_hours_schedule is not None,
            "binding_constraint": constraints.binding_constraint,
            "applied_scale_factor": 1.0,
            "hours_scaled": False,
        }

    scale = constraints.max_hours / original_total
    adjusted_items: list[_HasSuggestedHours] = []
    for item in items:
        scaled_hours = max(MIN_FEATURE_HOURS, round(float(item.suggested_hours) * scale, 2))
        if isinstance(item, FeatureItemSuggestion):
            adjusted_items.append(
                item.model_copy(update={"suggested_hours": scaled_hours})
            )
        else:
            item.suggested_hours = scaled_hours
            adjusted_items.append(item)

    adjusted_total = sum(float(item.suggested_hours) for item in adjusted_items)
    report = {
        "client_budget_jpy": constraints.client_budget_jpy,
        "delivery_schedule": constraints.delivery_schedule,
        "target_working_days": constraints.target_working_days,
        "max_hours_cap": round(constraints.max_hours, 2),
        "original_total_hours": round(original_total, 2),
        "adjusted_total_hours": round(adjusted_total, 2),
        "budget_limited": constraints.max_hours_budget is not None,
        "schedule_limited": constraints.max_hours_schedule is not None,
        "binding_constraint": constraints.binding_constraint,
        "applied_scale_factor": round(scale, 4),
        "hours_scaled": True,
        "warning": _constraint_warning(
            constraints, original_total, adjusted_total, scale, locale
        ),
    }
    return adjusted_items, report
