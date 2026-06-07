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
        "Identify risks, gaps, and note any uncertainty in confidence_notes."
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
