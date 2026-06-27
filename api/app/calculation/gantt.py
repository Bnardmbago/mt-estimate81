import heapq
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


def _normalize_role(name: str) -> str:
    return name.strip()


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


def _sum_role_hours(items: list[GanttFeatureItem]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for item in items:
        role = _normalize_role(item.role)
        totals[role] = totals.get(role, 0.0) + float(item.hours)
    return totals


def estimate_role_headcount(
    items: list[GanttFeatureItem],
    duration_days: float,
) -> dict[str, int]:
    totals = _sum_role_hours(items)
    hint = duration_days if duration_days > 0 else 1.0
    capacity = max(hint * HOURS_PER_EFFORT_DAY, HOURS_PER_EFFORT_DAY)
    headcount: dict[str, int] = {}
    for role, hours in totals.items():
        if hours <= 0:
            headcount[role] = 1
        else:
            headcount[role] = max(1, math.ceil(hours / capacity))
    return headcount


def _task_working_days(hours: float, personnel_count: int) -> int:
    if hours <= 0:
        return 0
    workers = max(1, personnel_count)
    return max(1, math.ceil(hours / (workers * HOURS_PER_EFFORT_DAY)))


def _resolve_role_headcount(role: str, role_headcount: dict[str, int]) -> int:
    key = _normalize_role(role)
    if key in role_headcount:
        return role_headcount[key]
    lowered = key.lower()
    for candidate, count in role_headcount.items():
        if candidate.lower() == lowered:
            return count
    return 1


def _build_phase_summary(
    phase_ranges: dict[str, dict[str, Any]],
    ordered_phases: list[str],
) -> list[dict[str, Any]]:
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

    return phases


def build_gantt_timeline(
    feature_items: list[GanttFeatureItem],
    phase_order: list[str] | None,
    start_date: date,
    *,
    role_headcount: dict[str, int] | None = None,
) -> dict[str, Any]:
    ordered_phases = _build_phase_order(phase_order)
    normalized_start = normalize_start_date(start_date)

    eligible = [
        item
        for item in feature_items
        if item.name.strip() and float(item.hours) > 0
    ]
    sorted_items = _sort_feature_items(eligible, ordered_phases)

    if not sorted_items:
        return {
            "project_start_date": normalized_start.isoformat(),
            "project_end_date": normalized_start.isoformat(),
            "total_working_days": 0,
            "phases": [],
            "tasks": [],
        }

    total_hours = sum(float(item.hours) for item in sorted_items)
    duration_hint = max(total_hours / HOURS_PER_EFFORT_DAY, 1.0)
    resolved_headcount = role_headcount or estimate_role_headcount(sorted_items, duration_hint)

    tasks: list[dict[str, Any]] = []
    phase_ranges: dict[str, dict[str, Any]] = {}
    role_heaps: dict[str, list[tuple[date, int]]] = {}

    for item in sorted_items:
        role_key = _normalize_role(item.role)
        personnel_count = _resolve_role_headcount(item.role, resolved_headcount)
        duration_days = _task_working_days(float(item.hours), personnel_count)

        if role_key not in role_heaps:
            initial_tracks = [normalized_start] * personnel_count
            role_heaps[role_key] = [
                (track_date, index) for index, track_date in enumerate(initial_tracks)
            ]
            heapq.heapify(role_heaps[role_key])

        available_date, track_index = heapq.heappop(role_heaps[role_key])
        task_start = max(available_date, normalized_start)
        end_date = add_working_days(task_start, duration_days)
        heapq.heappush(role_heaps[role_key], (next_working_day(end_date), track_index))

        phase_key = _normalize_phase(item.phase)
        task = {
            "feature_item_id": item.id,
            "name": item.name,
            "phase": item.phase,
            "role": item.role,
            "hours": float(item.hours),
            "effort_days": round(float(item.hours) / HOURS_PER_EFFORT_DAY, 2),
            "personnel_count": personnel_count,
            "start_date": task_start.isoformat(),
            "end_date": end_date.isoformat(),
            "duration_working_days": duration_days,
            "depends_on": None,
            "parallel_track": track_index,
        }
        tasks.append(task)

        if phase_key not in phase_ranges:
            phase_ranges[phase_key] = {
                "phase": item.phase,
                "start_date": task_start.isoformat(),
                "end_date": end_date.isoformat(),
            }
        else:
            existing_start = date.fromisoformat(phase_ranges[phase_key]["start_date"])
            existing_end = date.fromisoformat(phase_ranges[phase_key]["end_date"])
            phase_ranges[phase_key]["start_date"] = min(existing_start, task_start).isoformat()
            phase_ranges[phase_key]["end_date"] = max(existing_end, end_date).isoformat()

    project_end = max(date.fromisoformat(task["end_date"]) for task in tasks)
    total_working_days = count_working_days(normalized_start, project_end)

    return {
        "project_start_date": normalized_start.isoformat(),
        "project_end_date": project_end.isoformat(),
        "total_working_days": total_working_days,
        "phases": _build_phase_summary(phase_ranges, ordered_phases),
        "tasks": tasks,
    }


def build_gantt_timeline_two_pass(
    feature_items: list[GanttFeatureItem],
    phase_order: list[str] | None,
    start_date: date,
) -> dict[str, Any]:
    eligible = [
        item
        for item in feature_items
        if item.name.strip() and float(item.hours) > 0
    ]
    if not eligible:
        return build_gantt_timeline(feature_items, phase_order, start_date)

    total_hours = sum(float(item.hours) for item in eligible)
    duration_hint = max(total_hours / HOURS_PER_EFFORT_DAY, 1.0)
    headcount_pass1 = estimate_role_headcount(eligible, duration_hint)
    gantt_pass1 = build_gantt_timeline(
        feature_items,
        phase_order,
        start_date,
        role_headcount=headcount_pass1,
    )
    span = float(gantt_pass1["total_working_days"]) or duration_hint
    headcount_pass2 = estimate_role_headcount(eligible, span)
    return build_gantt_timeline(
        feature_items,
        phase_order,
        start_date,
        role_headcount=headcount_pass2,
    )
