"""Rasterize SVG markup to PNG for DOCX embeds."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def svg_to_png_bytes(svg: str, *, scale: float = 1.5) -> bytes | None:
    """Convert SVG string to PNG bytes. Returns None if empty or conversion fails."""
    markup = (svg or "").strip()
    if not markup:
        return None
    try:
        import cairosvg

        result = cairosvg.svg2png(bytestring=markup.encode("utf-8"), scale=scale)
        if not result:
            return None
        return bytes(result)
    except Exception:
        logger.exception("Failed to rasterize SVG for proposal export")
        return None
