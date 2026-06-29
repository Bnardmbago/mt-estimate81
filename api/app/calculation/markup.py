from typing import Any

from app.calculation.schemas import CalculationResult


def _scale_jpy(value: int | float, multiplier: float) -> int:
    return int(round(float(value) * multiplier))


def compute_internal_pricing(
    result: CalculationResult,
    markup_rate: float,
) -> dict[str, Any] | None:
    if markup_rate <= 0:
        return None

    multiplier = 1.0 + markup_rate
    data = result.model_dump()

    nrc_line_items: list[dict[str, Any]] = []
    for row in data.get("nrc_line_items") or []:
        cost_jpy = _scale_jpy(row.get("cost_jpy") or 0, multiplier)
        if cost_jpy <= 0:
            continue
        nrc_line_items.append({**row, "cost_jpy": cost_jpy})

    rc_line_items: list[dict[str, Any]] = []
    for row in data.get("rc_line_items") or []:
        monthly_jpy = _scale_jpy(row.get("monthly_jpy") or 0, multiplier)
        if monthly_jpy <= 0:
            continue
        rc_line_items.append(
            {
                **row,
                "monthly_jpy": monthly_jpy,
                "annual_jpy": monthly_jpy * 12,
            }
        )

    nrc_total_jpy = sum(int(item["cost_jpy"]) for item in nrc_line_items)
    rc_monthly_total_jpy = sum(int(item["monthly_jpy"]) for item in rc_line_items)
    rc_annual_total_jpy = rc_monthly_total_jpy * 12

    return {
        "markup_rate_applied": markup_rate,
        "nrc_line_items": nrc_line_items,
        "rc_line_items": rc_line_items,
        "nrc_total_jpy": nrc_total_jpy,
        "rc_monthly_total_jpy": rc_monthly_total_jpy,
        "rc_annual_total_jpy": rc_annual_total_jpy,
        "first_year_total_jpy": nrc_total_jpy + rc_annual_total_jpy,
    }
