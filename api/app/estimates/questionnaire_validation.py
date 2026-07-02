from __future__ import annotations

from typing import Any


def _non_empty_text(form_data: dict[str, Any], key: str) -> bool:
    return bool(str(form_data.get(key) or "").strip())


def missing_questionnaire_fields_for_calculation(
    *,
    has_documents: bool,
    form_data: dict[str, Any],
    contact_user: bool = False,
) -> list[str]:
    missing: list[str] = []

    has_scope_signal = (
        has_documents
        or _non_empty_text(form_data, "scope_boundaries")
        or _non_empty_text(form_data, "required_features")
    )
    if not has_scope_signal:
        missing.append("scope_signal")

    if contact_user:
        return missing

    if not _non_empty_text(form_data, "data_complexity"):
        missing.append("data_complexity")
    if not _non_empty_text(form_data, "ui_complexity"):
        missing.append("ui_complexity")

    return missing
