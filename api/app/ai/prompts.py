import json
from typing import Any, Literal

MAX_DOCUMENT_CHARS = 80_000
# Smaller cap for requirement extraction keeps AI latency predictable on large specs.
MAX_EXTRACTION_DOCUMENT_CHARS = 40_000


def _truncate_document_texts(
    texts: list[str],
    *,
    max_chars: int = MAX_DOCUMENT_CHARS,
) -> tuple[list[str], str | None]:
    combined_len = sum(len(text) for text in texts)
    if combined_len <= max_chars:
        return texts, None

    truncated: list[str] = []
    remaining = max_chars
    for text in texts:
        if remaining <= 0:
            break
        if len(text) <= remaining:
            truncated.append(text)
            remaining -= len(text)
        else:
            truncated.append(text[:remaining])
            remaining = 0

    note = (
        f"Document texts were truncated from {combined_len:,} to {max_chars:,} characters. "
        "Some content may be missing from the analysis."
    )
    return truncated, note


def build_system_prompt(locale: Literal["ja", "en"]) -> str:
    language = "Japanese" if locale == "ja" else "English"
    return (
        "You are an expert software project estimator. "
        "Analyze the provided questionnaire answers and document excerpts to produce structured "
        "requirements and feature line items for effort estimation.\n\n"
        f"Write all requirement text, risks, gaps, confidence notes, and feature descriptions in {language}.\n"
        "Return valid JSON matching the required schema exactly.\n"
        "Suggested hours must be positive numbers. "
        "Use only roles and phases from the provided rate card when assigning feature items.\n"
        "Each feature item role must exactly match one rate card role name (for example developer, not designer/developer).\n"
        "Assign requirement-phase work to the PM role, design-phase work to developer, "
        "development-phase work to developer, and testing-phase work to QA whenever those roles exist.\n"
        "Include explicit PM line items for project management and requirements activities.\n"
        "Identify risks, gaps, and note any uncertainty in confidence_notes.\n"
        "Provide confidence_score (0-100) and accuracy_level (high if score >= 80, "
        "medium if 50-79, low if below 50).\n"
        "List confidence_factors, missing_inputs, recommendations, estimation_warnings, "
        "assumption_risks, and estimate_exclusions (items not included in this estimate).\n"
        "Set estimate_type from the project (e.g. web application, mobile app, integration).\n"
        "Provide cost_drivers as major factors affecting cost with signed impact_jpy in JPY "
        "(positive means cost increase).\n"
        "For large documents, prioritize the highest-impact features and keep feature_items "
        "focused (roughly 25–45 items) unless the scope clearly requires more."
    )


def build_user_prompt(
    form_data: dict[str, Any],
    texts: list[str],
    rate_card_roles: list[dict[str, Any]] | None = None,
    *,
    max_document_chars: int | None = None,
    client_constraints: Any | None = None,
    locale: Literal["ja", "en"] = "en",
    constraints_section_template: str | None = None,
) -> str:
    from app.estimates.extraction_constraints import (
        ExtractionConstraints,
        format_constraints_for_prompt,
    )

    roles = rate_card_roles or []
    truncated_texts, truncation_note = _truncate_document_texts(
        texts,
        max_chars=max_document_chars or MAX_EXTRACTION_DOCUMENT_CHARS,
    )

    sections = [
        "## Questionnaire Answers",
        json.dumps(form_data, ensure_ascii=False, indent=2),
        "## Rate Card Roles and Phases",
        json.dumps(roles, ensure_ascii=False, indent=2),
    ]

    if isinstance(client_constraints, ExtractionConstraints):
        sections.extend(
            [
                "## Client Constraints",
                format_constraints_for_prompt(
                    client_constraints,
                    locale,
                    template=constraints_section_template,
                ),
            ]
        )

    sections.append("## Document Excerpts")

    if not truncated_texts:
        sections.append("(No documents provided)")
    else:
        for index, text in enumerate(truncated_texts, start=1):
            sections.append(f"### Document {index}\n{text}")

    if truncation_note:
        sections.extend(["## Truncation Notice", truncation_note])

    return "\n\n".join(sections)


def build_form_fields_system_prompt(
    locale: Literal["ja", "en"],
    field_metadata: list[dict[str, Any]],
) -> str:
    language = "Japanese" if locale == "ja" else "English"
    return (
        "You are an expert software project estimator helping draft a project questionnaire.\n"
        f"Write all field content in {language}.\n"
        "Return valid JSON matching the required schema exactly.\n\n"
        "Populate the form_data object with values for each **specification** field listed below.\n"
        "Do not populate header/client questionnaire fields — those are provided separately and must not be changed.\n\n"
        "Use these inputs:\n"
        "- The project name and client\n"
        "- The user's prompt describing what they need\n"
        "- Client header questionnaire answers in Current Questionnaire Values (treat as fixed context)\n"
        "- Any uploaded document excerpts\n"
        "- Current specification field values (improve or fill gaps; keep good existing values)\n\n"
        "Rules:\n"
        "- For select fields, use exactly one of the allowed option values listed below.\n"
        "- Leave a field as an empty string only when there is truly insufficient information.\n"
        "- Explain assumptions, gaps, and confidence in generation_notes.\n\n"
        "## Field definitions\n"
        f"{json.dumps(field_metadata, ensure_ascii=False, indent=2)}"
    )


def build_form_fields_user_prompt(
    *,
    prompt: str,
    project_name: str,
    client_name: str,
    current_form_data: dict[str, Any],
    document_texts: list[str],
    max_document_chars: int | None = None,
) -> str:
    truncated_texts, truncation_note = _truncate_document_texts(
        document_texts,
        max_chars=max_document_chars or MAX_DOCUMENT_CHARS,
    )

    sections = [
        "## User Prompt",
        prompt.strip(),
        "## Project",
        f"Project name: {project_name}",
        f"Client: {client_name}",
        "## Current Questionnaire Values",
        json.dumps(current_form_data, ensure_ascii=False, indent=2),
        "## Document Excerpts",
    ]

    if not truncated_texts:
        sections.append("(No documents provided)")
    else:
        for index, text in enumerate(truncated_texts, start=1):
            sections.append(f"### Document {index}\n{text}")

    if truncation_note:
        sections.extend(["## Truncation Notice", truncation_note])

    return "\n\n".join(sections)


SECTION_LABELS = {
    "roles": "Roles",
    "phases": "Phases",
    "setup_cost_items": "Setup costs (NRC)",
    "monthly_rc_items": "Monthly RC items",
}


def build_rate_card_section_system_prompt(
    locale: Literal["ja", "en"],
    section: Literal["roles", "phases", "setup_cost_items", "monthly_rc_items"],
    *,
    free_form: bool = False,
) -> str:
    language = "Japanese" if locale == "ja" else "English"
    section_label = SECTION_LABELS[section]

    common = (
        "You are an expert software project estimator helping refine a rate card section.\n"
        f"Write generation_notes in {language}.\n"
        "Return valid JSON matching the required schema exactly.\n"
        "Do not duplicate items that already exist in the current section (match by name, case-insensitive).\n"
    )
    if free_form:
        common += (
            "No project is linked. Use only the user prompt and the current section state. "
            "Apply practical industry defaults and explain assumptions in generation_notes.\n"
        )
    else:
        common += (
            "Use the linked project data and the user's prompt to propose practical additions.\n"
        )

    if section == "roles":
        return (
            common
            + f"Target section: {section_label}.\n"
            "Suggest only NEW roles not already listed in the current section.\n"
            "Each role needs name and hourly_rate_jpy in JPY.\n"
            "Base rates on project complexity, team location, and technology evident in the inputs."
        )
    if section == "phases":
        return (
            common
            + f"Target section: {section_label}.\n"
            "Prefer suggesting only NEW phase rows not already in the current section.\n"
            "If the user asks to rebalance percentages, return a complete phase set with percentages "
            "summing to 1.0 and set replace_all to true.\n"
            "Otherwise set replace_all to false and return only additive phase rows."
        )
    if section == "setup_cost_items":
        return (
            common
            + f"Target section: {section_label} (one-time NRC setup costs).\n"
            "Suggest only NEW line items not already listed.\n"
            "Each item needs name and amount_jpy in JPY."
        )

    return (
        common
        + f"Target section: {section_label} (recurring monthly RC costs).\n"
        "The rate card uses five standard categories: Cloud infrastructure, System monitoring, "
        "Maintenance and Support, Security, and Backup.\n"
        "Suggest amounts for missing categories only; use standard names when adding items.\n"
        "Each item needs name and amount_jpy in JPY."
    )


def build_rate_card_section_user_prompt(
    *,
    prompt: str,
    section: Literal["roles", "phases", "setup_cost_items", "monthly_rc_items"],
    current_section: list[dict[str, Any]],
    estimate_context: dict[str, Any],
    document_texts: list[str],
    free_form: bool = False,
    max_document_chars: int | None = None,
) -> str:
    truncated_texts, truncation_note = _truncate_document_texts(
        document_texts,
        max_chars=max_document_chars or MAX_DOCUMENT_CHARS,
    )
    section_label = SECTION_LABELS[section]

    sections = [
        "## User Prompt",
        prompt.strip(),
        f"## Target Section ({section_label})",
        json.dumps(current_section, ensure_ascii=False, indent=2),
    ]

    if free_form:
        sections.extend(
            [
                "## Linked Project Context",
                "(No linked project — follow the user prompt only.)",
                "## Document Excerpts",
                "(None)",
            ]
        )
    else:
        sections.extend(
            [
                "## Linked Project Context",
                json.dumps(estimate_context, ensure_ascii=False, indent=2),
                "## Document Excerpts",
            ]
        )
        if not truncated_texts:
            sections.append("(No documents provided)")
        else:
            for index, text in enumerate(truncated_texts, start=1):
                sections.append(f"### Document {index}\n{text}")

        if truncation_note:
            sections.extend(["## Truncation Notice", truncation_note])

    return "\n\n".join(sections)


def build_rate_card_system_prompt(
    locale: Literal["ja", "en"],
    *,
    has_extraction_context: bool = False,
) -> str:
    language = "Japanese" if locale == "ja" else "English"
    extraction_guidance = ""
    if has_extraction_context:
        extraction_guidance = (
            "\nWhen complexity_profile is provided:\n"
            "- Use exactly four roles (Tech Lead, Senior Engineer, Full Stack Engineer, Engineer); "
            "adjust hourly_rate_jpy by complexity rather than adding extra roles\n"
            "- Align phase percentages with phase_guidance while keeping sum = 1.0\n"
            "- Derive setup_cost_items and monthly_rc_items from nrc_rc_guidance, integrations, "
            "and non-functional requirements\n"
            "- Increase contingency_rate for higher complexity when justified\n"
        )
    return (
        "You are an expert software project estimator and rate card analyst. "
        "Analyze the project questionnaire and document excerpts to recommend a rate card "
        "for effort and cost estimation.\n\n"
        f"Write generation_notes in {language}.\n"
        "Return valid JSON matching the required schema exactly.\n\n"
        "Recommend:\n"
        "- development_approach: one of traditional, ai_assisted, hybrid, low_code\n"
        "- roles: exactly four roles — Tech Lead, Senior Engineer, Full Stack Engineer, and Engineer — "
        "each with hourly_rate_jpy in JPY (map PM/QA/DevOps/BA work onto these four)\n"
        "- phases: requirement, design, development, testing, deployment with percentages summing to 1.0\n"
        "- contingency_rate, overhead_rate, tax_rate as decimals (e.g. 0.15 for 15%)\n"
        "- productivity.hours_per_feature_default: typical hours per feature for this project\n"
        "- setup_cost_items: one-time NRC setup costs in JPY (e.g. infrastructure, tooling, licenses, "
        "environment setup, third-party integration fees). Derive 2–8 flexible line items from "
        "cost_breakdown_hints and project context when provided.\n"
        "- monthly_rc_items: recurring monthly RC costs in JPY. Derive 2–8 flexible line items from "
        "cost_breakdown_hints, maintenance_support, and project context. Include a name, amount_jpy, "
        "and service_description for each row. Use 0 when amounts are unknown.\n"
        "- generation_notes: brief rationale for key assumptions\n"
        "- used_default_assumptions: list field names where you had insufficient info and used "
        "reasonable industry defaults (empty list if confident)\n\n"
        "Base rates on project complexity, team location hints, technology stack, and delivery model "
        "when evident from the inputs. Use conservative JPY rates for Japan unless documents suggest otherwise."
        f"{extraction_guidance}"
    )


def _summarize_extracted_data(extracted_data: dict[str, Any]) -> dict[str, Any]:
    list_fields = (
        "functional_requirements",
        "non_functional_requirements",
        "user_roles",
        "modules",
        "external_systems",
        "risks",
        "gaps",
        "cost_drivers",
        "recommendations",
        "estimation_warnings",
    )
    summary: dict[str, Any] = {}
    for key, value in extracted_data.items():
        if key == "complexity_profile":
            summary[key] = value
        elif key in list_fields and isinstance(value, list):
            summary[key] = value[:12]
            if len(value) > 12:
                summary[f"{key}_truncated_count"] = len(value)
        elif key not in ("confidence_notes",):
            summary[key] = value
    if extracted_data.get("confidence_notes"):
        notes = str(extracted_data["confidence_notes"])
        summary["confidence_notes"] = notes[:500] + ("…" if len(notes) > 500 else "")
    return summary


def _summarize_feature_items(feature_items: list[dict[str, Any]], *, limit: int = 40) -> list[dict[str, Any]]:
    summarized = []
    for item in feature_items[:limit]:
        summarized.append(
            {
                "name": item.get("name", ""),
                "hours": item.get("hours", 0),
                "phase": item.get("phase", ""),
                "role": item.get("role", ""),
            }
        )
    return summarized


def build_rate_card_user_prompt(
    *,
    project_name: str,
    client_name: str,
    form_data: dict[str, Any],
    document_texts: list[str],
    feature_items: list[dict[str, Any]] | None = None,
    extracted_data: dict[str, Any] | None = None,
    complexity_profile: dict[str, Any] | None = None,
    cost_breakdown_hints: dict[str, Any] | None = None,
    max_document_chars: int | None = None,
) -> str:
    truncated_texts, truncation_note = _truncate_document_texts(
        document_texts,
        max_chars=max_document_chars or MAX_DOCUMENT_CHARS,
    )

    sections = [
        "## Project",
        f"Project name: {project_name}",
        f"Client: {client_name}",
        "## Questionnaire Answers",
        json.dumps(form_data, ensure_ascii=False, indent=2),
        "## Document Excerpts",
    ]

    if not truncated_texts:
        sections.append("(No documents provided — use reasonable defaults and note assumptions)")
    else:
        for index, text in enumerate(truncated_texts, start=1):
            sections.append(f"### Document {index}\n{text}")

    if extracted_data:
        sections.extend(
            [
                "## Extracted Requirements Summary",
                json.dumps(_summarize_extracted_data(extracted_data), ensure_ascii=False, indent=2),
            ]
        )

    if feature_items:
        summary = _summarize_feature_items(feature_items)
        feature_section = json.dumps(summary, ensure_ascii=False, indent=2)
        if len(feature_items) > len(summary):
            feature_section += f"\n\n(Showing {len(summary)} of {len(feature_items)} feature items)"
        sections.extend(["## Feature Items Summary", feature_section])

    if complexity_profile:
        sections.extend(
            [
                "## Complexity Analysis",
                json.dumps(complexity_profile, ensure_ascii=False, indent=2),
            ]
        )

    if cost_breakdown_hints:
        sections.extend(
            [
                "## Cost Breakdown Hints",
                json.dumps(cost_breakdown_hints, ensure_ascii=False, indent=2),
            ]
        )

    if truncation_note:
        sections.extend(["## Truncation Notice", truncation_note])

    return "\n\n".join(sections)
