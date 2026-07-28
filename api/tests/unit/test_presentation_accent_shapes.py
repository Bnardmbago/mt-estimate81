from __future__ import annotations

import math

import pytest

from app.presentation.accent_shapes import (
    BORDER_STYLES,
    FILL_MODES,
    PATTERN_TYPES,
    SHAPE_TYPES,
    legacy_accent_shape,
    normalize_accent_shape,
    normalize_accent_shapes,
    resolve_accent_shapes,
)


def _shape(**overrides):
    value = {
        "id": "shape-1",
        "name": "Accent",
        "type": "rectangle",
        "visible": True,
        "locked": False,
        "geometry": {
            "x_pct": 10,
            "y_pct": 20,
            "width_pct": 30,
            "height_pct": 40,
            "rotation_deg": 15,
            "z_index": 2,
        },
        "fill": {"mode": "theme", "opacity": 0.8},
    }
    value.update(overrides)
    return value


def test_normalize_accent_shape_rejects_raw_markup_and_clamps_values():
    shape, warnings = normalize_accent_shape(
        {
            "id": "shape-1",
            "name": "<script>alert(1)</script>",
            "type": "rectangle",
            "geometry": {
                "x_pct": -4,
                "y_pct": 90,
                "width_pct": 30,
                "height_pct": 30,
                "rotation_deg": 999,
                "z_index": 2000,
            },
            "fill": {
                "mode": "custom",
                "color": "url(https://invalid)",
                "opacity": 2,
                "onload": "alert(1)",
            },
            "raw_svg": "<script>alert(1)</script>",
        },
        set(),
    )

    assert shape is not None
    assert shape["geometry"] == {
        "x_pct": 0.0,
        "y_pct": 90.0,
        "width_pct": 30.0,
        "height_pct": 10.0,
        "rotation_deg": 180.0,
        "z_index": 999,
    }
    assert shape["fill"]["mode"] == "theme"
    assert shape["fill"]["opacity"] == 1.0
    assert shape["name"] == "Accent shape"
    assert "raw_svg" not in shape
    assert "onload" not in shape["fill"]
    assert warnings


@pytest.mark.parametrize("shape_type", sorted(SHAPE_TYPES))
def test_normalize_accent_shape_accepts_every_shape_type(shape_type):
    value = _shape(type=shape_type)
    if shape_type == "polygon":
        value["points"] = [
            {"x_pct": 0, "y_pct": 0},
            {"x_pct": 100, "y_pct": 0},
            {"x_pct": 50, "y_pct": 100},
        ]
    if shape_type == "line":
        value["line"] = {"thickness_pct": 4, "cap": "round"}

    shape, warnings = normalize_accent_shape(value, set())

    assert shape is not None
    assert shape["type"] == shape_type
    assert not warnings


def test_normalize_accent_shape_rejects_unsupported_type_and_non_finite_geometry():
    unsupported, unsupported_warnings = normalize_accent_shape(
        _shape(type="path"), set()
    )
    non_finite, non_finite_warnings = normalize_accent_shape(
        _shape(geometry={"x_pct": math.nan}), set()
    )

    assert unsupported is None
    assert non_finite is None
    assert unsupported_warnings
    assert non_finite_warnings


@pytest.mark.parametrize("mode", sorted(FILL_MODES))
def test_normalize_accent_shape_accepts_every_fill_mode(mode):
    fill = {"mode": mode, "opacity": 0.6}
    if mode == "custom":
        fill["color"] = "#123abc"
    elif mode == "linear":
        fill.update(
            {
                "start_color": "#112233",
                "end_color": "#abcdef",
                "angle_deg": 400,
            }
        )
    elif mode == "radial":
        fill.update(
            {
                "start_color": "#112233",
                "end_color": "#abcdef",
                "center_x_pct": -2,
                "center_y_pct": 120,
            }
        )

    shape, warnings = normalize_accent_shape(_shape(fill=fill), set())

    assert shape is not None
    assert shape["fill"]["mode"] == mode
    if mode == "linear":
        assert shape["fill"]["angle_deg"] == 180.0
    if mode == "radial":
        assert shape["fill"]["center_x_pct"] == 0.0
        assert shape["fill"]["center_y_pct"] == 100.0
    assert not warnings


@pytest.mark.parametrize("pattern_type", sorted(PATTERN_TYPES))
def test_normalize_accent_shape_accepts_every_pattern(pattern_type):
    shape, warnings = normalize_accent_shape(
        _shape(
            pattern={
                "type": pattern_type,
                "color": "#fff",
                "scale": 0,
                "spacing": 500,
                "opacity": -1,
            }
        ),
        set(),
    )

    assert shape is not None
    assert shape["pattern"] == {
        "type": pattern_type,
        "color": "#fff",
        "scale": 0.1,
        "spacing": 100.0,
        "opacity": 0.0,
    }
    assert not warnings


@pytest.mark.parametrize("border_style", sorted(BORDER_STYLES))
def test_normalize_accent_shape_accepts_every_border_style(border_style):
    shape, warnings = normalize_accent_shape(
        _shape(
            border={
                "enabled": True,
                "color": "#12345678",
                "width_pt": 1000,
                "style": border_style,
                "radius_pct": 80,
            }
        ),
        set(),
    )

    assert shape is not None
    assert shape["border"] == {
        "enabled": True,
        "color": "#12345678",
        "width_pt": 72.0,
        "style": border_style,
        "radius_pct": 50.0,
    }
    assert not warnings


def test_normalize_accent_shapes_regenerates_duplicate_and_unsafe_ids():
    shapes, warnings = normalize_accent_shapes(
        [
            _shape(id="same"),
            _shape(id="same"),
            _shape(id='"><script>'),
            _shape(id=None),
        ]
    )

    ids = [shape["id"] for shape in shapes]
    assert len(ids) == len(set(ids)) == 4
    assert ids[0] == "same"
    assert all(identifier.startswith("accent-") for identifier in ids[1:])
    assert warnings


def test_normalize_accent_shape_preserves_hidden_and_locked_for_storage():
    shape, warnings = normalize_accent_shape(
        _shape(visible=False, locked=True), set()
    )

    assert shape is not None
    assert shape["visible"] is False
    assert shape["locked"] is True
    assert not warnings


@pytest.mark.parametrize("count", [2, 13])
def test_normalize_accent_shape_rejects_polygon_outside_vertex_limits(count):
    shape, warnings = normalize_accent_shape(
        _shape(
            type="polygon",
            points=[
                {"x_pct": index * 10, "y_pct": index * 5}
                for index in range(count)
            ],
        ),
        set(),
    )

    assert shape is None
    assert warnings


def test_normalize_accent_shape_clamps_polygon_points_and_rejects_bad_points():
    shape, warnings = normalize_accent_shape(
        _shape(
            type="polygon",
            points=[
                {"x_pct": -1, "y_pct": 101},
                [50, 0],
                {"x_pct": 100, "y_pct": 100},
            ],
        ),
        set(),
    )
    bad_shape, bad_warnings = normalize_accent_shape(
        _shape(
            type="polygon",
            points=[
                {"x_pct": 0, "y_pct": 0},
                {"x_pct": float("inf"), "y_pct": 0},
                {"x_pct": 100, "y_pct": 100},
            ],
        ),
        set(),
    )

    assert shape is not None
    assert shape["points"] == [
        {"x_pct": 0.0, "y_pct": 100.0},
        {"x_pct": 50.0, "y_pct": 0.0},
        {"x_pct": 100.0, "y_pct": 100.0},
    ]
    assert not warnings
    assert bad_shape is None
    assert bad_warnings


@pytest.mark.parametrize(
    ("page", "thickness_key", "thickness", "expected"),
    [
        ({"size": "A4", "orientation": "portrait"}, "width_mm", 21, 10.0),
        ({"size": "A4", "orientation": "landscape"}, "thickness_mm", 29.7, 10.0),
        ({"size": "A3", "orientation": "portrait"}, "width_mm", 29.7, 10.0),
        ({"size": "Letter", "orientation": "portrait"}, "width_mm", 21.59, 10.0),
        ({"size": "Legal", "orientation": "portrait"}, "width_mm", 21.59, 10.0),
    ],
)
def test_legacy_accent_width_uses_page_dimensions(
    page, thickness_key, thickness, expected
):
    shape = legacy_accent_shape(
        {"accent": {"enabled": True, thickness_key: thickness, "opacity": 0.8}},
        page,
    )

    assert shape is not None
    assert shape["type"] == "rectangle"
    assert shape["geometry"]["width_pct"] == pytest.approx(expected)
    assert shape["geometry"]["height_pct"] == 100.0
    assert shape["fill"] == {"mode": "theme", "opacity": 0.8}


def test_legacy_accent_disabled_returns_none_and_invalid_values_fall_back():
    assert (
        legacy_accent_shape(
            {"accent": {"enabled": False, "width_mm": 21}},
            {"size": "A4", "orientation": "portrait"},
        )
        is None
    )

    shape = legacy_accent_shape(
        {"accent": {"enabled": True, "width_mm": "url(evil)", "opacity": math.nan}},
        {"size": "A4", "orientation": "portrait"},
    )
    assert shape is not None
    assert shape["geometry"]["width_pct"] > 0
    assert shape["fill"]["opacity"] == 0.9


def test_resolve_accent_shapes_prefers_explicit_canonical_key_even_when_empty():
    legacy = {"accent": {"enabled": True, "width_mm": 21}}

    shapes, warnings = resolve_accent_shapes(
        {**legacy, "accent_shapes": []},
        {"size": "A4", "orientation": "portrait"},
    )

    assert shapes == []
    assert warnings == []


def test_resolve_accent_shapes_converts_legacy_and_warns_after_fifty_shapes():
    legacy_shapes, legacy_warnings = resolve_accent_shapes(
        {"accent": {"enabled": True, "width_mm": 21}},
        {"size": "A4", "orientation": "portrait"},
    )
    many_shapes, many_warnings = resolve_accent_shapes(
        {"accent_shapes": [_shape(id=f"shape-{index}") for index in range(51)]},
        {"size": "A4", "orientation": "portrait"},
    )

    assert len(legacy_shapes) == 1
    assert not legacy_warnings
    assert len(many_shapes) == 51
    assert any("50" in warning for warning in many_warnings)
