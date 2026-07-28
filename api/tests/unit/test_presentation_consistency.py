from __future__ import annotations

from copy import deepcopy

from app.presentation.consistency import recommend_consistency


def test_cover_title_color_outside_palette_yields_stable_theme_suggestion():
    cover_design = {"colors": {"title": "#1E3A5F"}}
    theme_draft = {
        "colors": {
            "primary": "17365D",
            "accent": "D97706",
            "surface": "FFFFFF",
        }
    }

    suggestions = recommend_consistency(
        cover_design=cover_design,
        theme_draft=theme_draft,
        style_draft={},
    )

    assert suggestions == [
        {
            "id": "theme.colors.primary",
            "target": "theme",
            "field_path": "colors.primary",
            "before": "17365D",
            "after": "1E3A5F",
            "confidence": 0.9,
            "rationale": "Cover title color is outside Theme palette",
        }
    ]


def test_matching_cover_title_color_has_no_suggestion():
    suggestions = recommend_consistency(
        cover_design={"colors": {"title": "#17365d"}},
        theme_draft={"colors": {"primary": "17365D", "accent": "D97706"}},
        style_draft={},
    )

    assert suggestions == []


def test_cover_heading_font_mismatch_yields_theme_suggestion():
    suggestions = recommend_consistency(
        cover_design={"typography": {"heading_font": "Inter"}},
        theme_draft={"fonts": {"heading": "Noto Sans JP"}},
        style_draft={},
    )

    assert suggestions == [
        {
            "id": "theme.fonts.heading",
            "target": "theme",
            "field_path": "fonts.heading",
            "before": "Noto Sans JP",
            "after": "Inter",
            "confidence": 0.9,
            "rationale": "Cover heading font differs from Theme heading font",
        }
    ]


def test_cover_padding_outside_tolerance_yields_style_suggestion():
    suggestions = recommend_consistency(
        cover_design={"padding_mm": 30},
        theme_draft={},
        style_draft={
            "margins": {
                "top_mm": 18,
                "right_mm": 16,
                "bottom_mm": 18,
                "left_mm": 16,
            }
        },
    )

    assert suggestions == [
        {
            "id": "style.margins.cover_padding",
            "target": "style",
            "field_path": "margins",
            "before": {
                "top_mm": 18,
                "right_mm": 16,
                "bottom_mm": 18,
                "left_mm": 16,
            },
            "after": {
                "top_mm": 30,
                "right_mm": 30,
                "bottom_mm": 30,
                "left_mm": 30,
            },
            "confidence": 0.8,
            "rationale": "Cover padding differs materially from Style margins",
        }
    ]


def test_recommendations_are_deterministic_and_never_mutate_drafts():
    cover_design = {
        "colors": {"title": "1E3A5F"},
        "typography": {"heading_font": "Inter"},
        "padding_mm": 30,
    }
    theme_draft = {
        "colors": {"primary": "17365D"},
        "fonts": {"heading": "Noto Sans JP"},
    }
    style_draft = {"margins": {"left_mm": 16}}
    originals = deepcopy((cover_design, theme_draft, style_draft))

    first = recommend_consistency(
        cover_design=cover_design,
        theme_draft=theme_draft,
        style_draft=style_draft,
    )
    second = recommend_consistency(
        cover_design=cover_design,
        theme_draft=theme_draft,
        style_draft=style_draft,
    )

    assert first == second
    assert (cover_design, theme_draft, style_draft) == originals
