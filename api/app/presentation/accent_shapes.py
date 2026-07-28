"""Validation and legacy conversion for Cover accent-shape layers."""

from __future__ import annotations

import hashlib
import json
from math import cos, isfinite, radians, sin
import re
from typing import Any
from uuid import uuid4
from xml.etree import ElementTree

SHAPE_TYPES = frozenset(
    {"rectangle", "line", "circle", "ellipse", "triangle", "polygon"}
)
FILL_MODES = frozenset({"theme", "custom", "linear", "radial"})
PATTERN_TYPES = frozenset({"none", "stripes", "dots", "grid", "diagonal_hatch"})
BORDER_STYLES = frozenset({"solid", "dashed", "dotted"})
LINE_CAPS = frozenset({"butt", "round", "square"})

PAGE_DIMENSIONS_MM: dict[str, tuple[float, float]] = {
    "A4": (210.0, 297.0),
    "A3": (297.0, 420.0),
    "Letter": (215.9, 279.4),
    "Legal": (215.9, 355.6),
}

SAFE_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")

DEFAULT_GEOMETRY = {
    "x_pct": 0.0,
    "y_pct": 0.0,
    "width_pct": 100.0,
    "height_pct": 100.0,
    "rotation_deg": 0.0,
    "z_index": 0,
}
DEFAULT_BORDER = {
    "enabled": False,
    "color": "#000000",
    "width_pt": 0.0,
    "style": "solid",
    "radius_pct": 0.0,
}
DEFAULT_PATTERN = {
    "type": "none",
    "color": "#ffffff",
    "scale": 1.0,
    "spacing": 1.0,
    "opacity": 0.25,
}


def normalize_accent_shape(
    value: Any,
    seen_ids: set[str],
) -> tuple[dict | None, list[str]]:
    """Return one canonical, markup-free shape and non-blocking warnings."""
    warnings: list[str] = []
    if not isinstance(value, dict):
        return None, ["Accent shape must be an object and was omitted"]

    shape_type = value.get("type")
    if shape_type not in SHAPE_TYPES:
        return None, ["Accent shape has an unsupported type and was omitted"]

    geometry = _normalize_geometry(value.get("geometry"))
    if geometry is None:
        return None, ["Accent shape has invalid geometry and was omitted"]

    if shape_type == "circle":
        diameter = min(geometry["width_pct"], geometry["height_pct"])
        geometry["width_pct"] = diameter
        geometry["height_pct"] = diameter

    shape_id = value.get("id")
    if (
        not isinstance(shape_id, str)
        or not SAFE_ID_RE.fullmatch(shape_id)
        or shape_id in seen_ids
    ):
        shape_id = f"accent-{uuid4()}"
        warnings.append("Accent shape ID was missing, unsafe, or duplicated and was regenerated")
    seen_ids.add(shape_id)

    name = _safe_name(value.get("name"))
    if name is None:
        name = "Accent shape"
        if value.get("name") not in (None, ""):
            warnings.append("Accent shape name contained unsafe content and was replaced")

    fill, fill_warnings = _normalize_fill(value.get("fill"))
    border, border_warnings = _normalize_border(value.get("border"))
    pattern, pattern_warnings = _normalize_pattern(value.get("pattern"))
    warnings.extend(fill_warnings)
    warnings.extend(border_warnings)
    warnings.extend(pattern_warnings)

    normalized: dict[str, Any] = {
        "id": shape_id,
        "name": name,
        "type": shape_type,
        "visible": value["visible"] if isinstance(value.get("visible"), bool) else True,
        "locked": value["locked"] if isinstance(value.get("locked"), bool) else False,
        "geometry": geometry,
        "fill": fill,
        "border": border,
        "pattern": pattern,
    }

    if shape_type == "polygon":
        points = _normalize_polygon_points(value.get("points"))
        if points is None:
            return None, warnings + [
                "Polygon must contain 3 to 12 finite points and was omitted"
            ]
        normalized["points"] = points

    if shape_type == "line":
        normalized["line"] = _normalize_line(value.get("line"))

    return normalized, warnings


def normalize_accent_shapes(values: Any) -> tuple[list[dict], list[str]]:
    """Normalize a list without imposing a hard shape-count limit."""
    if not isinstance(values, list):
        return [], ["Accent shapes must be a list; invalid value was replaced"]

    seen_ids: set[str] = set()
    shapes: list[dict] = []
    warnings: list[str] = []
    for index, value in enumerate(values):
        shape, shape_warnings = normalize_accent_shape(value, seen_ids)
        warnings.extend(f"Shape {index + 1}: {warning}" for warning in shape_warnings)
        if shape is not None:
            shapes.append(shape)

    if len(shapes) > 50:
        warnings.append("More than 50 accent shapes may reduce editing and export performance")
    return shapes, warnings


def legacy_accent_shape(design: dict, page: dict) -> dict | None:
    """Convert the historical left-edge stripe to a canonical rectangle."""
    accent = design.get("accent") if isinstance(design, dict) else None
    if not isinstance(accent, dict):
        return None
    if accent.get("enabled") is False:
        return None

    width_mm = _finite_number_or_none(
        accent.get("width_mm", accent.get("thickness_mm"))
    )
    if width_mm is None or width_mm <= 0:
        width_mm = 12.0

    page_width_mm, _ = _page_dimensions(page)
    width_pct = _clamp(width_mm / page_width_mm * 100.0, 0.1, 100.0)
    opacity = _finite_number_or_none(accent.get("opacity"))
    if opacity is None:
        opacity = 0.9

    return {
        "id": "legacy-accent",
        "name": "Left stripe",
        "type": "rectangle",
        "visible": True,
        "locked": False,
        "geometry": {
            "x_pct": 0.0,
            "y_pct": 0.0,
            "width_pct": width_pct,
            "height_pct": 100.0,
            "rotation_deg": 0.0,
            "z_index": 1,
        },
        "fill": {"mode": "theme", "opacity": _clamp(opacity, 0.0, 1.0)},
        "border": dict(DEFAULT_BORDER),
        "pattern": dict(DEFAULT_PATTERN),
    }


def resolve_accent_shapes(
    design: dict,
    page: dict,
) -> tuple[list[dict], list[str]]:
    """Prefer canonical shapes, converting legacy accent data only when absent."""
    source = design if isinstance(design, dict) else {}
    if "accent_shapes" in source:
        return normalize_accent_shapes(source.get("accent_shapes"))

    legacy_shape = legacy_accent_shape(source, page)
    if legacy_shape is None:
        return [], []
    return [legacy_shape], []


def visible_accent_shapes(shapes: list[dict]) -> list[dict]:
    """Return visible normalized shapes in stable back-to-front layer order."""
    indexed_shapes = [
        (index, shape)
        for index, shape in enumerate(shapes)
        if isinstance(shape, dict) and shape.get("visible") is not False
    ]
    indexed_shapes.sort(key=lambda item: (_shape_z_index(item[1]), item[0]))
    return [shape for _, shape in indexed_shapes]


def render_accent_svg(
    shapes: list[dict],
    *,
    theme_accent: str,
    width_mm: float,
    height_mm: float,
) -> str:
    """Render normalized accent shapes as deterministic, markup-free SVG."""
    width = _positive_finite_number(width_mm)
    height = _positive_finite_number(height_mm)
    if width is None or height is None:
        return ""

    accent = _safe_color(theme_accent) or "#000000"
    ordered_shapes = visible_accent_shapes(shapes)
    renderable_shapes = [
        shape for shape in ordered_shapes if _is_renderable_shape(shape)
    ]
    if not renderable_shapes:
        return ""

    digest_source = json.dumps(
        {
            "height": height,
            "shapes": renderable_shapes,
            "theme_accent": accent,
            "width": width,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    scope = f"accent-{hashlib.sha256(digest_source.encode('utf-8')).hexdigest()[:12]}"

    root = ElementTree.Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "viewBox": f"0 0 {_format_number(width)} {_format_number(height)}",
            "width": f"{_format_number(width)}mm",
            "height": f"{_format_number(height)}mm",
            "preserveAspectRatio": "none",
        },
    )
    definitions = ElementTree.Element("defs")

    for shape in renderable_shapes:
        _render_shape(
            root,
            definitions,
            shape,
            scope=scope,
            theme_accent=accent,
            page_width=width,
            page_height=height,
        )

    if len(definitions):
        root.insert(0, definitions)
    return ElementTree.tostring(root, encoding="unicode", short_empty_elements=True)


def _render_shape(
    root: ElementTree.Element,
    definitions: ElementTree.Element,
    shape: dict,
    *,
    scope: str,
    theme_accent: str,
    page_width: float,
    page_height: float,
) -> None:
    geometry = shape["geometry"]
    x = page_width * geometry["x_pct"] / 100.0
    y = page_height * geometry["y_pct"] / 100.0
    width = page_width * geometry["width_pct"] / 100.0
    height = page_height * geometry["height_pct"] / 100.0
    center_x = x + width / 2.0
    center_y = y + height / 2.0

    group_attributes = {"data-accent-id": shape["id"]}
    rotation = geometry["rotation_deg"]
    if rotation:
        group_attributes["transform"] = (
            f"rotate({_format_number(rotation)} "
            f"{_format_number(center_x)} {_format_number(center_y)})"
        )
    group = ElementTree.SubElement(root, "g", group_attributes)
    ElementTree.SubElement(group, "title").text = shape["name"]

    paint = _shape_paint(
        definitions,
        shape,
        scope=scope,
        theme_accent=theme_accent,
    )
    primitive_attributes = _primitive_attributes(
        shape,
        x=x,
        y=y,
        width=width,
        height=height,
    )
    shape_type = shape["type"]

    if shape_type == "line":
        line_width = height * shape["line"]["thickness_pct"] / 100.0
        border = shape["border"]
        if border["enabled"] and border["width_pt"] > 0:
            border_width = border["width_pt"] * 25.4 / 72.0
            border_attributes = {
                **primitive_attributes,
                "fill": "none",
                "stroke": border["color"],
                "stroke-width": _format_number(line_width + 2.0 * border_width),
                "stroke-linecap": shape["line"]["cap"],
            }
            _add_dash_style(border_attributes, border["style"])
            ElementTree.SubElement(group, "line", border_attributes)
        primitive_attributes.update(
            {
                "fill": "none",
                "stroke": paint,
                "stroke-width": _format_number(line_width),
                "stroke-linecap": shape["line"]["cap"],
                "stroke-opacity": _format_number(shape["fill"]["opacity"]),
            }
        )
    else:
        primitive_attributes["fill"] = paint
        primitive_attributes["fill-opacity"] = _format_number(shape["fill"]["opacity"])
        _add_border_attributes(primitive_attributes, shape["border"])

    ElementTree.SubElement(group, _primitive_tag(shape_type), primitive_attributes)


def _shape_paint(
    definitions: ElementTree.Element,
    shape: dict,
    *,
    scope: str,
    theme_accent: str,
) -> str:
    fill = shape["fill"]
    mode = fill["mode"]
    if mode == "theme":
        paint = theme_accent
    elif mode == "custom":
        paint = fill["color"]
    elif mode == "linear":
        definition_id = f"{scope}-{shape['id']}-linear"
        angle = radians(fill["angle_deg"])
        x_offset = 50.0 * cos(angle)
        y_offset = 50.0 * sin(angle)
        gradient = ElementTree.SubElement(
            definitions,
            "linearGradient",
            {
                "id": definition_id,
                "x1": f"{_format_number(50.0 - x_offset)}%",
                "y1": f"{_format_number(50.0 - y_offset)}%",
                "x2": f"{_format_number(50.0 + x_offset)}%",
                "y2": f"{_format_number(50.0 + y_offset)}%",
            },
        )
        ElementTree.SubElement(
            gradient, "stop", {"offset": "0%", "stop-color": fill["start_color"]}
        )
        ElementTree.SubElement(
            gradient, "stop", {"offset": "100%", "stop-color": fill["end_color"]}
        )
        paint = f"url(#{definition_id})"
    else:
        definition_id = f"{scope}-{shape['id']}-radial"
        gradient = ElementTree.SubElement(
            definitions,
            "radialGradient",
            {
                "id": definition_id,
                "cx": f"{_format_number(fill['center_x_pct'])}%",
                "cy": f"{_format_number(fill['center_y_pct'])}%",
                "r": "70.710678%",
            },
        )
        ElementTree.SubElement(
            gradient, "stop", {"offset": "0%", "stop-color": fill["start_color"]}
        )
        ElementTree.SubElement(
            gradient, "stop", {"offset": "100%", "stop-color": fill["end_color"]}
        )
        paint = f"url(#{definition_id})"

    pattern = shape["pattern"]
    if pattern["type"] == "none":
        return paint
    return _add_pattern_definition(
        definitions,
        shape,
        scope=scope,
        background_paint=paint,
    )


def _add_pattern_definition(
    definitions: ElementTree.Element,
    shape: dict,
    *,
    scope: str,
    background_paint: str,
) -> str:
    pattern = shape["pattern"]
    definition_id = f"{scope}-{shape['id']}-pattern"
    tile_size = pattern["scale"] * pattern["spacing"]
    tile = _format_number(tile_size)
    element = ElementTree.SubElement(
        definitions,
        "pattern",
        {
            "id": definition_id,
            "patternUnits": "userSpaceOnUse",
            "width": tile,
            "height": tile,
        },
    )
    ElementTree.SubElement(
        element,
        "rect",
        {"width": tile, "height": tile, "fill": background_paint},
    )
    decoration_attributes = {
        "stroke": pattern["color"],
        "stroke-width": _format_number(max(0.1, pattern["scale"] * 0.25)),
        "opacity": _format_number(pattern["opacity"]),
        "fill": "none",
    }
    pattern_type = pattern["type"]
    if pattern_type == "dots":
        ElementTree.SubElement(
            element,
            "circle",
            {
                "cx": _format_number(tile_size / 2.0),
                "cy": _format_number(tile_size / 2.0),
                "r": _format_number(max(0.1, pattern["scale"] * 0.35)),
                "fill": pattern["color"],
                "opacity": _format_number(pattern["opacity"]),
            },
        )
    elif pattern_type == "grid":
        decoration_attributes["d"] = f"M 0 0 H {tile} M 0 0 V {tile}"
        ElementTree.SubElement(element, "path", decoration_attributes)
    elif pattern_type == "diagonal_hatch":
        decoration_attributes["d"] = (
            f"M 0 {tile} L {tile} 0 M {_format_number(-tile_size)} {tile} L 0 0 "
            f"M {tile} {tile} L {_format_number(tile_size * 2.0)} 0"
        )
        ElementTree.SubElement(element, "path", decoration_attributes)
    else:
        decoration_attributes["d"] = (
            f"M 0 0 V {tile} M {_format_number(tile_size / 2.0)} 0 V {tile}"
        )
        ElementTree.SubElement(element, "path", decoration_attributes)
    return f"url(#{definition_id})"


def _primitive_attributes(
    shape: dict,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
) -> dict[str, str]:
    shape_type = shape["type"]
    if shape_type == "rectangle":
        attributes = {
            "x": _format_number(x),
            "y": _format_number(y),
            "width": _format_number(width),
            "height": _format_number(height),
        }
        radius = min(width, height) * shape["border"]["radius_pct"] / 100.0
        if radius:
            attributes["rx"] = _format_number(radius)
        return attributes
    if shape_type == "line":
        center_y = y + height / 2.0
        return {
            "x1": _format_number(x),
            "y1": _format_number(center_y),
            "x2": _format_number(x + width),
            "y2": _format_number(center_y),
        }
    if shape_type == "circle":
        radius = min(width, height) / 2.0
        return {
            "cx": _format_number(x + width / 2.0),
            "cy": _format_number(y + height / 2.0),
            "r": _format_number(radius),
        }
    if shape_type == "ellipse":
        return {
            "cx": _format_number(x + width / 2.0),
            "cy": _format_number(y + height / 2.0),
            "rx": _format_number(width / 2.0),
            "ry": _format_number(height / 2.0),
        }
    if shape_type == "triangle":
        return {
            "points": " ".join(
                (
                    f"{_format_number(x + width / 2.0)},{_format_number(y)}",
                    f"{_format_number(x + width)},{_format_number(y + height)}",
                    f"{_format_number(x)},{_format_number(y + height)}",
                )
            )
        }
    return {
        "points": " ".join(
            f"{_format_number(x + width * point['x_pct'] / 100.0)},"
            f"{_format_number(y + height * point['y_pct'] / 100.0)}"
            for point in shape["points"]
        )
    }


def _primitive_tag(shape_type: str) -> str:
    if shape_type == "rectangle":
        return "rect"
    if shape_type in {"triangle", "polygon"}:
        return "polygon"
    return shape_type


def _add_border_attributes(attributes: dict[str, str], border: dict) -> None:
    if not border["enabled"] or border["width_pt"] <= 0:
        return
    attributes["stroke"] = border["color"]
    attributes["stroke-width"] = _format_number(border["width_pt"] * 25.4 / 72.0)
    _add_dash_style(attributes, border["style"])


def _add_dash_style(attributes: dict[str, str], style: str) -> None:
    if style == "dashed":
        attributes["stroke-dasharray"] = "6 4"
    elif style == "dotted":
        attributes["stroke-dasharray"] = "1 3"
        attributes["stroke-linecap"] = "round"


def _is_renderable_shape(shape: dict) -> bool:
    if shape.get("type") not in SHAPE_TYPES:
        return False
    if not isinstance(shape.get("id"), str) or not SAFE_ID_RE.fullmatch(shape["id"]):
        return False
    if not isinstance(shape.get("name"), str):
        return False
    geometry = shape.get("geometry")
    if not isinstance(geometry, dict):
        return False
    required_geometry = (
        "x_pct",
        "y_pct",
        "width_pct",
        "height_pct",
        "rotation_deg",
        "z_index",
    )
    if any(_finite_number_or_none(geometry.get(key)) is None for key in required_geometry):
        return False
    fill = shape.get("fill")
    border = shape.get("border")
    pattern = shape.get("pattern")
    if not isinstance(fill, dict) or fill.get("mode") not in FILL_MODES:
        return False
    if not isinstance(border, dict) or not isinstance(pattern, dict):
        return False
    if shape["type"] == "line" and not isinstance(shape.get("line"), dict):
        return False
    if shape["type"] == "polygon" and not isinstance(shape.get("points"), list):
        return False
    return True


def _shape_z_index(shape: dict) -> int:
    geometry = shape.get("geometry")
    if not isinstance(geometry, dict):
        return 0
    value = _finite_number_or_none(geometry.get("z_index"))
    return int(value) if value is not None else 0


def _positive_finite_number(value: Any) -> float | None:
    number = _finite_number_or_none(value)
    if number is None or number <= 0:
        return None
    return number


def _format_number(value: float) -> str:
    if abs(value) < 0.0000005:
        return "0"
    return f"{value:.6f}".rstrip("0").rstrip(".")


def _normalize_geometry(value: Any) -> dict[str, Any] | None:
    source = value if isinstance(value, dict) else {}
    numbers: dict[str, float] = {}
    for key, default in DEFAULT_GEOMETRY.items():
        number = _finite_number_or_none(source.get(key, default))
        if number is None:
            return None
        numbers[key] = number

    x_pct = _clamp(numbers["x_pct"], 0.0, 99.9)
    y_pct = _clamp(numbers["y_pct"], 0.0, 99.9)
    return {
        "x_pct": x_pct,
        "y_pct": y_pct,
        "width_pct": _clamp(numbers["width_pct"], 0.1, 100.0 - x_pct),
        "height_pct": _clamp(numbers["height_pct"], 0.1, 100.0 - y_pct),
        "rotation_deg": _clamp(numbers["rotation_deg"], -180.0, 180.0),
        "z_index": int(_clamp(numbers["z_index"], 0.0, 999.0)),
    }


def _normalize_fill(value: Any) -> tuple[dict[str, Any], list[str]]:
    source = value if isinstance(value, dict) else {}
    warnings: list[str] = []
    mode = source.get("mode", "theme")
    if mode not in FILL_MODES:
        mode = "theme"
        warnings.append("Unsupported fill mode was replaced with Theme accent")

    opacity = _bounded_number(source.get("opacity"), 1.0, 0.0, 1.0)
    if mode == "theme":
        return {"mode": "theme", "opacity": opacity}, warnings

    if mode == "custom":
        color = _safe_color(source.get("color"))
        if color is None:
            warnings.append("Unsafe custom fill color was replaced with Theme accent")
            return {"mode": "theme", "opacity": opacity}, warnings
        return {"mode": "custom", "color": color, "opacity": opacity}, warnings

    start_color = _safe_color(source.get("start_color"))
    end_color = _safe_color(source.get("end_color"))
    if start_color is None or end_color is None:
        warnings.append("Unsafe gradient colors were replaced with Theme accent")
        return {"mode": "theme", "opacity": opacity}, warnings

    normalized: dict[str, Any] = {
        "mode": mode,
        "start_color": start_color,
        "end_color": end_color,
        "opacity": opacity,
    }
    if mode == "linear":
        normalized["angle_deg"] = _bounded_number(
            source.get("angle_deg"), 0.0, -180.0, 180.0
        )
    else:
        normalized["center_x_pct"] = _bounded_number(
            source.get("center_x_pct"), 50.0, 0.0, 100.0
        )
        normalized["center_y_pct"] = _bounded_number(
            source.get("center_y_pct"), 50.0, 0.0, 100.0
        )
    return normalized, warnings


def _normalize_border(value: Any) -> tuple[dict[str, Any], list[str]]:
    source = value if isinstance(value, dict) else {}
    warnings: list[str] = []
    style = source.get("style", DEFAULT_BORDER["style"])
    if style not in BORDER_STYLES:
        style = DEFAULT_BORDER["style"]
        warnings.append("Unsupported border style was replaced")
    color = _safe_color(source.get("color", DEFAULT_BORDER["color"]))
    if color is None:
        color = DEFAULT_BORDER["color"]
        warnings.append("Unsafe border color was replaced")
    return {
        "enabled": source["enabled"]
        if isinstance(source.get("enabled"), bool)
        else DEFAULT_BORDER["enabled"],
        "color": color,
        "width_pt": _bounded_number(source.get("width_pt"), 0.0, 0.0, 72.0),
        "style": style,
        "radius_pct": _bounded_number(
            source.get("radius_pct"), 0.0, 0.0, 50.0
        ),
    }, warnings


def _normalize_pattern(value: Any) -> tuple[dict[str, Any], list[str]]:
    source = value if isinstance(value, dict) else {}
    warnings: list[str] = []
    pattern_type = source.get("type", DEFAULT_PATTERN["type"])
    if pattern_type not in PATTERN_TYPES:
        pattern_type = DEFAULT_PATTERN["type"]
        warnings.append("Unsupported pattern type was replaced")
    color = _safe_color(source.get("color", DEFAULT_PATTERN["color"]))
    if color is None:
        color = DEFAULT_PATTERN["color"]
        warnings.append("Unsafe pattern color was replaced")
    return {
        "type": pattern_type,
        "color": color,
        "scale": _bounded_number(source.get("scale"), 1.0, 0.1, 10.0),
        "spacing": _bounded_number(source.get("spacing"), 1.0, 0.1, 100.0),
        "opacity": _bounded_number(source.get("opacity"), 0.25, 0.0, 1.0),
    }, warnings


def _normalize_line(value: Any) -> dict[str, Any]:
    source = value if isinstance(value, dict) else {}
    cap = source.get("cap", "butt")
    if cap not in LINE_CAPS:
        cap = "butt"
    return {
        "thickness_pct": _bounded_number(
            source.get("thickness_pct"), 1.0, 0.1, 100.0
        ),
        "cap": cap,
    }


def _normalize_polygon_points(value: Any) -> list[dict[str, float]] | None:
    if not isinstance(value, list) or not 3 <= len(value) <= 12:
        return None
    points: list[dict[str, float]] = []
    for point in value:
        if isinstance(point, dict):
            x_value = point.get("x_pct")
            y_value = point.get("y_pct")
        elif isinstance(point, (list, tuple)) and len(point) == 2:
            x_value, y_value = point
        else:
            return None
        x_pct = _finite_number_or_none(x_value)
        y_pct = _finite_number_or_none(y_value)
        if x_pct is None or y_pct is None:
            return None
        points.append(
            {
                "x_pct": _clamp(x_pct, 0.0, 100.0),
                "y_pct": _clamp(y_pct, 0.0, 100.0),
            }
        )
    return points


def _safe_name(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    name = value.strip()
    if not name or len(name) > 100:
        return None
    lowered = name.lower()
    if any(token in lowered for token in ("<", ">", "url(", "javascript:", "{", "}")):
        return None
    if any(ord(character) < 32 for character in name):
        return None
    return name


def _safe_color(value: Any) -> str | None:
    return value if isinstance(value, str) and HEX_COLOR_RE.fullmatch(value) else None


def _page_dimensions(page: Any) -> tuple[float, float]:
    source = page if isinstance(page, dict) else {}
    dimensions = PAGE_DIMENSIONS_MM.get(str(source.get("size")), PAGE_DIMENSIONS_MM["A4"])
    if source.get("orientation") == "landscape":
        return dimensions[1], dimensions[0]
    return dimensions


def _bounded_number(value: Any, default: float, minimum: float, maximum: float) -> float:
    number = _finite_number_or_none(value)
    return _clamp(default if number is None else number, minimum, maximum)


def _finite_number_or_none(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
