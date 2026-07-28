"""Cover field resolution for presentation consumers."""

from __future__ import annotations

from typing import Any

from app.i18n.localized_content import resolve_localized_dict
from app.presentation.accent_shapes import HEX_COLOR_RE
from app.presentation.validators import (
    normalize_cover_geometry,
    normalize_cover_text_style,
)

_DEFAULT_COVER_BACKGROUND = "#ffffff"
_DEFAULT_COVER_TITLE = "#1e3a5f"
_DEFAULT_COVER_TEXT = "#334155"


def normalize_cover_hex(value: Any, fallback: str) -> str:
    """Return a safe #RRGGBB color or fallback."""
    if isinstance(value, str):
        normalized = value if value.startswith("#") else f"#{value}"
        if HEX_COLOR_RE.fullmatch(normalized):
            return f"#{normalized[1:].lower()}"
    return fallback.lower() if fallback.startswith("#") else fallback


def cover_surface_colors(cover_design: dict[str, Any] | None) -> dict[str, str]:
    """Resolve cover background/title/text colors to match Admin Cover preview defaults."""
    colors = cover_design.get("colors") if isinstance(cover_design, dict) else None
    colors = colors if isinstance(colors, dict) else {}
    return {
        "background": normalize_cover_hex(
            colors.get("background"),
            _DEFAULT_COVER_BACKGROUND,
        ),
        "title": normalize_cover_hex(colors.get("title"), _DEFAULT_COVER_TITLE),
        "text": normalize_cover_hex(colors.get("text"), _DEFAULT_COVER_TEXT),
    }


def resolve_cover_fields(
    template_fields: list[dict[str, Any]] | None,
    cover_values: dict[str, Any] | None,
    *,
    display_locale: str,
    fallback_locale: str,
    document_facts: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Resolve ordered cover fields without changing stored overrides."""
    fields = template_fields if isinstance(template_fields, list) else []
    overrides = cover_values if isinstance(cover_values, dict) else {}
    localized_facts = resolve_localized_dict(
        document_facts if isinstance(document_facts, dict) else {},
        display_locale,
        fallback_locale,
    )

    resolved_fields: list[dict[str, Any]] = []
    warnings: list[str] = []

    for field in fields:
        if not isinstance(field, dict):
            continue
        raw_key = field.get("key")
        if not isinstance(raw_key, str) or not raw_key:
            continue
        key = raw_key

        content = resolve_localized_dict(
            field.get("content") if isinstance(field.get("content"), dict) else {},
            display_locale,
            fallback_locale,
        )
        label = content.get("label") or key

        value, source = _resolve_value(
            key=key,
            field=field,
            content=content,
            overrides=overrides,
            document_facts=localized_facts,
            display_locale=display_locale,
            fallback_locale=fallback_locale,
        )
        required = bool(field.get("required", False))
        if required and not _is_present(value):
            value = None
            source = "missing"
            warnings.append(f"Missing required cover field: {key}")

        resolved_field = {
            "key": key,
            "label": label,
            "value": value,
            "required": required,
            "emphasis": field.get("emphasis"),
            "source": source,
        }
        if "geometry" in field:
            geometry = normalize_cover_geometry(field.get("geometry"))
            if geometry is not None:
                resolved_field["geometry"] = geometry
        if isinstance(field.get("style"), dict):
            resolved_field["style"] = normalize_cover_text_style(field["style"])
        resolved_fields.append(resolved_field)

    return resolved_fields, warnings


def _resolve_value(
    *,
    key: str,
    field: dict[str, Any],
    content: dict[str, Any],
    overrides: dict[str, Any],
    document_facts: dict[str, Any],
    display_locale: str,
    fallback_locale: str,
) -> tuple[Any, str]:
    override = overrides.get(key)
    if isinstance(override, dict):
        localized_override = resolve_localized_dict(
            override,
            display_locale,
            fallback_locale,
        )
        override_value = localized_override.get("value")
        if _is_present(override_value):
            return override_value, "override"
    elif _is_present(override):
        # Legacy flat values remain readable while callers migrate to `_i18n`.
        return override, "override"

    auto_fill = field.get("auto_fill")
    if auto_fill is True:
        auto_fill = key
    if isinstance(auto_fill, str) and auto_fill:
        fact = _get_path(document_facts, auto_fill)
        if isinstance(fact, dict):
            fact = resolve_localized_dict(fact, display_locale, fallback_locale).get(
                "value"
            )
        if _is_present(fact):
            return fact, "auto_fill"

    default_value = content.get("default_text")
    if _is_present(default_value):
        return default_value, "default"

    return None, "missing"


def _get_path(values: dict[str, Any], path: str) -> Any:
    current: Any = values
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _is_present(value: Any) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip()))
