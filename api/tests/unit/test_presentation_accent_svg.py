from __future__ import annotations

import re
from xml.etree import ElementTree

import pytest

from app.presentation.accent_shapes import (
    normalize_accent_shapes,
    render_accent_svg,
    visible_accent_shapes,
)


def _shape(identifier: str, shape_type: str = "rectangle", **overrides):
    value = {
        "id": identifier,
        "name": identifier,
        "type": shape_type,
        "visible": True,
        "locked": False,
        "geometry": {
            "x_pct": 10,
            "y_pct": 20,
            "width_pct": 30,
            "height_pct": 40,
            "rotation_deg": 0,
            "z_index": 0,
        },
        "fill": {"mode": "theme", "opacity": 0.8},
        "border": {
            "enabled": False,
            "color": "#000000",
            "width_pt": 0,
            "style": "solid",
            "radius_pct": 0,
        },
        "pattern": {
            "type": "none",
            "color": "#ffffff",
            "scale": 1,
            "spacing": 1,
            "opacity": 0.25,
        },
    }
    value.update(overrides)
    if shape_type == "line" and "line" not in value:
        value["line"] = {"thickness_pct": 4, "cap": "round"}
    if shape_type == "polygon" and "points" not in value:
        value["points"] = [
            {"x_pct": 0, "y_pct": 100},
            {"x_pct": 50, "y_pct": 0},
            {"x_pct": 100, "y_pct": 100},
        ]
    return value


def _normalized(*shapes):
    normalized, warnings = normalize_accent_shapes(list(shapes))
    assert warnings == []
    return normalized


def _local_names(svg: str) -> list[str]:
    return [element.tag.rsplit("}", 1)[-1] for element in ElementTree.fromstring(svg).iter()]


def test_render_svg_emits_every_supported_primitive():
    shapes = _normalized(
        _shape("rect", "rectangle"),
        _shape("line", "line"),
        _shape("circle", "circle"),
        _shape("ellipse", "ellipse"),
        _shape("triangle", "triangle"),
        _shape("polygon", "polygon"),
    )

    svg = render_accent_svg(
        shapes,
        theme_accent="#2563eb",
        width_mm=210,
        height_mm=297,
    )

    names = _local_names(svg)
    assert names.count("rect") == 1
    assert names.count("line") == 1
    assert names.count("circle") == 1
    assert names.count("ellipse") == 1
    assert names.count("polygon") == 2
    assert 'viewBox="0 0 210 297"' in svg


def test_render_svg_uses_theme_and_custom_colors_and_rotates_around_center():
    shapes = _normalized(
        _shape(
            "theme-shape",
            geometry={
                "x_pct": 10,
                "y_pct": 20,
                "width_pct": 30,
                "height_pct": 40,
                "rotation_deg": 30,
                "z_index": 0,
            },
        ),
        _shape(
            "custom-shape",
            fill={"mode": "custom", "color": "#123abc", "opacity": 0.5},
        ),
    )

    svg = render_accent_svg(
        shapes,
        theme_accent="#2563eb",
        width_mm=200,
        height_mm=100,
    )

    assert 'fill="#2563eb"' in svg
    assert 'fill="#123abc"' in svg
    assert 'fill-opacity="0.8"' in svg
    assert 'transform="rotate(30 50 40)"' in svg


def test_render_svg_creates_scoped_deterministic_linear_and_radial_gradients():
    shapes = _normalized(
        _shape(
            "linear-shape",
            fill={
                "mode": "linear",
                "start_color": "#112233",
                "end_color": "#abcdef",
                "angle_deg": 45,
                "opacity": 0.6,
            },
        ),
        _shape(
            "radial-shape",
            fill={
                "mode": "radial",
                "start_color": "#445566",
                "end_color": "#fedcba",
                "center_x_pct": 25,
                "center_y_pct": 75,
                "opacity": 0.7,
            },
        ),
    )

    first = render_accent_svg(
        shapes,
        theme_accent="#2563eb",
        width_mm=210,
        height_mm=297,
    )
    second = render_accent_svg(
        shapes,
        theme_accent="#2563eb",
        width_mm=210,
        height_mm=297,
    )

    assert first == second
    assert first.count("<linearGradient ") == 1
    assert first.count("<radialGradient ") == 1
    assert re.search(r'id="accent-[0-9a-f]{12}-linear-shape-linear"', first)
    assert re.search(r'id="accent-[0-9a-f]{12}-radial-shape-radial"', first)
    assert re.search(r'fill="url\(#accent-[0-9a-f]{12}-linear-shape-linear\)"', first)
    assert 'cx="25%"' in first
    assert 'cy="75%"' in first


@pytest.mark.parametrize("pattern_type", ["stripes", "dots", "grid", "diagonal_hatch"])
def test_render_svg_creates_scoped_pattern_definition(pattern_type):
    shapes = _normalized(
        _shape(
            f"{pattern_type}-shape",
            fill={"mode": "custom", "color": "#123456", "opacity": 0.9},
            pattern={
                "type": pattern_type,
                "color": "#abcdef",
                "scale": 1.5,
                "spacing": 3,
                "opacity": 0.4,
            },
        )
    )

    svg = render_accent_svg(
        shapes,
        theme_accent="#2563eb",
        width_mm=210,
        height_mm=297,
    )

    assert re.search(
        rf'id="accent-[0-9a-f]{{12}}-{pattern_type}-shape-pattern"', svg
    )
    assert re.search(
        rf'fill="url\(#accent-[0-9a-f]{{12}}-{pattern_type}-shape-pattern\)"',
        svg,
    )
    assert 'fill="#123456"' in svg
    assert 'stroke="#abcdef"' in svg or 'fill="#abcdef"' in svg
    assert 'opacity="0.4"' in svg


@pytest.mark.parametrize(
    ("style", "dasharray"),
    [("solid", None), ("dashed", "6 4"), ("dotted", "1 3")],
)
def test_render_svg_applies_border_style_and_rectangle_radius(style, dasharray):
    shapes = _normalized(
        _shape(
            "bordered",
            border={
                "enabled": True,
                "color": "#112233",
                "width_pt": 2,
                "style": style,
                "radius_pct": 25,
            },
        )
    )

    svg = render_accent_svg(
        shapes,
        theme_accent="#2563eb",
        width_mm=200,
        height_mm=100,
    )

    assert 'stroke="#112233"' in svg
    assert 'stroke-width="0.705556"' in svg
    assert 'rx="10"' in svg
    if dasharray is None:
        assert "stroke-dasharray" not in svg
    else:
        assert f'stroke-dasharray="{dasharray}"' in svg


def test_visible_accent_shapes_omits_hidden_and_render_orders_layers_by_z_index():
    hidden = _shape("hidden", visible=False)
    high = _shape(
        "high",
        name="High",
        geometry={
            "x_pct": 10,
            "y_pct": 20,
            "width_pct": 30,
            "height_pct": 40,
            "rotation_deg": 0,
            "z_index": 9,
        },
    )
    low = _shape(
        "low",
        name="Low",
        geometry={
            "x_pct": 10,
            "y_pct": 20,
            "width_pct": 30,
            "height_pct": 40,
            "rotation_deg": 0,
            "z_index": 1,
        },
    )
    shapes = _normalized(hidden, high, low)

    visible = visible_accent_shapes(shapes)
    svg = render_accent_svg(
        shapes,
        theme_accent="#2563eb",
        width_mm=210,
        height_mm=297,
    )

    assert [shape["id"] for shape in visible] == ["low", "high"]
    assert "hidden" not in svg
    assert svg.index("<title>Low</title>") < svg.index("<title>High</title>")


def test_render_svg_escapes_text_and_never_emits_raw_markup():
    shapes = _normalized(_shape("safe-id", name="Research & Development"))

    svg = render_accent_svg(
        shapes,
        theme_accent="#2563eb",
        width_mm=210,
        height_mm=297,
    )

    ElementTree.fromstring(svg)
    assert "<title>Research &amp; Development</title>" in svg
    assert "<script" not in svg.lower()
    assert "javascript:" not in svg.lower()
