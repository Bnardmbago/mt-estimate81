import json
from typing import Any, Literal

MAX_DOCUMENT_CHARS = 80_000


def _truncate_document_texts(texts: list[str]) -> tuple[list[str], str | None]:
    combined_len = sum(len(text) for text in texts)
    if combined_len <= MAX_DOCUMENT_CHARS:
        return texts, None

    truncated: list[str] = []
    remaining = MAX_DOCUMENT_CHARS
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
        f"Document texts were truncated from {combined_len:,} to {MAX_DOCUMENT_CHARS:,} characters. "
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
        "Identify risks, gaps, and note any uncertainty in confidence_notes.\n"
        "Provide confidence_score (0-100) and accuracy_level (high if score >= 80, "
        "medium if 50-79, low if below 50).\n"
        "List confidence_factors, missing_inputs, recommendations, estimation_warnings, "
        "assumption_risks, and estimate_exclusions (items not included in this estimate).\n"
        "Set estimate_type from the project (e.g. web application, mobile app, integration).\n"
        "Provide cost_drivers as major factors affecting cost with signed impact_jpy in JPY "
        "(positive means cost increase)."
    )


def build_user_prompt(
    form_data: dict[str, Any],
    texts: list[str],
    rate_card_roles: list[dict[str, Any]] | None = None,
) -> str:
    roles = rate_card_roles or []
    truncated_texts, truncation_note = _truncate_document_texts(texts)

    sections = [
        "## Questionnaire Answers",
        json.dumps(form_data, ensure_ascii=False, indent=2),
        "## Rate Card Roles and Phases",
        json.dumps(roles, ensure_ascii=False, indent=2),
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
) -> str:
    truncated_texts, truncation_note = _truncate_document_texts(document_texts)

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
        "Suggest only NEW line items not already listed.\n"
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
) -> str:
    truncated_texts, truncation_note = _truncate_document_texts(document_texts)
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


def build_rate_card_system_prompt(locale: Literal["ja", "en"]) -> str:
    language = "Japanese" if locale == "ja" else "English"
    return (
        "You are an expert software project estimator and rate card analyst. "
        "Analyze the project questionnaire and document excerpts to recommend a rate card "
        "for effort and cost estimation.\n\n"
        f"Write generation_notes in {language}.\n"
        "Return valid JSON matching the required schema exactly.\n\n"
        "Recommend:\n"
        "- development_approach: one of traditional, ai_assisted, hybrid, low_code\n"
        "- roles: project roles with hourly_rate_jpy in JPY (include PM, developer, QA at minimum)\n"
        "- phases: requirement, design, development, testing, deployment with percentages summing to 1.0\n"
        "- contingency_rate, overhead_rate, tax_rate as decimals (e.g. 0.15 for 15%)\n"
        "- productivity.hours_per_feature_default: typical hours per feature for this project\n"
        "- setup_cost_items: one-time NRC setup costs in JPY (e.g. infrastructure, tooling, licenses, "
        "environment setup, third-party integration fees). Provide 2–6 line items derived from the "
        "project form and documents when possible.\n"
        "- monthly_rc_items: recurring monthly RC costs in JPY (e.g. hosting, monitoring, support, "
        "SaaS subscriptions, maintenance). Provide 1–5 line items derived from the project form and "
        "documents when possible.\n"
        "- generation_notes: brief rationale for key assumptions\n"
        "- used_default_assumptions: list field names where you had insufficient info and used "
        "reasonable industry defaults (empty list if confident)\n\n"
        "Base rates on project complexity, team location hints, technology stack, and delivery model "
        "when evident from the inputs. Use conservative JPY rates for Japan unless documents suggest otherwise."
    )


def build_rate_card_user_prompt(
    *,
    project_name: str,
    client_name: str,
    form_data: dict[str, Any],
    document_texts: list[str],
) -> str:
    truncated_texts, truncation_note = _truncate_document_texts(document_texts)

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

    if truncation_note:
        sections.extend(["## Truncation Notice", truncation_note])

    return "\n\n".join(sections)
