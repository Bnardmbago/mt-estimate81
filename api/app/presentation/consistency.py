"""Deterministic Cover-to-Theme/Style consistency recommendations."""

from __future__ import annotations

from typing import Any

MARGIN_TOLERANCE_MM = 4.0


def recommend_consistency(
    *,
    cover_design: dict[str, Any] | None,
    theme_draft: dict[str, Any] | None,
    style_draft: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Return stable, optional draft changes without mutating any input."""
    cover = cover_design if isinstance(cover_design, dict) else {}
    theme = theme_draft if isinstance(theme_draft, dict) else {}
    style = style_draft if isinstance(style_draft, dict) else {}

    suggestions: list[dict[str, Any]] = []
    color_suggestion = _title_color_suggestion(cover, theme)
    if color_suggestion:
        suggestions.append(color_suggestion)

    font_suggestion = _heading_font_suggestion(cover, theme)
    if font_suggestion:
        suggestions.append(font_suggestion)

    spacing_suggestion = _padding_suggestion(cover, style)
    if spacing_suggestion:
        suggestions.append(spacing_suggestion)

    return suggestions


def _title_color_suggestion(
    cover: dict[str, Any],
    theme: dict[str, Any],
) -> dict[str, Any] | None:
    cover_colors = cover.get("colors")
    theme_colors = theme.get("colors")
    if not isinstance(cover_colors, dict) or not isinstance(theme_colors, dict):
        return None

    cover_title = _normalize_hex(
        cover_colors.get("title", cover_colors.get("title_color"))
    )
    theme_primary = _normalize_hex(theme_colors.get("primary"))
    if not cover_title or not theme_primary:
        return None

    palette = {
        color
        for value in theme_colors.values()
        if (color := _normalize_hex(value)) is not None
    }
    if cover_title in palette:
        return None

    return {
        "id": "theme.colors.primary",
        "target": "theme",
        "field_path": "colors.primary",
        "before": theme_primary,
        "after": cover_title,
        "confidence": 0.9,
        "rationale": "Cover title color is outside Theme palette",
    }


def _heading_font_suggestion(
    cover: dict[str, Any],
    theme: dict[str, Any],
) -> dict[str, Any] | None:
    typography = cover.get("typography")
    fonts = theme.get("fonts")
    if not isinstance(typography, dict) or not isinstance(fonts, dict):
        return None

    cover_font = _first_text(
        typography.get("heading_font"),
        typography.get("title_font"),
        typography.get("font_family"),
    )
    theme_font = _first_text(fonts.get("heading"))
    if not cover_font or not theme_font or cover_font.casefold() == theme_font.casefold():
        return None

    return {
        "id": "theme.fonts.heading",
        "target": "theme",
        "field_path": "fonts.heading",
        "before": theme_font,
        "after": cover_font,
        "confidence": 0.9,
        "rationale": "Cover heading font differs from Theme heading font",
    }


def _padding_suggestion(
    cover: dict[str, Any],
    style: dict[str, Any],
) -> dict[str, Any] | None:
    padding = _number(cover.get("padding_mm"))
    margins = style.get("margins")
    if padding is None or not isinstance(margins, dict) or not margins:
        return None

    margin_values = [_number(value) for value in margins.values()]
    comparable = [value for value in margin_values if value is not None]
    if not comparable or all(
        abs(padding - value) <= MARGIN_TOLERANCE_MM for value in comparable
    ):
        return None

    normalized_padding: int | float = int(padding) if padding.is_integer() else padding
    return {
        "id": "style.margins.cover_padding",
        "target": "style",
        "field_path": "margins",
        "before": dict(margins),
        "after": {
            side: normalized_padding
            for side in ("top_mm", "right_mm", "bottom_mm", "left_mm")
        },
        "confidence": 0.8,
        "rationale": "Cover padding differs materially from Style margins",
    }


def _normalize_hex(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lstrip("#").upper()
    if len(normalized) not in {6, 8}:
        return None
    if any(character not in "0123456789ABCDEF" for character in normalized):
        return None
    return normalized


def _first_text(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
