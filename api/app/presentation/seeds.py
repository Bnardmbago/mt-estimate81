"""Seeded Theme / Style / Template presets for Proposal presentation."""

from __future__ import annotations

from app.exports.theme import EXPORT_THEME

CORPORATE_NAVY_CONFIG: dict = {
    "colors": {
        "primary": EXPORT_THEME["primary"],
        "primary_light": EXPORT_THEME["primary_light"],
        "surface": EXPORT_THEME["surface"],
        "border": EXPORT_THEME["border"],
        "border_light": EXPORT_THEME["border_light"],
        "text_body": EXPORT_THEME["text_body"],
        "text_muted": EXPORT_THEME["text_muted"],
        "accent": EXPORT_THEME["accent"],
        "text_on_primary": EXPORT_THEME["text_on_primary"],
        "table_header": EXPORT_THEME["primary"],
        "table_row_alt": EXPORT_THEME["primary_light"],
        "chart": EXPORT_THEME["accent"],
    },
    "fonts": {
        "heading": "Noto Sans JP, Helvetica, Arial, sans-serif",
        "body": "Noto Sans JP, Helvetica, Arial, sans-serif",
    },
    "watermark": False,
}

MODERN_SLATE_CONFIG: dict = {
    "colors": {
        "primary": "0F172A",
        "primary_light": "E2E8F0",
        "surface": "F8FAFC",
        "border": "CBD5E1",
        "border_light": "E2E8F0",
        "text_body": "0F172A",
        "text_muted": "64748B",
        "accent": "0EA5E9",
        "text_on_primary": "FFFFFF",
        "table_header": "0F172A",
        "table_row_alt": "F1F5F9",
        "chart": "0EA5E9",
    },
    "fonts": {
        "heading": "Noto Sans JP, Helvetica, Arial, sans-serif",
        "body": "Noto Sans JP, Helvetica, Arial, sans-serif",
    },
    "watermark": False,
}

WARM_EDITORIAL_CONFIG: dict = {
    "colors": {
        "primary": "3F2E22",
        "primary_light": "F3EDE6",
        "surface": "FAF7F2",
        "border": "D6C7B8",
        "border_light": "E8DFD4",
        "text_body": "2C241C",
        "text_muted": "7A6A5A",
        "accent": "B45309",
        "text_on_primary": "FFFFFF",
        "table_header": "3F2E22",
        "table_row_alt": "F3EDE6",
        "chart": "B45309",
    },
    "fonts": {
        "heading": "Noto Sans JP, Georgia, serif",
        "body": "Noto Sans JP, Helvetica, Arial, sans-serif",
    },
    "watermark": False,
}

COMPACT_STYLE: dict = {
    "margins": {"top_mm": 12, "right_mm": 12, "bottom_mm": 12, "left_mm": 12},
    "paragraph_spacing_em": 0.4,
    "line_spacing": 1.25,
    "base_font_size_pt": 9,
    "heading_scale": {"h1": 1.6, "h2": 1.35, "h3": 1.15},
    "list_indent_mm": 4,
    "table_cell_padding_pt": 4,
    "header_footer_font_size_pt": 8,
}

COMFORTABLE_STYLE: dict = {
    "margins": {"top_mm": 18, "right_mm": 16, "bottom_mm": 18, "left_mm": 16},
    "paragraph_spacing_em": 0.65,
    "line_spacing": 1.4,
    "base_font_size_pt": 10,
    "heading_scale": {"h1": 1.8, "h2": 1.45, "h3": 1.2},
    "list_indent_mm": 6,
    "table_cell_padding_pt": 6,
    "header_footer_font_size_pt": 9,
}

SPACIOUS_STYLE: dict = {
    "margins": {"top_mm": 24, "right_mm": 20, "bottom_mm": 24, "left_mm": 20},
    "paragraph_spacing_em": 0.9,
    "line_spacing": 1.55,
    "base_font_size_pt": 11,
    "heading_scale": {"h1": 2.0, "h2": 1.55, "h3": 1.25},
    "list_indent_mm": 8,
    "table_cell_padding_pt": 8,
    "header_footer_font_size_pt": 9,
}

DEFAULT_PAGE: dict = {"size": "A4", "orientation": "portrait"}

DEFAULT_ACCENT_SHAPES: list[dict] = [
    {
        "id": "default-left-stripe",
        "name": "Left stripe",
        "type": "rectangle",
        "visible": True,
        "locked": False,
        "geometry": {
            "x_pct": 0.0,
            "y_pct": 0.0,
            "width_pct": 48.0 / 210.0 * 100.0,
            "height_pct": 100.0,
            "rotation_deg": 0.0,
            "z_index": 1,
        },
        "fill": {"mode": "theme", "opacity": 0.9},
        "border": {
            "enabled": False,
            "color": "#000000",
            "width_pt": 0.0,
            "style": "solid",
            "radius_pct": 0.0,
        },
        "pattern": {
            "type": "none",
            "color": "#ffffff",
            "scale": 1.0,
            "spacing": 1.0,
            "opacity": 0.25,
        },
    }
]

DEFAULT_COVER_DESIGN: dict = {
    "alignment": "left",
    "padding_mm": 24,
    "accent_shapes": DEFAULT_ACCENT_SHAPES,
    "typography": {"title_pt": 30, "metadata_pt": 10},
    "colors": {
        "background": "FFFFFF",
        "title": "1E3A5F",
        "text": "334155",
    },
    "assets": [],
}

DEFAULT_COVER_FIELDS: list[dict] = [
    {
        "key": "title",
        "emphasis": "title",
        "required": False,
        "auto_fill": "project_name",
        "content": {
            "_i18n": {
                "en": {"label": "Title", "default_text": "Proposal title"},
                "ja": {"label": "タイトル", "default_text": "提案書タイトル"},
            }
        },
    }
]

CLASSIC_LINEAR_TEMPLATE: dict = {
    "layout": "linear",
    "cover": False,
    "page": DEFAULT_PAGE,
    "cover_fields": [],
    "cover_design": DEFAULT_COVER_DESIGN,
    "toc_style": "simple",
    "section_chrome": "ruled",
    "columns": 1,
    "header_slot": "title",
    "footer_slot": "page_number",
}

EXECUTIVE_COVER_TEMPLATE: dict = {
    "layout": "executive_cover",
    "cover": True,
    "page": DEFAULT_PAGE,
    "cover_fields": DEFAULT_COVER_FIELDS,
    "cover_design": DEFAULT_COVER_DESIGN,
    "toc_style": "numbered",
    "section_chrome": "minimal",
    "columns": 1,
    "header_slot": "title_logo",
    "footer_slot": "page_number",
}

TWO_COLUMN_SUMMARY_TEMPLATE: dict = {
    "layout": "two_column",
    "cover": False,
    "page": DEFAULT_PAGE,
    "cover_fields": [],
    "cover_design": DEFAULT_COVER_DESIGN,
    "toc_style": "simple",
    "section_chrome": "cards",
    "columns": 2,
    "header_slot": "title",
    "footer_slot": "page_number",
}

SEED_THEMES: list[dict] = [
    {
        "id": "corporate-navy",
        "name": "Corporate Navy",
        "description": "Default branded navy/blue look aligned with current exports.",
        "is_default": True,
        "is_active": True,
        "config": CORPORATE_NAVY_CONFIG,
    },
    {
        "id": "modern-slate",
        "name": "Modern Slate",
        "description": "Cool slate primary with sky accent.",
        "is_default": False,
        "is_active": True,
        "config": MODERN_SLATE_CONFIG,
    },
    {
        "id": "warm-editorial",
        "name": "Warm Editorial",
        "description": "Warm brown primary with amber accent.",
        "is_default": False,
        "is_active": True,
        "config": WARM_EDITORIAL_CONFIG,
    },
]

SEED_STYLES: list[dict] = [
    {
        "id": "compact",
        "name": "Compact",
        "description": "Tighter margins and smaller type for dense packs.",
        "is_default": False,
        "is_active": True,
        "config": COMPACT_STYLE,
    },
    {
        "id": "comfortable",
        "name": "Comfortable",
        "description": "Balanced spacing and typography (default).",
        "is_default": True,
        "is_active": True,
        "config": COMFORTABLE_STYLE,
    },
    {
        "id": "spacious",
        "name": "Spacious",
        "description": "More white space and larger type for readability.",
        "is_default": False,
        "is_active": True,
        "config": SPACIOUS_STYLE,
    },
]

SEED_TEMPLATES: list[dict] = [
    {
        "id": "classic-linear",
        "name": "Classic Linear",
        "description": "Single-column linear section flow (default).",
        "is_default": True,
        "is_active": True,
        "config": CLASSIC_LINEAR_TEMPLATE,
    },
    {
        "id": "executive-cover",
        "name": "Executive Cover",
        "description": "Cover page plus minimal section chrome.",
        "is_default": False,
        "is_active": True,
        "config": EXECUTIVE_COVER_TEMPLATE,
    },
    {
        "id": "two-column-summary",
        "name": "Two-Column Summary",
        "description": "Two-column summary blocks with card chrome.",
        "is_default": False,
        "is_active": True,
        "config": TWO_COLUMN_SUMMARY_TEMPLATE,
    },
]

DEFAULT_THEME_ID = "corporate-navy"
DEFAULT_STYLE_ID = "comfortable"
DEFAULT_TEMPLATE_ID = "classic-linear"
