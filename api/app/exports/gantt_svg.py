from __future__ import annotations

from datetime import date, datetime
from html import escape
from typing import Any

from app.exports.theme import BLUE_LIGHT, BLUE_PRIMARY

PHASE_COLORS: dict[str, str] = {
    "requirement": f"#{BLUE_PRIMARY}",
    "design": "#6B9BC3",
    "development": f"#{BLUE_PRIMARY}",
    "testing": "#F5C842",
    "deployment": "#7BA3C9",
}

DEFAULT_BAR_COLOR = f"#{BLUE_PRIMARY}"


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _phase_color(phase: str) -> str:
    return PHASE_COLORS.get(phase.strip().lower(), DEFAULT_BAR_COLOR)


def _truncate(text: str, max_len: int = 28) -> str:
    cleaned = text.strip()
    if len(cleaned) <= max_len:
        return cleaned
    return f"{cleaned[: max_len - 1]}…"


def build_gantt_svg(gantt: dict[str, Any]) -> str:
    tasks = gantt.get("tasks") or []
    if not tasks:
        return ""

    project_start = _parse_date(str(gantt["project_start_date"]))
    project_end = _parse_date(str(gantt["project_end_date"]))
    total_days = max((project_end - project_start).days, 1)

    label_width = 160
    chart_width = 480
    row_height = 18
    header_height = 16
    padding_top = 4
    width = label_width + chart_width + 8
    height = padding_top + header_height + len(tasks) * row_height + 8

    ticks: list[str] = []
    tick_count = min(5, total_days + 1)
    for index in range(tick_count):
        offset = round(total_days * index / max(tick_count - 1, 1))
        tick_date = project_start.toordinal() + offset
        ticks.append(date.fromordinal(tick_date).isoformat())

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
    ]

    for index, tick in enumerate(ticks):
        x = label_width + (chart_width * index / max(len(ticks) - 1, 1))
        parts.append(
            f'<text x="{x:.1f}" y="{padding_top + 10}" font-size="7" fill="#9ca3af" '
            f'text-anchor="middle">{escape(tick)}</text>'
        )

    chart_top = padding_top + header_height
    parts.append(
        f'<rect x="{label_width}" y="{chart_top}" width="{chart_width}" height="{len(tasks) * row_height}" '
        f'fill="#{BLUE_LIGHT}" stroke="#{BLUE_PRIMARY}" stroke-width="0.5"/>'
    )

    for row_index, task in enumerate(tasks):
        y = chart_top + row_index * row_height
        name = _truncate(str(task.get("name") or ""))
        parts.append(
            f'<text x="4" y="{y + 12}" font-size="7" fill="#374151">{escape(name)}</text>'
        )

        task_start = _parse_date(str(task["start_date"]))
        task_end = _parse_date(str(task["end_date"]))
        start_offset = max((task_start - project_start).days, 0)
        end_offset = max((task_end - project_start).days, start_offset)
        bar_left = label_width + (start_offset / total_days) * chart_width
        bar_width = max(((end_offset - start_offset + 1) / (total_days + 1)) * chart_width, 4)
        color = _phase_color(str(task.get("phase") or ""))
        parts.append(
            f'<rect x="{bar_left:.1f}" y="{y + 3}" width="{bar_width:.1f}" height="{row_height - 6}" '
            f'rx="2" fill="{color}"/>'
        )

    parts.append("</svg>")
    return "".join(parts)
