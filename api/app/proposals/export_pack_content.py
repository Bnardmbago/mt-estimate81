"""Shared proposal-pack content walkers for MD/DOCX/XLSX emitters."""

from __future__ import annotations

from typing import Any, Iterator


BRIEF_FIELD_KEYS = (
    ("project_name", "brief_project_name"),
    ("project_description", "brief_description"),
    ("business_problem", "brief_business_problem"),
    ("target_users", "brief_target_users"),
    ("technology_stack", "brief_technology_stack"),
    ("constraints", "brief_constraints"),
)


def iter_pack_parts(ctx: dict[str, Any]) -> Iterator[tuple[str, str, dict[str, Any]]]:
    """Yield (part_key, localized_title, blob) for non-empty parts."""
    labels = ctx.get("labels") or {}
    for key, label_key, default in (
        ("assessment", "assessment", "Assessment"),
        ("proposal_body", "proposal", "Proposal"),
        ("poc", "poc", "Proof of Concept"),
    ):
        blob = ctx.get(key)
        if not blob:
            continue
        if key == "poc" and not ctx.get("include_poc", True):
            continue
        yield key, str(labels.get(label_key) or default), blob


def brief_field_rows(
    brief: dict[str, Any] | None,
    labels: dict[str, Any],
) -> list[tuple[str, str]]:
    if not brief:
        return []
    rows: list[tuple[str, str]] = []
    for field_key, label_key in BRIEF_FIELD_KEYS:
        value = brief.get(field_key)
        if value is None or value == "":
            continue
        rows.append((str(labels.get(label_key) or field_key), str(value)))
    return rows


def section_rows(blob: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten sections to rows with title, body, and optional bullets list."""
    rows: list[dict[str, Any]] = []
    for section in blob.get("sections") or []:
        rows.append(
            {
                "title": section.get("title") or "",
                "body": section.get("body") or "",
                "bullets": list(section.get("bullets") or []),
                "rating": section.get("rating") or "",
            }
        )
    return rows


def collect_diagrams(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    """Proposal-level diagrams plus PoC diagrams."""
    diagrams: list[dict[str, Any]] = []
    for d in ctx.get("diagrams") or []:
        diagrams.append(d)
    poc = ctx.get("poc") or {}
    for d in poc.get("diagrams") or []:
        diagrams.append(d)
    return diagrams


def gantt_timeline_rows(gantt: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Task/phase rows for Excel Timeline sheet."""
    if not gantt:
        return []
    rows: list[dict[str, Any]] = []
    tasks = gantt.get("tasks") or []
    if tasks:
        for task in tasks:
            rows.append(
                {
                    "name": task.get("name") or "",
                    "phase": task.get("phase") or "",
                    "start_date": task.get("start_date") or "",
                    "end_date": task.get("end_date") or "",
                    "duration_working_days": task.get("duration_working_days"),
                    "hours": task.get("hours"),
                }
            )
        return rows
    for phase in gantt.get("phases") or []:
        rows.append(
            {
                "name": phase.get("phase") or "",
                "phase": phase.get("phase") or "",
                "start_date": phase.get("start_date") or "",
                "end_date": phase.get("end_date") or "",
                "duration_working_days": phase.get("duration_working_days"),
                "hours": None,
            }
        )
    return rows
