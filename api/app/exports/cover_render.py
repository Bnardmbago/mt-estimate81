"""Prepare cover assets/SVG for HTML/PDF/DOCX renderers."""

from __future__ import annotations

import base64
import logging
import mimetypes

logger = logging.getLogger(__name__)


async def embed_cover_asset_data(ctx: dict, storage) -> None:
    """Replace private storage paths with data URIs for PDF/HTML renderers."""
    cover = ctx.get("cover") or {}
    for asset in cover.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        storage_path = str(asset.get("storage_path") or "").strip()
        if not storage_path:
            continue
        current_url = str(asset.get("url") or "")
        if current_url.startswith("data:"):
            continue
        try:
            content = await storage.read(storage_path)
        except Exception:
            logger.warning(
                "Cover asset could not be read for export: %s",
                storage_path,
                exc_info=True,
            )
            continue
        content_type = mimetypes.guess_type(storage_path)[0] or "application/octet-stream"
        encoded = base64.b64encode(content).decode("ascii")
        asset["url"] = f"data:{content_type};base64,{encoded}"
