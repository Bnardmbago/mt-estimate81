"""Locale-aware prompts for detailed stakeholder proposal generation."""

from __future__ import annotations

import json
from typing import Any, Literal

from app.proposals.generation_presets import (
    GenerationPurpose,
    get_preset,
    min_tables_for_part,
)

Locale = Literal["ja", "en"]


def _language(locale: Locale) -> str:
    return "Japanese" if locale == "ja" else "English"


def _section_depth_line(locale: Locale, purpose: GenerationPurpose) -> str:
    preset = get_preset(purpose)
    if locale == "ja":
        return preset.section_guidance_ja
    return preset.section_guidance


def _visual_aids_line(
    *,
    part: Literal["assessment", "proposal", "poc"],
    purpose: GenerationPurpose,
) -> str:
    preset = get_preset(purpose)
    diagrams = preset.min_diagrams
    if part == "assessment":
        return ""
    tables = min_tables_for_part(purpose, part)
    if part == "poc":
        if tables <= 1:
            return (
                f"Include visual aids: at least {diagrams} mermaid diagram(s) "
                f"(architecture) and at least {tables} table "
                "(e.g. risks/mitigation or technology stack).\n"
            )
        return (
            f"Always include visual aids: at least {diagrams} mermaid diagrams "
            "(architecture + validation or data/integration flow) and at least "
            f"{tables} tables (technology stack, risks/mitigation, and timeline or "
            "success-criteria matrix).\n"
        )
    # proposal
    if tables <= 1:
        return (
            f"Include visual aids: at least {diagrams} mermaid diagram(s) "
            f"(solution overview) and at least {tables} table "
            "(e.g. cost/timeline or risks/mitigation).\n"
        )
    return (
        f"Always include visual aids: at least {diagrams} mermaid diagrams "
        "(solution overview + delivery or integration flow) and at least "
        f"{tables} tables (e.g. cost/timeline summary and risks/mitigation).\n"
    )


def _user_visual_requirements(
    *,
    part: Literal["proposal", "poc"],
    purpose: GenerationPurpose,
) -> str:
    preset = get_preset(purpose)
    diagrams = preset.min_diagrams
    tables = min_tables_for_part(purpose, part)
    if part == "poc":
        diagram_detail = (
            "proposed architecture"
            if diagrams <= 1
            else "(1) proposed architecture, (2) validation or integration flow"
        )
        table_detail = (
            "technology stack or risks/mitigation"
            if tables <= 1
            else "technology stack, risks/mitigation, and a timeline or success-criteria matrix"
        )
        return (
            f"Include diagrams[] with at least {diagrams} mermaid flowchart TD source(s) "
            f"(top-down only — not LR/RL): {diagram_detail}. "
            "Each diagram needs a clear title and readable node labels.\n"
            f"Include tables[] with at least {tables} entr"
            f"{'y' if tables == 1 else 'ies'} ({table_detail}; headers + data rows).\n"
        )
    diagram_detail = (
        "solution overview"
        if diagrams <= 1
        else "(1) solution overview, (2) delivery or integration flow"
    )
    table_detail = (
        "cost/timeline or risks/mitigation"
        if tables <= 1
        else "cost/timeline summary and risks/mitigation"
    )
    return (
        f"Include diagrams[] with at least {diagrams} mermaid flowchart TD source(s) "
        f"(top-down only — not LR/RL): {diagram_detail}. "
        "Each diagram needs a clear title and readable node labels.\n"
        f"Include tables[] with at least {tables} entr"
        f"{'y' if tables == 1 else 'ies'} ({table_detail}; headers + multiple data rows).\n"
    )


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


def build_assessment_system_prompt(
    locale: Locale,
    *,
    purpose: GenerationPurpose = "standard",
) -> str:
    language = _language(locale)
    return (
        "You are a senior consulting partner writing a project feasibility assessment "
        "for business stakeholders (not developers).\n"
        f"Write all section titles and prose in {language}.\n"
        f"{_section_depth_line(locale, purpose)}\n"
        "Never invent costs, hours, or dates; only use figures provided in the facts.\n"
        "Use full phrases: 'one-time project cost', 'monthly recurring cost', 'Proof of Concept'. "
        "Do not use abbreviations like NRC, RC, or POC alone.\n"
        "Return JSON matching the required schema exactly."
    )


def build_assessment_user_prompt(
    snapshot: dict[str, Any],
    locale: Locale,
    *,
    purpose: GenerationPurpose = "standard",
) -> str:
    required_ids = [
        "feasibility",
        "readiness",
        "complexity",
        "risks",
        "recommendation",
        "poc_recommendation",
    ]
    depth = (
        "Keep sections concise.\n"
        if purpose == "concise"
        else "For each section write substantive analysis (not single-sentence placeholders).\n"
    )
    return (
        "Create a Project Assessment from these estimate facts.\n"
        f"Required section ids (in order): {', '.join(required_ids)}.\n"
        f"{depth}"
        "Include ratings where useful (high/medium/low).\n"
        "Set poc_recommended true only if high uncertainty (especially AI/integration risk) warrants a Proof of Concept.\n"
        "On section poc_recommendation, set field poc_recommended consistently.\n\n"
        f"FACTS:\n{_snapshot_facts(snapshot, locale)}\n"
    )


def build_proposal_system_prompt(
    locale: Locale,
    *,
    purpose: GenerationPurpose = "detailed",
) -> str:
    language = _language(locale)
    visual = _visual_aids_line(part="proposal", purpose=purpose)
    return (
        "You are writing a client-facing project proposal for executives and business stakeholders.\n"
        f"Write all titles and prose in {language}.\n"
        f"{_section_depth_line(locale, purpose)}\n"
        "Do not invent commercial numbers or schedule dates; quote the provided facts.\n"
        "Avoid developer jargon; prefer business outcomes.\n"
        f"{visual}"
        "Mermaid diagrams must be top-down (TD) flowchart only — portrait-friendly; do not use LR/RL.\n"
        "Milestones must use dates from the provided timeline phases when available.\n"
        "Use full phrases: 'one-time project cost', 'monthly recurring cost', 'Proof of Concept'. "
        "Do not use abbreviations like NRC, RC, or POC alone.\n"
        "Return JSON matching the required schema exactly."
    )


def build_proposal_user_prompt(
    snapshot: dict[str, Any],
    assessment: dict[str, Any],
    locale: Locale,
    *,
    purpose: GenerationPurpose = "detailed",
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
    body_rule = (
        "Keep each section body short (1–2 sentences) while remaining concrete.\n"
        if purpose == "concise"
        else "For EVERY section: write a multi-sentence body that explains context, approach, and "
        "why it matters; avoid single-sentence placeholders.\n"
    )
    return (
        "Create a Project Proposal.\n"
        f"Required section ids (in order): {', '.join(required_ids)}.\n"
        f"{body_rule}"
        "Prefer bullets under objectives, included_scope, excluded_scope, deliverables, "
        "assumptions, risks, cost_summary, and next_steps.\n"
        "Align recommendation tone with the Assessment.\n"
        "Cost summary must restate one-time project cost, monthly recurring cost, and first-year total "
        "using the provided JPY figures (full phrases, no NRC/RC abbreviations).\n"
        f"{_user_visual_requirements(part='proposal', purpose=purpose)}"
        "Include milestones for kickoff, each phase end, and delivery acceptance when dates exist.\n\n"
        f"ASSESSMENT:\n{json.dumps(assessment, ensure_ascii=False, indent=2)}\n\n"
        f"FACTS:\n{_snapshot_facts(snapshot, locale)}\n"
    )


def build_poc_system_prompt(
    locale: Locale,
    *,
    purpose: GenerationPurpose = "detailed",
) -> str:
    language = _language(locale)
    visual = _visual_aids_line(part="poc", purpose=purpose)
    return (
        "You are writing an enterprise Proof of Concept document for business and technical stakeholders.\n"
        f"Write all titles and prose in {language}.\n"
        "Focus on demonstrating technical feasibility, not production readiness.\n"
        f"{_section_depth_line(locale, purpose)}\n"
        "Use clear professional language with headings, bullets, tables, and diagrams.\n"
        "Derive the project brief from estimate facts. When a fact is missing, write an explicit "
        "assumption marker — in English use 'Assumption: ...'; in Japanese use '前提: ...' — "
        "never invent official hours, costs, or calendar dates for engine pricing.\n"
        "Select only feature ids from the provided catalog for Proof of Concept scope "
        "(prefer high-uncertainty / AI / integration items).\n"
        f"{visual}"
        "Spell out Proof of Concept; do not use bare abbreviations like POC, NRC, or RC.\n"
        "Return JSON matching the required schema exactly."
    )


def build_poc_user_prompt(
    snapshot: dict[str, Any],
    assessment: dict[str, Any],
    locale: Locale,
    *,
    purpose: GenerationPurpose = "detailed",
) -> str:
    from app.proposals.schemas_ai import POC_SECTION_IDS

    body_rule = (
        "Keep each section body short (1–2 sentences) while remaining concrete.\n"
        if purpose == "concise"
        else "For EVERY section: write a multi-sentence body that explains context, approach, and "
        "why it matters for feasibility; avoid single-sentence placeholders.\n"
    )
    brief_rule = (
        "Fill project_brief from facts briefly. "
        if purpose == "concise"
        else "Fill project_brief from facts (project_name, project_description, business_problem, "
        "target_users, technology_stack, constraints) with substantive sentences — not stubs. "
    )
    return (
        "Create an enterprise Proof of Concept document.\n"
        f"{brief_rule}"
        "Mark gaps with locale-appropriate assumption wording (Assumption: / 前提:).\n"
        f"Required section ids (in order): {', '.join(POC_SECTION_IDS)}.\n"
        f"{body_rule}"
        "Prefer bullets under objectives, scope_in, scope_out, success_criteria, assumptions, "
        "risks_mitigation, deliverables, and recommendations.\n"
        "Put selected feature ids in selected_feature_ids AND in section scope_in.feature_ids.\n"
        "scope_out lists deferred full-delivery items.\n"
        "Use localized feature names in bullets when name_ja/name_en are provided.\n"
        "Select 3–6 features when possible; never invent ids.\n"
        "Provide suggested_validation_window as narrative guidance only.\n"
        f"{_user_visual_requirements(part='poc', purpose=purpose)}"
        "Include milestones for the Proof of Concept validation phases when timeline facts exist.\n\n"
        f"ASSESSMENT:\n{json.dumps(assessment, ensure_ascii=False, indent=2)}\n\n"
        f"FACTS:\n{_snapshot_facts(snapshot, locale)}\n"
    )


def build_presentation_recommend_system_prompt(locale: Locale) -> str:
    return (
        f"You recommend Theme, Style, and Template presets for a stakeholder proposal pack. "
        f"Respond in {_language(locale)} for rationale only. "
        "Choose ONLY from the provided catalog ids. "
        "Theme = branding/colors; Style = spacing/typography density; "
        "Template = page layout (cover/columns/chrome). "
        "Do not invent ids."
    )


def build_presentation_recommend_user_prompt(
    snapshot: dict[str, Any],
    catalog: dict[str, list[dict[str, str]]],
    locale: Locale,
    *,
    include_poc: bool,
) -> str:
    return (
        "Recommend the best theme_id, style_id, and template_id for this proposal.\n"
        f"include_poc={include_poc}\n"
        "Prefer classic-linear for standard packs; executive-cover for larger/executive audiences; "
        "two-column-summary when cost/timeline density is high.\n"
        "Prefer comfortable style unless the pack is very long (compact) or sparse (spacious).\n"
        "Prefer corporate-navy unless the brief suggests modern tech (modern-slate) or "
        "warm brand tone (warm-editorial).\n\n"
        f"CATALOG:\n{json.dumps(catalog, ensure_ascii=False, indent=2)}\n\n"
        f"FACTS:\n{_snapshot_facts(snapshot, locale)}\n"
    )
