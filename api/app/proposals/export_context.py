"""Build stakeholder-facing export context for proposals."""

from __future__ import annotations

from typing import Any

from app.exports.gantt_svg import build_gantt_svg
from app.exports.theme import EXPORT_THEME
from app.models.proposal import Proposal


def _lexicon_labels(locale: str) -> dict[str, str]:
    if locale == "ja":
        return {
            "title": "プロジェクト提案書",
            "toc": "目次",
            "assessment": "プロジェクト評価",
            "proposal": "プロジェクト提案",
            "poc": "概念実証（Proof of Concept）",
            "one_time": "一次性のプロジェクト費用",
            "monthly": "月次の継続費用",
            "first_year": "初年度合計",
            "timeline": "プロジェクトタイムライン",
            "milestones": "マイルストーン",
            "official_poc_cost": "概念実証の公式費用（見積エンジン）",
            "suggested_window": "推奨する検証期間（目安）",
            "effort_hours": "想定工数（時間）",
            "effort_days": "想定工数（人日）",
            "working_days": "想定期間（稼働日）",
            "project_brief": "プロジェクト概要",
            "brief_project_name": "プロジェクト名",
            "brief_description": "プロジェクト説明",
            "brief_business_problem": "ビジネス課題",
            "brief_target_users": "想定利用者",
            "brief_technology_stack": "技術スタック",
            "brief_constraints": "制約条件",
            "poc_diagrams": "図",
            "poc_tables": "表",
            "poc_milestones": "概念実証マイルストーン",
        }
    return {
        "title": "Project Proposal Pack",
        "toc": "Table of Contents",
        "assessment": "Project Assessment",
        "proposal": "Project Proposal",
        "poc": "Proof of Concept",
        "one_time": "One-time project cost",
        "monthly": "Monthly recurring cost",
        "first_year": "First-year total",
        "timeline": "Project timeline",
        "milestones": "Milestones",
        "official_poc_cost": "Official Proof of Concept cost (from estimate engine)",
        "suggested_window": "Suggested validation window",
        "effort_hours": "Estimated effort (hours)",
        "effort_days": "Estimated effort (days)",
        "working_days": "Estimated timeline (working days)",
        "project_brief": "Project brief",
        "brief_project_name": "Project name",
        "brief_description": "Project description",
        "brief_business_problem": "Business problem",
        "brief_target_users": "Target users",
        "brief_technology_stack": "Technology stack",
        "brief_constraints": "Constraints",
        "poc_diagrams": "Illustrations",
        "poc_tables": "Tables",
        "poc_milestones": "Proof of Concept milestones",
    }


def _toc_entries(proposal: Proposal, locale: str, variant: str) -> list[dict[str, str]]:
    labels = _lexicon_labels(locale)
    entries: list[dict[str, str]] = []
    include_assessment = variant in {"full", "assessment"}
    include_proposal = variant in {"full", "proposal"}
    include_poc = variant in {"full", "poc"} and proposal.include_poc and proposal.poc

    def add_part(part_key: str, part_label: str, blob: dict[str, Any] | None) -> None:
        entries.append({"id": part_key, "title": part_label, "level": "1"})
        for section in (blob or {}).get("sections") or []:
            entries.append(
                {
                    "id": f"{part_key}-{section.get('id')}",
                    "title": str(section.get("title") or section.get("id")),
                    "level": "2",
                }
            )

    if include_assessment:
        add_part("assessment", labels["assessment"], proposal.assessment)
    if include_proposal:
        add_part("proposal", labels["proposal"], proposal.proposal_body)
    if include_poc:
        entries.append({"id": "poc", "title": labels["poc"], "level": "1"})
        if (proposal.poc or {}).get("project_brief"):
            entries.append(
                {
                    "id": "poc-project_brief",
                    "title": labels["project_brief"],
                    "level": "2",
                }
            )
        for section in (proposal.poc or {}).get("sections") or []:
            entries.append(
                {
                    "id": f"poc-{section.get('id')}",
                    "title": str(section.get("title") or section.get("id")),
                    "level": "2",
                }
            )
    return entries


def build_proposal_export_context(
    proposal: Proposal,
    *,
    locale: str | None = None,
    variant: str = "full",
    project_name: str | None = None,
) -> dict[str, Any]:
    loc = locale or proposal.locale
    labels = _lexicon_labels(loc)
    snapshot = proposal.source_snapshot or {}
    costs = snapshot.get("costs") or {}
    gantt = snapshot.get("gantt") or {}
    gantt_svg = ""
    try:
        gantt_svg = build_gantt_svg(gantt) if gantt else ""
    except Exception:
        gantt_svg = ""

    # Stakeholder cost block — never use NRC/RC abbreviations
    cost_summary = {
        "one_time_project_cost_jpy": costs.get("one_time_project_cost_jpy"),
        "monthly_recurring_cost_jpy": costs.get("monthly_recurring_cost_jpy"),
        "annual_recurring_cost_jpy": costs.get("annual_recurring_cost_jpy"),
        "first_year_total_jpy": costs.get("first_year_total_jpy"),
        "total_effort_hours": costs.get("total_effort_hours"),
        "total_effort_days": costs.get("total_effort_days"),
    }

    display_name = (project_name or "").strip() or (snapshot.get("project_name") or "")

    poc = proposal.poc if variant in {"full", "poc"} and proposal.include_poc else None
    if poc and display_name:
        poc = dict(poc)
        brief = dict(poc.get("project_brief") or {})
        if brief:
            brief["project_name"] = display_name
            poc["project_brief"] = brief

    return {
        "labels": labels,
        "locale": loc,
        "variant": variant,
        "project_name": display_name,
        "client_name": snapshot.get("client_name") or "",
        "toc": _toc_entries(proposal, loc, variant),
        "assessment": proposal.assessment if variant in {"full", "assessment"} else None,
        "proposal_body": proposal.proposal_body if variant in {"full", "proposal"} else None,
        "poc": poc,
        "diagrams": proposal.diagrams or [],
        "milestones": proposal.milestones or [],
        "cost_summary": cost_summary,
        "gantt": gantt,
        "gantt_svg": gantt_svg,
        "include_poc": proposal.include_poc,
        "theme": dict(EXPORT_THEME),
    }
