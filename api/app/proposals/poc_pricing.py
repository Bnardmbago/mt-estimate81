"""Engine-backed Proof of Concept pricing from selected feature items."""

from __future__ import annotations

from typing import Any


HOURS_PER_DAY = 8.0


def price_poc_selection(
    *,
    selected_feature_ids: list[str],
    features: list[dict[str, Any]],
    role_breakdown: list[dict[str, Any]] | None = None,
    gantt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Price POC from feature hours using average role rates from the estimate snapshot."""
    selected = {str(fid) for fid in selected_feature_ids}
    chosen = [f for f in features if str(f.get("id")) in selected]
    if not chosen and selected_feature_ids:
        # Fall back to name match is not used; empty official figures with warning.
        return {
            "selected_feature_ids": selected_feature_ids,
            "selected_features": [],
            "total_effort_hours": 0.0,
            "total_effort_days": 0.0,
            "estimated_one_time_cost_jpy": 0,
            "estimated_timeline_working_days": 0,
            "warning": "Selected work items were not found in the estimate snapshot.",
        }

    total_hours = sum(float(f.get("hours") or 0) for f in chosen)

    rate_by_role: dict[str, float] = {}
    for row in role_breakdown or []:
        role = str(row.get("role") or "")
        rate = row.get("rate_jpy")
        if role and rate is not None:
            rate_by_role[role] = float(rate)

    avg_rate = 0.0
    if rate_by_role:
        avg_rate = sum(rate_by_role.values()) / len(rate_by_role)

    labor_cost = 0
    for feature in chosen:
        role = str(feature.get("role") or "")
        hours = float(feature.get("hours") or 0)
        rate = rate_by_role.get(role, avg_rate)
        labor_cost += int(round(hours * rate))

    working_days = int(round(total_hours / HOURS_PER_DAY)) if total_hours else 0

    # Prefer proportional slice of project gantt span when available.
    gantt = gantt or {}
    project_days = gantt.get("total_working_days")
    if project_days and features:
        all_hours = sum(float(f.get("hours") or 0) for f in features) or 1.0
        working_days = max(1, int(round(float(project_days) * (total_hours / all_hours)))) if total_hours else 0

    return {
        "selected_feature_ids": [str(f["id"]) for f in chosen],
        "selected_features": [
            {
                "id": str(f["id"]),
                "name": f.get("name"),
                "hours": float(f.get("hours") or 0),
                "phase": f.get("phase"),
                "role": f.get("role"),
            }
            for f in chosen
        ],
        "total_effort_hours": round(total_hours, 2),
        "total_effort_days": round(total_hours / HOURS_PER_DAY, 2) if total_hours else 0.0,
        "estimated_one_time_cost_jpy": labor_cost,
        "estimated_timeline_working_days": working_days,
        "project_start_date": gantt.get("project_start_date"),
        "project_end_date": gantt.get("project_end_date"),
    }
