from __future__ import annotations

from copy import deepcopy

from app.presentation.validators import (
    clamp_cover_design,
    normalize_cover_geometry,
    normalize_cover_text_style,
    normalize_page,
)


def test_normalize_page_defaults_to_a4_portrait():
    assert normalize_page(None) == {"size": "A4", "orientation": "portrait"}


def test_normalize_page_accepts_supported_sizes_and_orientations():
    for size in ("A4", "A3", "Letter", "Legal"):
        assert normalize_page({"size": size, "orientation": "landscape"}) == {
            "size": size,
            "orientation": "landscape",
        }


def test_normalize_page_replaces_unsupported_values():
    assert normalize_page({"size": "Tabloid", "orientation": "square"}) == {
        "size": "A4",
        "orientation": "portrait",
    }


def test_clamp_cover_design_clamps_asset_controls_without_mutating_input():
    design = {
        "assets": [
            {
                "id": "background",
                "role": "background",
                "opacity": 1.4,
                "zoom": 8,
                "rotation": 20,
                "x": -10,
                "y": 120,
            },
            {
                "id": "logo",
                "role": "logo",
                "opacity": -0.2,
                "zoom": 0,
                "rotation": 240,
            },
            {
                "id": "decoration",
                "role": "decorative",
                "rotation": -30,
            },
        ]
    }
    original = deepcopy(design)

    result = clamp_cover_design(design)

    assert design == original
    assert result["assets"][0] == {
        "id": "background",
        "role": "background",
        "opacity": 1.0,
        "zoom": 4.0,
        "x": 0.0,
        "y": 100.0,
    }
    assert result["assets"][1]["opacity"] == 0.0
    assert result["assets"][1]["zoom"] == 0.1
    assert result["assets"][1]["rotation"] == 180.0
    assert result["assets"][2]["rotation"] == -30.0


def test_clamp_cover_design_normalizes_standalone_background():
    result = clamp_cover_design(
        {"background": {"opacity": 2, "zoom": -2, "rotation": 45}}
    )

    assert result["background"] == {"opacity": 1.0, "zoom": 0.1}


def test_clamp_cover_design_normalizes_explicit_accent_shapes():
    result = clamp_cover_design(
        {
            "accent_shapes": [
                {
                    "id": "stripe",
                    "type": "rectangle",
                    "visible": False,
                    "locked": True,
                    "geometry": {
                        "x_pct": -10,
                        "y_pct": 0,
                        "width_pct": 20,
                        "height_pct": 200,
                        "rotation_deg": -300,
                        "z_index": 1001,
                    },
                    "fill": {"mode": "custom", "color": "#123456"},
                },
                {"id": "unsafe", "type": "raw_svg"},
            ]
        }
    )

    assert len(result["accent_shapes"]) == 1
    assert result["accent_shapes"][0]["id"] == "stripe"
    assert result["accent_shapes"][0]["visible"] is False
    assert result["accent_shapes"][0]["locked"] is True
    assert result["accent_shapes"][0]["geometry"] == {
        "x_pct": 0.0,
        "y_pct": 0.0,
        "width_pct": 20.0,
        "height_pct": 100.0,
        "rotation_deg": -180.0,
        "z_index": 999,
    }


def test_clamp_cover_design_canonicalizes_invalid_accent_shape_container():
    result = clamp_cover_design({"accent_shapes": "<svg onload=alert(1)>"})

    assert result["accent_shapes"] == []


def test_clamp_cover_design_normalizes_nested_asset_geometry():
    result = clamp_cover_design(
        {
            "assets": [
                {
                    "id": "logo",
                    "role": "logo",
                    "geometry": {
                        "x_pct": 90,
                        "y_pct": 95,
                        "width_pct": 30,
                        "height_pct": 20,
                        "z_index": 4,
                    },
                },
                {
                    "id": "unsafe",
                    "role": "decorative",
                    "geometry": {"x_pct": "calc(100% - 1px)"},
                },
            ]
        }
    )

    assert result["assets"][0]["geometry"] == {
        "x_pct": 90.0,
        "y_pct": 95.0,
        "width_pct": 10.0,
        "height_pct": 5.0,
        "z_index": 4,
    }
    assert "geometry" not in result["assets"][1]


def test_clamp_cover_design_removes_unsafe_legacy_asset_css_geometry():
    result = clamp_cover_design(
        {
            "assets": [
                {
                    "id": "unsafe",
                    "role": "decorative",
                    "width_pct": "calc(100% + 1px)",
                    "height_pct": "url(https://evil.test)",
                    "z_index": "1;position:fixed",
                }
            ]
        }
    )

    assert result["assets"][0] == {
        "id": "unsafe",
        "role": "decorative",
    }


def test_normalize_cover_geometry_clamps_percentages_and_layer_order():
    assert normalize_cover_geometry(
        {
            "x_pct": -5,
            "y_pct": 120,
            "width_pct": 0,
            "height_pct": 150,
            "z_index": 1200,
            "rotation_deg": -300,
        }
    ) == {
        "x_pct": 0.0,
        "y_pct": 99.0,
        "width_pct": 1.0,
        "height_pct": 1.0,
        "z_index": 999,
        "rotation_deg": -180.0,
    }


def test_normalize_cover_geometry_clamps_size_to_remaining_page_area():
    assert normalize_cover_geometry(
        {
            "x_pct": 75,
            "y_pct": 80,
            "width_pct": 50,
            "height_pct": 50,
        }
    ) == {
        "x_pct": 75.0,
        "y_pct": 80.0,
        "width_pct": 25.0,
        "height_pct": 20.0,
        "z_index": 0,
    }


def test_normalize_cover_geometry_rejects_non_finite_and_non_mapping_values():
    assert normalize_cover_geometry(None) is None
    assert normalize_cover_geometry("positioned") is None
    assert normalize_cover_geometry({"x_pct": float("nan")}) is None
    assert normalize_cover_geometry({"width_pct": float("inf")}) is None


def test_normalize_cover_geometry_omits_optional_height():
    assert normalize_cover_geometry(
        {"x_pct": 10, "y_pct": 20, "width_pct": 30, "z_index": 4}
    ) == {
        "x_pct": 10.0,
        "y_pct": 20.0,
        "width_pct": 30.0,
        "z_index": 4,
    }


def test_normalize_cover_text_style_clamps_numeric_values_and_weight():
    assert normalize_cover_text_style(
        {
            "font_size_pt": 500,
            "font_weight": 450,
            "line_height": 0,
            "letter_spacing_em": 5,
            "opacity": -1,
            "padding_mm": 100,
        }
    ) == {
        "font_size_pt": 144.0,
        "font_weight": 400,
        "line_height": 0.5,
        "letter_spacing_em": 1.0,
        "opacity": 0.0,
        "padding_mm": 50.0,
    }


def test_normalize_cover_text_style_preserves_valid_visual_values():
    assert normalize_cover_text_style(
        {
            "font_family": "Noto Sans JP",
            "font_size_pt": 24,
            "font_weight": 700,
            "italic": True,
            "color": "#123abc",
            "text_align": "center",
            "line_height": 1.4,
            "letter_spacing_em": 0.05,
            "opacity": 0.8,
            "background_color": "#ffffff80",
            "padding_mm": 3,
        }
    ) == {
        "font_family": "Noto Sans JP",
        "font_size_pt": 24.0,
        "font_weight": 700,
        "italic": True,
        "color": "#123abc",
        "text_align": "center",
        "line_height": 1.4,
        "letter_spacing_em": 0.05,
        "opacity": 0.8,
        "background_color": "#ffffff80",
        "padding_mm": 3.0,
    }


def test_normalize_cover_text_style_preserves_partial_semantics():
    assert normalize_cover_text_style({"font_size_pt": 24}) == {
        "font_size_pt": 24.0
    }
    assert normalize_cover_text_style({}) == {}


def test_normalize_cover_text_style_removes_unsafe_css_values():
    assert normalize_cover_text_style(
        {
            "font_family": 'Arial; background: url("https://evil.test")',
            "font_size_pt": float("nan"),
            "font_weight": "bold",
            "italic": "yes",
            "color": "red; position: fixed",
            "text_align": "justify",
            "line_height": float("inf"),
            "letter_spacing_em": None,
            "opacity": "opaque",
            "background_color": "rgba(255, 255, 255, 0.5)",
            "padding_mm": -4,
        }
    ) == {
        "padding_mm": 0.0,
    }


def test_normalize_cover_text_style_accepts_only_hex_colors_and_safe_fonts():
    assert normalize_cover_text_style(
        {
            "font_family": "Arial",
            "color": "#abc",
            "background_color": "#12345678",
            "text_align": "right",
        }
    ) == {
        "font_family": "Arial",
        "color": "#abc",
        "background_color": "#12345678",
        "text_align": "right",
    }
