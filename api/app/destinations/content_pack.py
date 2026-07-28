"""Build a Canva autofill content pack from proposal export context."""

from __future__ import annotations

from typing import Any


def build_canva_content_pack(
    ctx: dict[str, Any],
    *,
    variant: str,
) -> dict[str, Any]:
    """Shape fields + image placeholders for Canva Brand template autofill.

    Official cost summary is included as locked read-only text — not editable fee fields.
    """
    project_name = (
        ctx.get("project_name")
        or (ctx.get("source_snapshot") or {}).get("project_name")
        or "Proposal"
    )
    locale = ctx.get("locale") or "en"
    costs = ctx.get("cost_summary") or (ctx.get("source_snapshot") or {}).get("costs") or {}

    official_cost_lines: list[str] = []
    for key, label in (
        ("one_time_project_cost_jpy", "One-time project cost"),
        ("monthly_recurring_cost_jpy", "Monthly recurring cost"),
        ("first_year_total_jpy", "First-year total"),
        ("nrc_jpy", "NRC"),
        ("rc_monthly_jpy", "Monthly RC"),
        ("poc_nrc_jpy", "Official POC cost"),
    ):
        value = costs.get(key)
        if value is not None:
            official_cost_lines.append(f"{label}: {value}")

    poc = ctx.get("poc") or {}
    if poc.get("official_cost") is not None:
        official_cost_lines.append(f"Official POC cost: {poc['official_cost']}")
    elif ctx.get("official_poc_cost") is not None:
        official_cost_lines.append(f"Official POC cost: {ctx['official_poc_cost']}")

    locked_cost_summary = (
        "\n".join(official_cost_lines)
        if official_cost_lines
        else "Official costs are owned by mt-estimate81 — regenerate in-app to update."
    )

    proposal_body = ctx.get("proposal_body") or {}
    assessment = ctx.get("assessment") or {}

    fields: dict[str, str] = {
        "project_name": str(project_name),
        "locale": str(locale),
        "variant": variant,
        "locked_official_cost_summary": locked_cost_summary,
        "executive_summary": _text(
            proposal_body.get("executive_summary")
            or assessment.get("summary")
            or poc.get("summary")
            or ""
        ),
        "title": _text(
            proposal_body.get("title")
            or assessment.get("title")
            or poc.get("title")
            or project_name
        ),
    }

    milestones = ctx.get("milestones") or proposal_body.get("milestones") or poc.get("milestones") or []
    if isinstance(milestones, list):
        fields["milestones"] = "\n".join(
            _text(m.get("name") if isinstance(m, dict) else m) for m in milestones[:12]
        )

    diagram_images: list[dict[str, Any]] = []
    gantt_svg = ctx.get("gantt_svg")
    if isinstance(gantt_svg, str) and gantt_svg.strip():
        diagram_images.append(
            {"name": "gantt_svg", "content_type": "image/svg+xml", "text": gantt_svg}
        )

    for diag in ctx.get("diagrams") or []:
        if not isinstance(diag, dict):
            continue
        svg = diag.get("svg") or diag.get("rendered_svg")
        if isinstance(svg, str) and svg.strip():
            diagram_images.append(
                {
                    "name": str(diag.get("id") or diag.get("title") or "diagram"),
                    "content_type": "image/svg+xml",
                    "text": svg,
                }
            )

    return {
        "variant": variant,
        "fields": fields,
        "diagram_images": [
            {k: v for k, v in img.items() if k != "bytes"}
            | ({"byte_length": len(img["bytes"])} if "bytes" in img else {})
            for img in diagram_images
        ],
        "_diagram_blobs": diagram_images,
        "locked_official_cost_summary": locked_cost_summary,
    }


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()
