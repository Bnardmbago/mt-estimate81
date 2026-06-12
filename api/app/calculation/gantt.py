import math
from dataclasses import dataclass
from datetime import date
from typing import Any

from app.calculation.calendar import (
    add_working_days,
    count_working_days,
    next_working_day,
    normalize_start_date,
)

HOURS_PER_EFFORT_DAY = 8

DEFAULT_PHASE_ORDER = [
    "requirement",
    "design",
    "development",
    "testing",
    "deployment",
]


@dataclass
class GanttFeatureItem:
    id: str | None
    sort_order: int
    name: str
    hours: float
    phase: str
    role: str


def _normalize_phase(name: str) -> str:
    return name.strip().lower()


def _phase_sort_key(phase: str, phase_order: list[str]) -> tuple[int, str]:
    normalized = _normalize_phase(phase)
    order_map = {_normalize_phase(p): index for index, p in enumerate(phase_order)}
    if normalized in order_map:
        return (order_map[normalized], normalized)
    return (len(phase_order), normalized)


def _build_phase_order(rate_card_phases: list[str] | None) -> list[str]:
    if rate_card_phases:
        return [_normalize_phase(phase) for phase in rate_card_phases]
    return list(DEFAULT_PHASE_ORDER)


def _sort_feature_items(items: list[GanttFeatureItem], phase_order: list[str]) -> list[GanttFeatureItem]:
    return sorted(
        items,
        key=lambda item: (
            _phase_sort_key(item.phase, phase_order)[0],
            _phase_sort_key(item.phase, phase_order)[1],
            item.sort_order,
            item.name.lower(),
        ),
    )


def _effort_working_days(hours: float) -> int:
    if hours <= 0:
        return 0
    return max(1, math.ceil(hours / HOURS_PER_EFFORT_DAY))


def build_gantt_timeline(
    feature_items: list[GanttFeatureItem],
    phase_order: list[str] | None,
    start_date: date,
) -> dict[str, Any]:
    ordered_phases = _build_phase_order(phase_order)
    normalized_start = normalize_start_date(start_date)

    eligible = [
        item
        for item in feature_items
        if item.name.strip() and float(item.hours) > 0
    ]
    sorted_items = _sort_feature_items(eligible, ordered_phases)

    tasks: list[dict[str, Any]] = []
    phase_ranges: dict[str, dict[str, Any]] = {}

    if not sorted_items:
        return {
            "project_start_date": normalized_start.isoformat(),
            "project_end_date": normalized_start.isoformat(),
            "total_working_days": 0,
            "phases": [],
            "tasks": [],
        }

    current_start = normalized_start

    for item in sorted_items:
        duration_days = _effort_working_days(float(item.hours))
        end_date = add_working_days(current_start, duration_days)
        phase_key = _normalize_phase(item.phase)

        task = {
            "feature_item_id": item.id,
            "name": item.name,
            "phase": item.phase,
            "role": item.role,
            "hours": float(item.hours),
            "effort_days": round(float(item.hours) / HOURS_PER_EFFORT_DAY, 2),
            "start_date": current_start.isoformat(),
            "end_date": end_date.isoformat(),
            "duration_working_days": duration_days,
        }
        tasks.append(task)

        if phase_key not in phase_ranges:
            phase_ranges[phase_key] = {
                "phase": item.phase,
                "start_date": current_start.isoformat(),
                "end_date": end_date.isoformat(),
            }
        else:
            phase_ranges[phase_key]["end_date"] = end_date.isoformat()

        current_start = next_working_day(end_date)

    phases: list[dict[str, Any]] = []
    seen_phases: set[str] = set()
    for phase_name in ordered_phases:
        if phase_name in phase_ranges and phase_name not in seen_phases:
            seen_phases.add(phase_name)
            row = phase_ranges[phase_name]
            start = date.fromisoformat(row["start_date"])
            end = date.fromisoformat(row["end_date"])
            phases.append(
                {
                    "phase": row["phase"],
                    "start_date": row["start_date"],
                    "end_date": row["end_date"],
                    "duration_working_days": count_working_days(start, end),
                }
            )

    for phase_key, row in phase_ranges.items():
        if phase_key in seen_phases:
            continue
        start = date.fromisoformat(row["start_date"])
        end = date.fromisoformat(row["end_date"])
        phases.append(
            {
                "phase": row["phase"],
                "start_date": row["start_date"],
                "end_date": row["end_date"],
                "duration_working_days": count_working_days(start, end),
            }
        )

    project_end = date.fromisoformat(tasks[-1]["end_date"])
    total_working_days = count_working_days(normalized_start, project_end)

    return {
        "project_start_date": normalized_start.isoformat(),
        "project_end_date": project_end.isoformat(),
        "total_working_days": total_working_days,
        "phases": phases,
        "tasks": tasks,
    }
