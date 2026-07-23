"""Locale-aware prompts for detailed stakeholder proposal generation."""

from __future__ import annotations

import json
from typing import Any, Literal

Locale = Literal["ja", "en"]


def _language(locale: Locale) -> str:
    return "Japanese" if locale == "ja" else "English"


def _snapshot_facts(snapshot: dict[str, Any], locale: Locale = "en") -> str:
    costs = snapshot.get("costs") or {}
    gantt = snapshot.get("gantt") or {}
    features = snapshot.get("features") or []
    feature_lines = []
    for f in features[:80]:
        feature_lines.append(
            {
                "id": f.get("id"),
                "name": (
                    f.get("name_ja") or f.get("name")
                    if locale == "ja"
                    else f.get("name_en") or f.get("name")
                ),
                "name_en": f.get("name_en") or f.get("name"),
                "name_ja": f.get("name_ja") or f.get("name"),
                "hours": f.get("hours"),
                "phase": f.get("phase"),
            }
        )
    facts = {
        "project_name": snapshot.get("project_name"),
        "client_name": snapshot.get("client_name"),
        "modules": snapshot.get("modules") or [],
        "risks": snapshot.get("risks") or [],
        "gaps": snapshot.get("gaps") or [],
        "assumptions": snapshot.get("assumptions") or [],
        "functional_requirements": (snapshot.get("functional_requirements") or [])[:20],
        "non_functional_requirements": (snapshot.get("non_functional_requirements") or [])[:15],
        "user_roles": snapshot.get("user_roles") or [],
        "costs": {
            "one_time_project_cost_jpy": costs.get("one_time_project_cost_jpy"),
            "monthly_recurring_cost_jpy": costs.get("monthly_recurring_cost_jpy"),
            "first_year_total_jpy": costs.get("first_year_total_jpy"),
            "total_effort_hours": costs.get("total_effort_hours"),
            "total_effort_days": costs.get("total_effort_days"),
        },
        "timeline": {
            "project_start_date": gantt.get("project_start_date"),
            "project_end_date": gantt.get("project_end_date"),
            "total_working_days": gantt.get("total_working_days"),
            "phases": gantt.get("phases") or [],
        },
        "features": feature_lines,
    }
    return json.dumps(facts, ensure_ascii=False, indent=2)


def build_assessment_system_prompt(locale: Locale) -> str:
    language = _language(locale)
    return (
        "You are a senior consulting partner writing a project feasibility assessment "
        "for business stakeholders (not developers).\n"
        f"Write all section titles and prose in {language}.\n"
        "Produce detailed, persuasive, clear analysis — several sentences per section, not one-liners.\n"
        "Never invent costs, hours, or dates; only use figures provided in the facts.\n"
        "Use full phrases: 'one-time project cost', 'monthly recurring cost', 'Proof of Concept'. "
        "Do not use abbreviations like NRC, RC, or POC alone.\n"
        "Return JSON matching the required schema exactly."
    )


def build_assessment_user_prompt(snapshot: dict[str, Any], locale: Locale) -> str:
    required_ids = [
        "feasibility",
        "readiness",
        "complexity",
        "risks",
        "recommendation",
        "poc_recommendation",
    ]
    return (
        "Create a detailed Project Assessment from these estimate facts.\n"
        f"Required section ids (in order): {', '.join(required_ids)}.\n"
        "Include ratings where useful (high/medium/low).\n"
        "Set poc_recommended true only if high uncertainty (especially AI/integration risk) warrants a Proof of Concept.\n"
        "On section poc_recommendation, set field poc_recommended consistently.\n\n"
        f"FACTS:\n{_snapshot_facts(snapshot, locale)}\n"
    )


def build_proposal_system_prompt(locale: Locale) -> str:
    language = _language(locale)
    return (
        "You are writing a client-facing project proposal for executives and business stakeholders.\n"
        f"Write all titles and prose in {language}.\n"
        "Make each section detailed and concrete (paragraphs + bullets where helpful).\n"
        "Do not invent commercial numbers or schedule dates; quote the provided facts.\n"
        "Avoid developer jargon; prefer business outcomes.\n"
        "Include a simple top-down (TD) mermaid flowchart for solution overview "
        "(portrait-friendly; do not use LR/RL).\n"
        "Milestones must use dates from the provided timeline phases when available.\n"
        "Return JSON matching the required schema exactly."
    )


def build_proposal_user_prompt(
    snapshot: dict[str, Any],
    assessment: dict[str, Any],
    locale: Locale,
) -> str:
    required_ids = [
        "executive_summary",
        "objectives",
        "proposed_solution",
        "included_scope",
        "excluded_scope",
        "deliverables",
        "timeline_summary",
        "cost_summary",
        "assumptions",
        "risks",
        "next_steps",
    ]
    return (
        "Create a detailed Project Proposal.\n"
        f"Required section ids (in order): {', '.join(required_ids)}.\n"
        "Align recommendation tone with the Assessment.\n"
        "Cost summary must restate one-time project cost, monthly recurring cost, and first-year total "
        "using the provided JPY figures (full phrases, no NRC/RC abbreviations).\n"
        "Include diagrams[0] as mermaid flowchart TD (top-down, not LR) for solution overview.\n"
        "Include milestones for kickoff, each phase end, and delivery acceptance when dates exist.\n\n"
        f"ASSESSMENT:\n{json.dumps(assessment, ensure_ascii=False, indent=2)}\n\n"
        f"FACTS:\n{_snapshot_facts(snapshot, locale)}\n"
    )


def build_poc_system_prompt(locale: Locale) -> str:
    language = _language(locale)
    return (
        "You are writing an enterprise Proof of Concept document for business and technical stakeholders.\n"
        f"Write all titles and prose in {language}.\n"
        "Focus on demonstrating technical feasibility, not production readiness.\n"
        "Use clear professional language with headings, bullets, and tables where helpful.\n"
        "Derive the project brief from estimate facts. When a fact is missing, write an explicit "
        "assumption marker — in English use 'Assumption: ...'; in Japanese use '前提: ...' — "
        "never invent official hours, costs, or calendar dates for engine pricing.\n"
        "Select only feature ids from the provided catalog for Proof of Concept scope "
        "(prefer high-uncertainty / AI / integration items).\n"
        "Include at least one mermaid architecture diagram and useful tables "
        "(e.g. risks/mitigation, technology stack, timeline).\n"
        "Spell out Proof of Concept; do not use bare abbreviations like POC, NRC, or RC.\n"
        "Return JSON matching the required schema exactly."
    )


def build_poc_user_prompt(
    snapshot: dict[str, Any],
    assessment: dict[str, Any],
    locale: Locale,
) -> str:
    from app.proposals.schemas_ai import POC_SECTION_IDS

    return (
        "Create a complete enterprise Proof of Concept document.\n"
        "Fill project_brief from facts (project_name, project_description, business_problem, "
        "target_users, technology_stack, constraints). "
        "Mark gaps with locale-appropriate assumption wording (Assumption: / 前提:).\n"
        f"Required section ids (in order): {', '.join(POC_SECTION_IDS)}.\n"
        "Put selected feature ids in selected_feature_ids AND in section scope_in.feature_ids.\n"
        "scope_out lists deferred full-delivery items.\n"
        "Use localized feature names in bullets when name_ja/name_en are provided.\n"
        "Select 3–6 features when possible; never invent ids.\n"
        "Provide suggested_validation_window as narrative guidance only.\n"
        "Include diagrams (mermaid flowchart TD / top-down only — not LR) for proposed "
        "architecture and optionally a validation flow.\n"
        "Include tables for technology stack and risks/mitigation at minimum.\n"
        "Include milestones for the Proof of Concept validation phases when timeline facts exist.\n\n"
        f"ASSESSMENT:\n{json.dumps(assessment, ensure_ascii=False, indent=2)}\n\n"
        f"FACTS:\n{_snapshot_facts(snapshot, locale)}\n"
    )
