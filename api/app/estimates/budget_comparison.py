from __future__ import annotations

from typing import Any, Literal

BudgetComparisonStatus = Literal["under", "over", "aligned"]


def _parse_client_budget_jpy(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    digits = "".join(char for char in text if char.isdigit())
    if not digits:
        return None
    amount = int(digits)
    return amount if amount > 0 else None


def build_budget_comparison(
    client_budget_raw: Any,
    calculated_nrc_jpy: int,
    *,
    alignment_tolerance: float = 0.10,
) -> dict[str, Any] | None:
    client_budget_jpy = _parse_client_budget_jpy(client_budget_raw)
    if client_budget_jpy is None:
        return None

    delta_jpy = calculated_nrc_jpy - client_budget_jpy
    if client_budget_jpy <= 0:
        status: BudgetComparisonStatus = "aligned"
    elif abs(delta_jpy) <= int(client_budget_jpy * alignment_tolerance):
        status = "aligned"
    elif delta_jpy > 0:
        status = "over"
    else:
        status = "under"

    return {
        "client_budget_jpy": client_budget_jpy,
        "calculated_nrc_jpy": calculated_nrc_jpy,
        "delta_jpy": delta_jpy,
        "status": status,
    }
