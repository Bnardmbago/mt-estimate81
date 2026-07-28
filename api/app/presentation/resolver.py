"""Resolve Theme / Style / Template presets into a PresentationBundle."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exports.theme import EXPORT_THEME
from app.models.presentation import PresentationStyle, PresentationTemplate, PresentationTheme
from app.models.system_config import SystemConfig
from app.presentation.accent_shapes import resolve_accent_shapes
from app.presentation.seeds import (
    CLASSIC_LINEAR_TEMPLATE,
    COMFORTABLE_STYLE,
    CORPORATE_NAVY_CONFIG,
    DEFAULT_COVER_DESIGN,
    DEFAULT_PAGE,
    DEFAULT_STYLE_ID,
    DEFAULT_TEMPLATE_ID,
    DEFAULT_THEME_ID,
)
from app.presentation.validators import clamp_cover_design, normalize_page


THEME_HEX_COLOR_RE = re.compile(r"^[0-9A-Fa-f]{6}$")


def _safe_theme_color(value: Any, fallback: str) -> str:
    """Return a safe six-digit hex token without the CSS '#' prefix."""
    if isinstance(value, str):
        candidate = value[1:] if value.startswith("#") else value
        if THEME_HEX_COLOR_RE.fullmatch(candidate):
            return candidate
    return fallback.lstrip("#")


@dataclass
class PresentationBundle:
    theme_id: str
    style_id: str
    template_id: str
    theme_tokens: dict[str, Any] = field(default_factory=dict)
    style_tokens: dict[str, Any] = field(default_factory=dict)
    layout: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    accent_warnings: list[str] = field(default_factory=list)
    theme_name: str = ""
    style_name: str = ""
    template_name: str = ""
    logo_storage_path: str | None = None
    page: dict[str, str] = field(default_factory=lambda: deepcopy(DEFAULT_PAGE))
    cover_design: dict[str, Any] = field(default_factory=dict)
    cover_fields: list[dict[str, Any]] = field(default_factory=list)
    cover_assets: list[dict[str, Any]] = field(default_factory=list)

    def theme_color_map(self) -> dict[str, str]:
        """Flat color map compatible with legacy EXPORT_THEME / Jinja ctx.theme."""
        raw_colors = self.theme_tokens.get("colors")
        colors = dict(raw_colors) if isinstance(raw_colors, dict) else {}
        # Legacy aliases used by DOCX/XLSX/PDF
        primary = _safe_theme_color(colors.get("primary"), EXPORT_THEME["primary"])
        primary_light = _safe_theme_color(
            colors.get("primary_light"),
            EXPORT_THEME["primary_light"],
        )
        surface = _safe_theme_color(colors.get("surface"), EXPORT_THEME["surface"])
        border = _safe_theme_color(colors.get("border"), EXPORT_THEME["border"])
        border_light = _safe_theme_color(
            colors.get("border_light"),
            EXPORT_THEME["border_light"],
        )
        text_body = _safe_theme_color(
            colors.get("text_body"),
            EXPORT_THEME["text_body"],
        )
        text_muted = _safe_theme_color(
            colors.get("text_muted"),
            EXPORT_THEME["text_muted"],
        )
        accent = _safe_theme_color(colors.get("accent"), EXPORT_THEME["accent"])
        text_on_primary = _safe_theme_color(
            colors.get("text_on_primary"),
            EXPORT_THEME["text_on_primary"],
        )
        return {
            "primary": primary,
            "primary_light": primary_light,
            "surface": surface,
            "border": border,
            "border_light": border_light,
            "text_body": text_body,
            "text_muted": text_muted,
            "accent": accent,
            "blue_primary": primary,
            "blue_light": primary_light,
            "yellow_section": surface,
            "yellow_total": primary_light,
            "text_on_primary": text_on_primary,
            "border_legacy": _safe_theme_color(
                colors.get("border_light"),
                EXPORT_THEME["border_legacy"],
            ),
            "table_header": _safe_theme_color(colors.get("table_header"), primary),
            "table_row_alt": _safe_theme_color(colors.get("table_row_alt"), primary_light),
            "chart": _safe_theme_color(colors.get("chart"), accent),
            "callout": _safe_theme_color(colors.get("callout"), accent),
            "table_highlight": _safe_theme_color(
                colors.get("table_highlight"),
                accent,
            ),
        }

    def css_var_map(self) -> dict[str, str]:
        colors = self.theme_color_map()
        style = self.style_tokens
        layout = self.layout
        fonts = self.theme_tokens.get("fonts") or {}

        def hex_css(value: str) -> str:
            v = (value or "").lstrip("#")
            return f"#{v}" if v else "#1E3A5F"

        return {
            "--proposal-primary": hex_css(colors["primary"]),
            "--proposal-primary-light": hex_css(colors["primary_light"]),
            "--proposal-surface": hex_css(colors["surface"]),
            "--proposal-border": hex_css(colors["border"]),
            "--proposal-text": hex_css(colors["text_body"]),
            "--proposal-muted": hex_css(colors["text_muted"]),
            "--proposal-accent": hex_css(colors["accent"]),
            "--proposal-on-primary": hex_css(colors["text_on_primary"]),
            "--proposal-callout": hex_css(colors["callout"]),
            "--proposal-font-heading": fonts.get("heading", "Noto Sans JP, Helvetica, Arial, sans-serif"),
            "--proposal-font-body": fonts.get("body", "Noto Sans JP, Helvetica, Arial, sans-serif"),
            "--proposal-base-size": f"{style.get('base_font_size_pt', 10)}pt",
            "--proposal-line-height": str(style.get("line_spacing", 1.4)),
            "--proposal-layout": str(layout.get("layout", "linear")),
        }

    def layout_class(self) -> str:
        layout = self.layout.get("layout") or "linear"
        return f"proposal-layout-{layout.replace('_', '-')}"

    def page_css_size(self) -> str:
        """Return the CSS @page size value for this presentation."""
        return f"{self.page['size']} {self.page['orientation']}"


def _deep_merge(base: dict, overlay: dict) -> dict:
    result = deepcopy(base)
    for key, value in (overlay or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


async def get_default_theme(db: AsyncSession) -> PresentationTheme | None:
    result = await db.execute(
        select(PresentationTheme).where(
            PresentationTheme.is_default.is_(True),
            PresentationTheme.is_active.is_(True),
        )
    )
    row = result.scalar_one_or_none()
    if row:
        return row
    result = await db.execute(
        select(PresentationTheme).where(PresentationTheme.id == DEFAULT_THEME_ID)
    )
    return result.scalar_one_or_none()


async def get_default_style(db: AsyncSession) -> PresentationStyle | None:
    result = await db.execute(
        select(PresentationStyle).where(
            PresentationStyle.is_default.is_(True),
            PresentationStyle.is_active.is_(True),
        )
    )
    row = result.scalar_one_or_none()
    if row:
        return row
    result = await db.execute(
        select(PresentationStyle).where(PresentationStyle.id == DEFAULT_STYLE_ID)
    )
    return result.scalar_one_or_none()


async def get_default_template(db: AsyncSession) -> PresentationTemplate | None:
    result = await db.execute(
        select(PresentationTemplate).where(
            PresentationTemplate.is_default.is_(True),
            PresentationTemplate.is_active.is_(True),
        )
    )
    row = result.scalar_one_or_none()
    if row:
        return row
    result = await db.execute(
        select(PresentationTemplate).where(PresentationTemplate.id == DEFAULT_TEMPLATE_ID)
    )
    return result.scalar_one_or_none()


async def get_default_cover_template_id(db: AsyncSession) -> str | None:
    result = await db.execute(select(SystemConfig).where(SystemConfig.id == 1))
    row = result.scalar_one_or_none()
    configured = (
        (row.presentation_default_cover_template_id or "").strip()
        if row is not None
        else ""
    )
    if not configured:
        return None
    template = await db.execute(
        select(PresentationTemplate).where(PresentationTemplate.id == configured)
    )
    preset = template.scalar_one_or_none()
    if preset is None or not preset.is_active:
        return None
    config = preset.config if isinstance(preset.config, dict) else {}
    if not config.get("cover"):
        return None
    return preset.id


async def get_presentation_defaults(db: AsyncSession) -> dict[str, str | None]:
    theme = await get_default_theme(db)
    style = await get_default_style(db)
    template = await get_default_template(db)
    return {
        "theme_id": theme.id if theme else DEFAULT_THEME_ID,
        "style_id": style.id if style else DEFAULT_STYLE_ID,
        "template_id": template.id if template else DEFAULT_TEMPLATE_ID,
        "cover_template_id": await get_default_cover_template_id(db),
    }


async def resolve_presentation(
    db: AsyncSession,
    theme_id: str | None = None,
    style_id: str | None = None,
    template_id: str | None = None,
    cover_template_id: str | None = None,
) -> PresentationBundle:
    warnings: list[str] = []

    default_theme = await get_default_theme(db)
    default_style = await get_default_style(db)
    default_template = await get_default_template(db)

    theme: PresentationTheme | None = None
    if theme_id:
        result = await db.execute(select(PresentationTheme).where(PresentationTheme.id == theme_id))
        theme = result.scalar_one_or_none()
        if theme is None:
            warnings.append(f"Unknown theme_id '{theme_id}'; using default")
        elif not theme.is_active:
            warnings.append(f"Inactive theme_id '{theme_id}'; using default")
            theme = None
    if theme is None:
        theme = default_theme

    style: PresentationStyle | None = None
    if style_id:
        result = await db.execute(select(PresentationStyle).where(PresentationStyle.id == style_id))
        style = result.scalar_one_or_none()
        if style is None:
            warnings.append(f"Unknown style_id '{style_id}'; using default")
        elif not style.is_active:
            warnings.append(f"Inactive style_id '{style_id}'; using default")
            style = None
    if style is None:
        style = default_style

    template: PresentationTemplate | None = None
    if template_id:
        result = await db.execute(
            select(PresentationTemplate).where(PresentationTemplate.id == template_id)
        )
        template = result.scalar_one_or_none()
        if template is None:
            warnings.append(f"Unknown template_id '{template_id}'; using default")
        elif not template.is_active:
            warnings.append(f"Inactive template_id '{template_id}'; using default")
            template = None
    if template is None:
        template = default_template

    cover_template: PresentationTemplate | None = None
    if cover_template_id:
        result = await db.execute(
            select(PresentationTemplate).where(PresentationTemplate.id == cover_template_id)
        )
        cover_template = result.scalar_one_or_none()
        if cover_template is None:
            warnings.append(f"Unknown cover_template_id '{cover_template_id}'; ignoring")
        elif not cover_template.is_active:
            warnings.append(f"Inactive cover_template_id '{cover_template_id}'; ignoring")
            cover_template = None
        else:
            cover_config = cover_template.config if isinstance(cover_template.config, dict) else {}
            if not cover_config.get("cover"):
                warnings.append(
                    f"cover_template_id '{cover_template_id}' has cover disabled; ignoring"
                )
                cover_template = None

    theme_tokens = _deep_merge(CORPORATE_NAVY_CONFIG, (theme.config if theme else {}) or {})
    explicit_theme_colors = (
        ((theme.config if theme else {}) or {}).get("colors") or {}
    )
    resolved_theme_colors = theme_tokens.setdefault("colors", {})
    accent = resolved_theme_colors.get("accent", EXPORT_THEME["accent"])
    for specialized_token in ("chart", "callout", "table_highlight"):
        if specialized_token not in explicit_theme_colors:
            resolved_theme_colors[specialized_token] = accent
    style_tokens = _deep_merge(COMFORTABLE_STYLE, (style.config if style else {}) or {})
    layout = _deep_merge(CLASSIC_LINEAR_TEMPLATE, (template.config if template else {}) or {})
    cover_source = cover_template or template
    cover_source_config = (cover_source.config if cover_source else {}) or {}
    if cover_template is not None:
        layout["cover"] = True
        if "cover_design" in cover_source_config:
            layout["cover_design"] = deepcopy(cover_source_config.get("cover_design") or {})
        if "cover_fields" in cover_source_config:
            layout["cover_fields"] = deepcopy(cover_source_config.get("cover_fields") or [])
        if "page" in cover_source_config:
            layout["page"] = deepcopy(cover_source_config.get("page") or layout.get("page"))
    page = normalize_page(layout.get("page"))
    merged_cover_design = _deep_merge(
        DEFAULT_COVER_DESIGN, layout.get("cover_design") or {}
    )
    template_cover_design = cover_source_config.get("cover_design")
    if (
        isinstance(template_cover_design, dict)
        and "accent" in template_cover_design
        and "accent_shapes" not in template_cover_design
    ):
        merged_cover_design.pop("accent_shapes", None)
    accent_shapes, accent_warnings = resolve_accent_shapes(
        merged_cover_design,
        page,
    )
    merged_cover_design["accent_shapes"] = accent_shapes
    merged_cover_design.pop("accent", None)
    cover_design = clamp_cover_design(merged_cover_design)
    raw_cover_fields = layout.get("cover_fields")
    cover_fields = deepcopy(raw_cover_fields) if isinstance(raw_cover_fields, list) else []
    raw_cover_assets = cover_design.get("assets")
    cover_assets = deepcopy(raw_cover_assets) if isinstance(raw_cover_assets, list) else []

    return PresentationBundle(
        theme_id=(theme.id if theme else DEFAULT_THEME_ID),
        style_id=(style.id if style else DEFAULT_STYLE_ID),
        template_id=(template.id if template else DEFAULT_TEMPLATE_ID),
        theme_tokens=theme_tokens,
        style_tokens=style_tokens,
        layout=layout,
        warnings=warnings,
        accent_warnings=accent_warnings,
        theme_name=(theme.name if theme else "Corporate Navy"),
        style_name=(style.name if style else "Comfortable"),
        template_name=(template.name if template else "Classic Linear"),
        logo_storage_path=(theme.logo_storage_path if theme else None),
        page=page,
        cover_design=cover_design,
        cover_fields=cover_fields,
        cover_assets=cover_assets,
    )
