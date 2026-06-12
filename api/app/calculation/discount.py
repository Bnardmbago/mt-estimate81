from copy import deepcopy

from app.calculation.line_items import build_nrc_line_items
from app.calculation.schemas import CalculationResult, RateCardSettings, SetupCostItem


def _scale_jpy(value: int | float, multiplier: float) -> int:
    return int(round(float(value) * multiplier))


def apply_estimate_discount(
    result: CalculationResult,
    rate_card: RateCardSettings,
    discount_rate: float,
) -> CalculationResult:
    if discount_rate <= 0:
        return result

    multiplier = 1.0 - discount_rate
    data = result.model_dump()

    role_breakdown = deepcopy(data["role_breakdown"])
    for row in role_breakdown:
        hours = float(row["hours"])
        discounted_cost = _scale_jpy(row["cost_jpy"], multiplier)
        row["cost_jpy"] = discounted_cost
        if hours > 0:
            row["rate_jpy"] = int(round(discounted_cost / hours))
        else:
            row["rate_jpy"] = _scale_jpy(row["rate_jpy"], multiplier)

    setup_items = deepcopy(data["nrc"]["setup_items"])
    for item in setup_items:
        item["amount_jpy"] = _scale_jpy(item["amount_jpy"], multiplier)

    contingency_jpy = _scale_jpy(data["nrc"]["contingency_jpy"], multiplier)
    overhead_jpy = _scale_jpy(data["nrc"]["overhead_jpy"], multiplier)

    labor_jpy = sum(int(row["cost_jpy"]) for row in role_breakdown)
    setup_jpy = sum(int(item["amount_jpy"]) for item in setup_items)
    nrc_total = labor_jpy + setup_jpy + contingency_jpy + overhead_jpy

    setup_cost_items = [
        SetupCostItem(name=item["name"], amount_jpy=int(item["amount_jpy"]))
        for item in setup_items
    ]
    nrc_line_items = build_nrc_line_items(
        role_breakdown,
        setup_cost_items,
        contingency_jpy,
        overhead_jpy,
    )

    rc = data["rc"]
    annual_rc = int(rc["annual_total_jpy"])

    data["role_breakdown"] = role_breakdown
    data["nrc"] = {
        **data["nrc"],
        "labor_jpy": labor_jpy,
        "setup_items": setup_items,
        "setup_jpy": setup_jpy,
        "contingency_jpy": contingency_jpy,
        "overhead_jpy": overhead_jpy,
        "total_jpy": nrc_total,
    }
    data["nrc_line_items"] = nrc_line_items
    data["first_year_total_jpy"] = nrc_total + annual_rc

    return CalculationResult(**data)
