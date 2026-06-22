import math
from datetime import date

from app.calculation.development_approach import coerce_development_approach, get_approach_factors
from app.calculation.gantt import GanttFeatureItem, build_gantt_timeline
from app.calculation.line_items import (
    build_nrc_line_items,
    build_rc_line_items,
    enrich_phase_breakdown,
    serialize_jpy_line_item,
)
from app.calculation.discount import apply_estimate_discount
from app.calculation.role_allocation import allocate_role_hours_from_phases, resolve_feature_item_role
from app.calculation.schemas import (
    CalculationResult,
    FeatureItemInput,
    GanttFeatureItemInput,
    RateCardSettings,
)
from app.rate_cards.normalize import setup_items_total

HOURS_PER_EFFORT_DAY = 8


def role_personnel_count(
    hours: float,
    *,
    estimated_duration_days: float,
    total_days: float,
) -> int:
    if hours <= 0:
        return 0
    duration_days = estimated_duration_days if estimated_duration_days > 0 else total_days
    capacity = max(duration_days * HOURS_PER_EFFORT_DAY, HOURS_PER_EFFORT_DAY)
    return max(1, math.ceil(hours / capacity))


class CalculationError(Exception):
    def __init__(self, message: str, feature_item_name: str | None = None):
        self.feature_item_name = feature_item_name
        super().__init__(message)


def calculate_estimate(
    feature_items: list[FeatureItemInput],
    rate_card: RateCardSettings,
    maintenance: dict,
    rate_card_version_id: str,
    *,
    cost_drivers: list[dict] | None = None,
    project_start_date: date | None = None,
    gantt_feature_items: list[GanttFeatureItemInput] | None = None,
    discount_rate: float = 0.0,
) -> CalculationResult:
    approach = coerce_development_approach(rate_card.development_approach)
    approach_factors = get_approach_factors(approach)
    effort_multiplier = approach_factors.effort_multiplier
    team_size_multiplier = approach_factors.team_size_multiplier

    role_rates = {
        role.name: role.hourly_rate if role.hourly_rate else (role.hourly_rate_jpy or 0)
        for role in rate_card.roles
    }
    role_hours: dict[str, float] = {}
    total_hours = 0.0

    for item in feature_items:
        resolved_role = resolve_feature_item_role(
            item.role,
            role_rates,
            phase=item.phase,
        )
        if resolved_role is None:
            raise CalculationError(f"Unknown role '{item.role}'", feature_item_name=item.name)
        adjusted_hours = round(float(item.hours) * effort_multiplier, 2)
        total_hours += adjusted_hours
        role_hours[resolved_role] = role_hours.get(resolved_role, 0) + adjusted_hours

    role_hours = allocate_role_hours_from_phases(
        feature_items,
        rate_card,
        role_hours,
        total_hours,
        effort_multiplier,
    )

    total_days = total_hours / HOURS_PER_EFFORT_DAY

    phase_breakdown = enrich_phase_breakdown(
        [
            {
                "phase": phase.name,
                "hours": round(total_hours * phase.percentage, 2),
                "percentage": phase.percentage,
            }
            for phase in rate_card.phases
        ]
    )

    gantt: dict = {}
    estimated_duration_days = total_days
    if project_start_date is not None:
        gantt_items = gantt_feature_items or [
            GanttFeatureItemInput(
                name=item.name,
                hours=round(float(item.hours) * effort_multiplier, 2),
                phase=item.phase,
                role=item.role,
            )
            for item in feature_items
        ]
        gantt = build_gantt_timeline(
            [
                GanttFeatureItem(
                    id=item.id,
                    sort_order=item.sort_order,
                    name=item.name,
                    hours=float(item.hours),
                    phase=item.phase,
                    role=item.role,
                )
                for item in gantt_items
            ],
            [phase.name for phase in rate_card.phases],
            project_start_date,
        )
        if gantt["total_working_days"] > 0:
            estimated_duration_days = float(gantt["total_working_days"])

    role_breakdown = [
        {
            "role": role.name,
            "hours": role_hours.get(role.name, 0.0),
            "personnel_count": role_personnel_count(
                role_hours.get(role.name, 0.0),
                estimated_duration_days=estimated_duration_days,
                total_days=total_days,
            ),
            "rate_jpy": role_rates[role.name],
            "cost_jpy": int(role_hours.get(role.name, 0.0) * role_rates[role.name]),
        }
        for role in rate_card.roles
    ]

    labor_jpy = sum(entry["cost_jpy"] for entry in role_breakdown)
    contingency_jpy = int(labor_jpy * rate_card.contingency_rate)
    overhead_jpy = int(labor_jpy * rate_card.overhead_rate)
    setup_items = [serialize_jpy_line_item(item) for item in rate_card.setup_cost_items]
    setup_jpy = setup_items_total(rate_card.setup_cost_items)
    nrc_total = labor_jpy + setup_jpy + contingency_jpy + overhead_jpy

    support_role = maintenance.get("support_role", "developer")
    maintenance_jpy = int(maintenance.get("monthly_support_hours", 0) * role_rates.get(support_role, 0))
    monthly_rc_items = [serialize_jpy_line_item(item) for item in rate_card.monthly_rc_items]
    monthly_rc = sum(item.amount for item in rate_card.monthly_rc_items) + maintenance_jpy

    active_roles = len([row for row in role_breakdown if row["hours"] > 0])
    base_team_size = max(active_roles, 1)
    recommended_team_size = max(
        1,
        math.ceil(base_team_size * team_size_multiplier),
        sum(row["personnel_count"] for row in role_breakdown),
    )
    nrc_line_items = build_nrc_line_items(
        role_breakdown,
        rate_card.setup_cost_items,
        contingency_jpy,
        overhead_jpy,
    )
    rc_line_items = build_rc_line_items(monthly_rc_items, maintenance_jpy)

    result = CalculationResult(
        total_effort_hours=total_hours,
        total_effort_days=total_days,
        estimated_duration_days=estimated_duration_days,
        recommended_team_size=recommended_team_size,
        development_approach=approach.value,
        development_approach_effort_multiplier=effort_multiplier,
        phase_breakdown=phase_breakdown,
        role_breakdown=role_breakdown,
        nrc={
            "labor_jpy": labor_jpy,
            "setup_items": setup_items,
            "setup_jpy": setup_jpy,
            "contingency_jpy": contingency_jpy,
            "overhead_jpy": overhead_jpy,
            "total_jpy": nrc_total,
        },
        rc={
            "monthly_items": monthly_rc_items,
            "maintenance_jpy": maintenance_jpy,
            "monthly_total_jpy": monthly_rc,
            "annual_total_jpy": monthly_rc * 12,
        },
        nrc_line_items=nrc_line_items,
        rc_line_items=rc_line_items,
        cost_drivers=cost_drivers or [],
        first_year_total_jpy=nrc_total + monthly_rc * 12,
        rate_card_version_id=rate_card_version_id,
        gantt=gantt,
    )
    return apply_estimate_discount(result, rate_card, discount_rate)
