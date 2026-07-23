"""Render Mermaid diagram source to PNG via the Node mermaid-cli helper."""

from __future__ import annotations

import base64
import io
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_MERMAID_DIR = Path(__file__).resolve().parent.parent.parent / "tools" / "mermaid"
_RENDER_SCRIPT = _MERMAID_DIR / "render.mjs"
_DEFAULT_TIMEOUT_SEC = 45
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
# Keep exported diagrams compact on the page (pixel budget after trim).
_MAX_EXPORT_WIDTH_PX = 720
_MAX_EXPORT_HEIGHT_PX = 900

# Horizontal Mermaid directions waste portrait page width; force top-down.
_HORIZONTAL_DIRS = ("LR", "RL")
_DIAGRAM_HEADER_RE = re.compile(
    r"(?im)^(\s*(?:flowchart|graph)\s+)(LR|RL|TB|BT|TD)\b"
)
_DIRECTION_STMT_RE = re.compile(r"(?im)^(\s*direction\s+)(LR|RL|TB|BT|TD)\b")


def normalize_mermaid_for_portrait(source: str) -> str:
    """Rewrite left/right Mermaid layouts to top-down for portrait PDF/DOCX."""
    text = (source or "").strip()
    if not text:
        return text

    def _to_td(match: re.Match[str]) -> str:
        direction = match.group(2).upper()
        if direction in _HORIZONTAL_DIRS or direction == "BT":
            return f"{match.group(1)}TD"
        return match.group(0)

    text = _DIAGRAM_HEADER_RE.sub(_to_td, text)
    text = _DIRECTION_STMT_RE.sub(_to_td, text)
    return text


def _trim_and_fit_png(png: bytes) -> bytes:
    """Crop near-white margins and cap dimensions to reduce blank page space."""
    try:
        from PIL import Image, ImageChops
    except Exception:
        return png

    try:
        image = Image.open(io.BytesIO(png)).convert("RGBA")
    except Exception:
        return png

    # Build a mask of non-background pixels (treat near-white as empty).
    rgb = image.convert("RGB")
    bg = Image.new("RGB", rgb.size, (255, 255, 255))
    diff = ImageChops.difference(rgb, bg)
    bbox = diff.getbbox()
    if bbox:
        pad = 8
        left = max(0, bbox[0] - pad)
        top = max(0, bbox[1] - pad)
        right = min(image.width, bbox[2] + pad)
        bottom = min(image.height, bbox[3] + pad)
        image = image.crop((left, top, right, bottom))

    width, height = image.size
    scale = min(
        1.0,
        _MAX_EXPORT_WIDTH_PX / max(width, 1),
        _MAX_EXPORT_HEIGHT_PX / max(height, 1),
    )
    if scale < 0.999:
        new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    out = io.BytesIO()
    flat = Image.new("RGB", image.size, (255, 255, 255))
    flat.paste(image, mask=image.split()[3] if image.mode == "RGBA" else None)
    flat.save(out, format="PNG", optimize=True)
    return out.getvalue()


def render_mermaid_png(source: str, *, timeout: float = _DEFAULT_TIMEOUT_SEC) -> bytes | None:
    """Return PNG bytes for Mermaid source, or None if unavailable/fails."""
    text = normalize_mermaid_for_portrait(source)
    if not text:
        return None
    if not _RENDER_SCRIPT.is_file():
        logger.warning("Mermaid render script missing: %s", _RENDER_SCRIPT)
        return None

    node = shutil.which("node")
    if not node:
        logger.warning("Node.js not found; skipping Mermaid render")
        return None

    env = os.environ.copy()
    env.setdefault("PUPPETEER_EXECUTABLE_PATH", "/usr/bin/chromium")

    try:
        completed = subprocess.run(
            [node, str(_RENDER_SCRIPT)],
            input=text.encode("utf-8"),
            capture_output=True,
            timeout=timeout,
            cwd=str(_MERMAID_DIR),
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        logger.exception("Mermaid render timed out")
        return None
    except OSError:
        logger.exception("Failed to invoke Mermaid renderer")
        return None

    if completed.returncode != 0:
        err = (completed.stderr or b"").decode("utf-8", errors="replace")[:500]
        logger.warning("Mermaid render failed (code %s): %s", completed.returncode, err)
        return None

    png = completed.stdout or b""
    if not png.startswith(_PNG_MAGIC):
        logger.warning("Mermaid render produced no PNG")
        return None
    return _trim_and_fit_png(png)


# Back-compat alias used by older tests/callers
def render_mermaid_svg(source: str, *, timeout: float = _DEFAULT_TIMEOUT_SEC) -> str | None:
    """Deprecated: PNG is preferred. Returns None (SVG path removed)."""
    _ = source, timeout
    return None


def enrich_diagrams_with_svg(diagrams: list[dict] | None) -> list[dict]:
    """Return shallow-copied diagrams with optional PNG fields for PDF/DOCX."""
    out: list[dict] = []
    for raw in diagrams or []:
        diagram = dict(raw)
        if not diagram.get("png_base64"):
            png = render_mermaid_png(str(diagram.get("source") or ""))
            if png:
                diagram["png_base64"] = base64.b64encode(png).decode("ascii")
        out.append(diagram)
    return out
