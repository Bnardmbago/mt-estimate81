from __future__ import annotations

from datetime import date, datetime
from html import escape
from typing import Any

from app.exports.theme import ACCENT, BORDER, PRIMARY, PRIMARY_LIGHT, SURFACE

PHASE_COLORS: dict[str, str] = {
    "requirement": f"#{PRIMARY}",
    "design": f"#{ACCENT}",
    "development": "#475569",
    "testing": "#D97706",
    "deployment": "#64748B",
    "management": "#0EA5E9",
}

DEFAULT_BAR_COLOR = f"#{PRIMARY}"
BORDER_STROKE = f"#{BORDER}"


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _phase_color(phase: str, accent_color: str) -> str:
    normalized_phase = phase.strip().lower()
    if normalized_phase == "design":
        return accent_color
    return PHASE_COLORS.get(normalized_phase, DEFAULT_BAR_COLOR)


def _truncate(text: str, max_len: int = 32) -> str:
    cleaned = text.strip()
    if len(cleaned) <= max_len:
        return cleaned
    return f"{cleaned[: max_len - 1]}…"


def build_gantt_svg(
    gantt: dict[str, Any],
    accent_color: str = f"#{ACCENT}",
) -> str:
    tasks = gantt.get("tasks") or []
    if not tasks:
        return ""

    project_start = _parse_date(str(gantt["project_start_date"]))
    project_end = _parse_date(str(gantt["project_end_date"]))
    total_days = max((project_end - project_start).days, 1)

    label_width = 180
    chart_width = 500
    row_height = 24
    header_height = 22
    legend_height = 22
    padding = 8
    width = padding * 2 + label_width + chart_width
    chart_rows_height = len(tasks) * row_height
    height = padding * 2 + header_height + chart_rows_height + legend_height + 6

    ticks: list[str] = []
    tick_count = min(6, total_days + 1)
    for index in range(tick_count):
        offset = round(total_days * index / max(tick_count - 1, 1))
        tick_date = project_start.toordinal() + offset
        ticks.append(date.fromordinal(tick_date).isoformat())

    chart_left = padding + label_width
    chart_top = padding + header_height

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">',
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" '
        f'fill="#ffffff" stroke="{BORDER_STROKE}" stroke-width="1" rx="4"/>',
    ]

    for index, tick in enumerate(ticks):
        x = chart_left + (chart_width * index / max(len(ticks) - 1, 1))
        parts.append(
            f'<line x1="{x:.1f}" y1="{chart_top}" x2="{x:.1f}" y2="{chart_top + chart_rows_height}" '
            f'stroke="{BORDER_STROKE}" stroke-width="0.5"/>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{padding + 14}" font-size="8" fill="#64748B" '
            f'text-anchor="middle">{escape(tick[5:])}</text>'
        )

    parts.append(
        f'<rect x="{chart_left}" y="{chart_top}" width="{chart_width}" height="{chart_rows_height}" '
        f'fill="#{SURFACE}" rx="3"/>'
    )

    phases_seen: dict[str, str] = {}
    for row_index, task in enumerate(tasks):
        y = chart_top + row_index * row_height
        if row_index % 2 == 0:
            parts.append(
                f'<rect x="{padding}" y="{y}" width="{label_width + chart_width}" '
                f'height="{row_height}" fill="#ffffff"/>'
            )

        name = _truncate(str(task.get("name") or ""))
        parts.append(
            f'<text x="{padding + 4}" y="{y + 15}" font-size="8" fill="#{PRIMARY}">'
            f"{escape(name)}</text>"
        )

        task_start = _parse_date(str(task["start_date"]))
        task_end = _parse_date(str(task["end_date"]))
        start_offset = max((task_start - project_start).days, 0)
        end_offset = max((task_end - project_start).days, start_offset)
        bar_left = chart_left + (start_offset / total_days) * chart_width
        bar_width = max(((end_offset - start_offset + 1) / (total_days + 1)) * chart_width, 6)
        phase = str(task.get("phase_key") or task.get("phase") or "")
        color = _phase_color(phase, accent_color)
        display_phase = str(task.get("phase") or phase)
        phases_seen.setdefault(display_phase, color)
        parts.append(
            f'<rect x="{bar_left:.1f}" y="{y + 5}" width="{bar_width:.1f}" height="{row_height - 10}" '
            f'rx="4" fill="{color}"/>'
        )

    legend_y = chart_top + chart_rows_height + 8
    legend_x = padding
    for phase_label, color in sorted(phases_seen.items()):
        if not phase_label:
            continue
        parts.append(
            f'<rect x="{legend_x}" y="{legend_y}" width="10" height="10" fill="{color}" rx="2"/>'
        )
        parts.append(
            f'<text x="{legend_x + 14}" y="{legend_y + 9}" font-size="7.5" fill="#64748B">'
            f"{escape(phase_label)}</text>"
        )
        legend_x += 80

    parts.append("</svg>")
    return "".join(parts)
