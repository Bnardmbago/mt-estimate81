from app.calculation.schemas import CalculationResult, FeatureItemInput, RateCardSettings

HOURS_PER_EFFORT_DAY = 8


class CalculationError(Exception):
    def __init__(self, message: str, feature_item_name: str | None = None):
        self.feature_item_name = feature_item_name
        super().__init__(message)


def calculate_estimate(
    feature_items: list[FeatureItemInput],
    rate_card: RateCardSettings,
    maintenance: dict,
    rate_card_version_id: str,
) -> CalculationResult:
    role_rates = {role.name: role.hourly_rate_jpy for role in rate_card.roles}
    role_hours: dict[str, float] = {}
    total_hours = 0.0

    for item in feature_items:
        if item.role not in role_rates:
            raise CalculationError(f"Unknown role '{item.role}'", feature_item_name=item.name)
        total_hours += float(item.hours)
        role_hours[item.role] = role_hours.get(item.role, 0) + float(item.hours)

    total_days = total_hours / HOURS_PER_EFFORT_DAY

    phase_breakdown = [
        {
            "phase": phase.name,
            "hours": round(total_hours * phase.percentage, 2),
            "percentage": phase.percentage,
        }
        for phase in rate_card.phases
    ]

    role_breakdown = [
        {
            "role": role,
            "hours": hours,
            "rate_jpy": role_rates[role],
            "cost_jpy": int(hours * role_rates[role]),
        }
        for role, hours in role_hours.items()
    ]

    labor_jpy = sum(entry["cost_jpy"] for entry in role_breakdown)
    contingency_jpy = int(labor_jpy * rate_card.contingency_rate)
    overhead_jpy = int(labor_jpy * rate_card.overhead_rate)
    setup_jpy = sum(rate_card.setup_costs.model_dump().values())
    nrc_total = labor_jpy + setup_jpy + contingency_jpy + overhead_jpy

    support_role = maintenance.get("support_role", "developer")
    maintenance_jpy = int(maintenance.get("monthly_support_hours", 0) * role_rates.get(support_role, 0))
    monthly_rc_items = [item.model_dump() for item in rate_card.monthly_rc_items]
    monthly_rc = sum(item.amount_jpy for item in rate_card.monthly_rc_items) + maintenance_jpy

    return CalculationResult(
        total_effort_hours=total_hours,
        total_effort_days=total_days,
        phase_breakdown=phase_breakdown,
        role_breakdown=role_breakdown,
        nrc={
            "labor_jpy": labor_jpy,
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
        first_year_total_jpy=nrc_total + monthly_rc * 12,
        rate_card_version_id=rate_card_version_id,
    )
