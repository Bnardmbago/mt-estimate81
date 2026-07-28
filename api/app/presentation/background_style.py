"""Cover background pan/zoom CSS shared by HTML/PDF export templates."""

from __future__ import annotations

from typing import Any


def cover_background_inline_css(asset: dict[str, Any] | None) -> str:
    """Build focal-point pan/zoom CSS for a full-bleed cover background image."""
    controls = asset if isinstance(asset, dict) else {}
    x = _clamp(_finite(controls.get("x"), 50.0), 0.0, 100.0)
    y = _clamp(_finite(controls.get("y"), 50.0), 0.0, 100.0)
    zoom = _clamp(_finite(controls.get("zoom"), 1.0), 0.1, 4.0)
    opacity = _clamp(_finite(controls.get("opacity"), 1.0), 0.0, 1.0)
    fit = controls.get("fit") if controls.get("fit") in {"cover", "contain", "fill"} else "cover"
    size = _format_number(zoom * 100.0)
    x_pct = _format_number(x)
    y_pct = _format_number(y)
    tx = _format_number(0.0 if x == 0 else -x)
    ty = _format_number(0.0 if y == 0 else -y)

    parts = [
        "position:absolute",
        f"left:{x_pct}%",
        f"top:{y_pct}%",
        f"transform:translate({tx}%, {ty}%)",
        f"opacity:{_format_number(opacity)}",
        "right:auto",
        "bottom:auto",
    ]
    if fit == "fill":
        parts.extend(
            [
                f"width:{size}%",
                f"height:{size}%",
                "max-width:none",
                "object-fit:fill",
            ]
        )
    elif fit == "contain":
        parts.extend(
            [
                "width:auto",
                "height:auto",
                f"max-width:{size}%",
                f"max-height:{size}%",
                "object-fit:contain",
            ]
        )
    else:
        parts.extend(
            [
                "width:auto",
                "height:auto",
                "max-width:none",
                f"min-width:{size}%",
                f"min-height:{size}%",
                "object-fit:cover",
            ]
        )
    return ";".join(parts)


def _finite(value: Any, default: float) -> float:
    if isinstance(value, bool):
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number != number or number in (float("inf"), float("-inf")):
        return default
    return number


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _format_number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.4f}".rstrip("0").rstrip(".")
