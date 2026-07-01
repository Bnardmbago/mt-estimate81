from __future__ import annotations

DEFAULT_PROJECT_NAMES = frozenset({"New Estimate", "新規見積"})


def is_usable_project_name(name: str | None) -> bool:
    trimmed = (name or "").strip()
    return bool(trimmed) and trimmed not in DEFAULT_PROJECT_NAMES
