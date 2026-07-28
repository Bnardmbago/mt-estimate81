"""Pure normalization helpers for presentation configuration."""

from __future__ import annotations

from copy import deepcopy
from math import isfinite
import re
from typing import Any

from app.presentation.accent_shapes import normalize_accent_shapes

DEFAULT_PAGE = {"size": "A4", "orientation": "portrait"}
SUPPORTED_PAGE_SIZES = ("A4", "A3", "Letter", "Legal")
SUPPORTED_ORIENTATIONS = ("portrait", "landscape")

MIN_ZOOM = 0.1
MAX_ZOOM = 4.0
MIN_ROTATION = -180.0
MAX_ROTATION = 180.0

MIN_COVER_FONT_SIZE_PT = 6.0
MAX_COVER_FONT_SIZE_PT = 144.0
MIN_COVER_LINE_HEIGHT = 0.5
MAX_COVER_LINE_HEIGHT = 3.0
MIN_COVER_LETTER_SPACING_EM = -0.2
MAX_COVER_LETTER_SPACING_EM = 1.0
MAX_COVER_PADDING_MM = 50.0
COVER_FONT_WEIGHTS = (300, 400, 500, 600, 700, 800, 900)
COVER_TEXT_ALIGNMENTS = ("left", "center", "right")
SAFE_COVER_FONT_FAMILIES = frozenset(
    {
        "Arial",
        "Helvetica",
        "Helvetica Neue",
        "Hiragino Kaku Gothic ProN",
        "Noto Sans JP",
        "Yu Gothic",
        "monospace",
        "sans-serif",
        "serif",
    }
)
HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


def normalize_page(page: dict[str, Any] | None) -> dict[str, str]:
    """Return a supported page setup, defaulting invalid values independently."""
    source = page if isinstance(page, dict) else {}

    size_lookup = {size.lower(): size for size in SUPPORTED_PAGE_SIZES}
    raw_size = source.get("size")
    size = size_lookup.get(str(raw_size).strip().lower(), DEFAULT_PAGE["size"])

    raw_orientation = source.get("orientation")
    orientation = str(raw_orientation).strip().lower()
    if orientation not in SUPPORTED_ORIENTATIONS:
        orientation = DEFAULT_PAGE["orientation"]

    return {"size": size, "orientation": orientation}


def normalize_cover_geometry(value: Any) -> dict[str, Any] | None:
    """Return finite, page-safe Cover geometry or None for invalid input."""
    if not isinstance(value, dict):
        return None

    defaults = {
        "x_pct": 0.0,
        "y_pct": 0.0,
        "width_pct": 100.0,
        "z_index": 0.0,
    }
    numbers: dict[str, float] = {}
    for key, default in defaults.items():
        number = _optional_finite_number(value, key, default)
        if number is None:
            return None
        numbers[key] = number

    x_pct = _clamp(numbers["x_pct"], 0.0, 99.0)
    y_pct = _clamp(numbers["y_pct"], 0.0, 99.0)
    normalized: dict[str, Any] = {
        "x_pct": x_pct,
        "y_pct": y_pct,
        "width_pct": _clamp(numbers["width_pct"], 1.0, 100.0 - x_pct),
        "z_index": int(_clamp(numbers["z_index"], 0.0, 999.0)),
    }

    if "height_pct" in value:
        height = _optional_finite_number(value, "height_pct", 1.0)
        if height is None:
            return None
        normalized["height_pct"] = _clamp(height, 1.0, 100.0 - y_pct)

    if "rotation_deg" in value:
        rotation = _optional_finite_number(value, "rotation_deg", 0.0)
        if rotation is None:
            return None
        normalized["rotation_deg"] = _clamp(rotation, MIN_ROTATION, MAX_ROTATION)

    return normalized


def normalize_cover_text_style(value: Any) -> dict[str, Any]:
    """Normalize only explicitly supplied, export-safe Cover text styling."""
    source = value if isinstance(value, dict) else {}
    normalized: dict[str, Any] = {}

    numeric_ranges = {
        "font_size_pt": (MIN_COVER_FONT_SIZE_PT, MAX_COVER_FONT_SIZE_PT),
        "line_height": (MIN_COVER_LINE_HEIGHT, MAX_COVER_LINE_HEIGHT),
        "letter_spacing_em": (
            MIN_COVER_LETTER_SPACING_EM,
            MAX_COVER_LETTER_SPACING_EM,
        ),
        "opacity": (0.0, 1.0),
        "padding_mm": (0.0, MAX_COVER_PADDING_MM),
    }
    for key, (minimum, maximum) in numeric_ranges.items():
        if key not in source:
            continue
        number = _finite_number_or_none(source[key])
        if number is not None:
            normalized[key] = _clamp(number, minimum, maximum)

    if "font_weight" in source:
        raw_weight = _finite_number_or_none(source["font_weight"])
        if raw_weight is not None:
            normalized["font_weight"] = min(
                COVER_FONT_WEIGHTS,
                key=lambda weight: (abs(weight - raw_weight), weight),
            )

    font_family = _nonempty_string(source.get("font_family"))
    if font_family in SAFE_COVER_FONT_FAMILIES:
        normalized["font_family"] = font_family

    if isinstance(source.get("italic"), bool):
        normalized["italic"] = source["italic"]

    for key in ("color", "background_color"):
        color = _nonempty_string(source.get(key))
        if color is not None and HEX_COLOR_RE.fullmatch(color):
            normalized[key] = color

    text_align = _nonempty_string(source.get("text_align"))
    if text_align is not None:
        text_align = text_align.lower()
        if text_align in COVER_TEXT_ALIGNMENTS:
            normalized["text_align"] = text_align

    return normalized


def clamp_cover_design(design: dict[str, Any] | None) -> dict[str, Any]:
    """Copy and clamp cover image controls to export-safe ranges."""
    normalized = deepcopy(design) if isinstance(design, dict) else {}

    background = normalized.get("background")
    if isinstance(background, dict):
        normalized["background"] = _clamp_asset(background, role="background")

    assets = normalized.get("assets")
    if isinstance(assets, list):
        normalized["assets"] = [
            _clamp_asset(asset, role=asset.get("role"))
            for asset in assets
            if isinstance(asset, dict)
        ]

    if "accent_shapes" in normalized:
        accent_shapes, _ = normalize_accent_shapes(normalized["accent_shapes"])
        normalized["accent_shapes"] = accent_shapes

    return normalized


def _clamp_asset(asset: dict[str, Any], *, role: Any) -> dict[str, Any]:
    normalized = deepcopy(asset)

    if "geometry" in normalized:
        geometry = normalize_cover_geometry(normalized["geometry"])
        if geometry is None:
            normalized.pop("geometry", None)
        else:
            normalized["geometry"] = geometry

    _clamp_existing(normalized, "opacity", 0.0, 1.0, default=1.0)
    _clamp_existing(normalized, "zoom", MIN_ZOOM, MAX_ZOOM, default=1.0)
    for key in ("x", "y", "x_pct", "y_pct"):
        _clamp_existing(normalized, key, 0.0, 100.0, default=50.0)
    _normalize_legacy_asset_geometry(normalized)

    if role == "background":
        normalized.pop("rotation", None)
    elif role in {"logo", "decorative"}:
        _clamp_existing(
            normalized,
            "rotation",
            MIN_ROTATION,
            MAX_ROTATION,
            default=0.0,
        )
    else:
        normalized.pop("rotation", None)

    return normalized


def _normalize_legacy_asset_geometry(asset: dict[str, Any]) -> None:
    """Sanitize legacy top-level values still rendered as inline CSS."""
    for size_key, origin_keys in (
        ("width_pct", ("x_pct", "x")),
        ("height_pct", ("y_pct", "y")),
    ):
        if size_key not in asset:
            continue
        size = _finite_number_or_none(asset[size_key])
        if size is None:
            asset.pop(size_key, None)
            continue
        origin_key = next((key for key in origin_keys if key in asset), None)
        origin = 0.0
        if origin_key is not None:
            origin = _clamp(float(asset[origin_key]), 0.0, 99.0)
            asset[origin_key] = origin
        asset[size_key] = _clamp(size, 1.0, 100.0 - origin)

    if "z_index" in asset:
        z_index = _finite_number_or_none(asset["z_index"])
        if z_index is None:
            asset.pop("z_index", None)
        else:
            asset["z_index"] = int(_clamp(z_index, 0.0, 999.0))


def _clamp_existing(
    values: dict[str, Any],
    key: str,
    minimum: float,
    maximum: float,
    *,
    default: float,
) -> None:
    if key not in values:
        return
    number = _finite_number(values[key], default)
    values[key] = max(minimum, min(maximum, number))


def _finite_number(value: Any, default: float) -> float:
    if isinstance(value, bool):
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if isfinite(number) else default


def _finite_number_or_none(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _optional_finite_number(
    values: dict[str, Any],
    key: str,
    default: float,
) -> float | None:
    if key not in values:
        return default
    value = values[key]
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _nonempty_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
