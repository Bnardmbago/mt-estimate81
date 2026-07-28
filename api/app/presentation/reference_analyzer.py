"""Deterministic, storage-free analysis of presentation reference files."""

from __future__ import annotations

from io import BytesIO
import re
import struct
from typing import Any

MAX_REFERENCE_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 10
SUPPORTED_IMAGE_TYPES = {
    "image/jpeg": "jpeg",
    "image/png": "png",
    "image/webp": "webp",
}
SUPPORTED_CONTENT_TYPES = {*SUPPORTED_IMAGE_TYPES, "application/pdf"}


class ReferenceValidationError(ValueError):
    """Raised when a reference cannot safely be analyzed."""


def analyze_reference(
    content: bytes,
    filename: str | None = None,
    content_type: str | None = None,
) -> dict[str, Any]:
    """Validate a reference and return deterministic palette/geometry signals."""
    if not content:
        raise ReferenceValidationError("Reference file is empty")
    if len(content) > MAX_REFERENCE_BYTES:
        raise ReferenceValidationError("Reference file is too large")

    normalized_type = _normalized_content_type(content_type)
    detected_type = _detect_content_type(content)
    extension_type = _content_type_from_filename(filename)
    requested_type = normalized_type or extension_type

    if requested_type and requested_type not in SUPPORTED_CONTENT_TYPES:
        raise ReferenceValidationError("Reference file type is unsupported")
    if detected_type is None:
        kind = requested_type or "file"
        raise ReferenceValidationError(f"Reference {kind} is corrupt")
    if requested_type and requested_type != detected_type:
        raise ReferenceValidationError("Reference content does not match its file type and is corrupt")

    if detected_type == "application/pdf":
        return _analyze_pdf(content)
    return _analyze_image(content, detected_type)


def _analyze_image(content: bytes, content_type: str) -> dict[str, Any]:
    try:
        from PIL import Image
    except ImportError:
        try:
            width, height = _minimal_dimensions(content, content_type)
        except (ValueError, struct.error):
            raise ReferenceValidationError("Reference image is corrupt") from None
        palette = [_fallback_color(content)]
    else:
        try:
            with Image.open(BytesIO(content)) as image:
                image.verify()
            with Image.open(BytesIO(content)) as image:
                width, height = image.size
                rgb = image.convert("RGB")
                rgb.thumbnail((128, 128))
                quantized = rgb.quantize(colors=6)
                palette_data = quantized.getpalette() or []
                ranked = sorted(
                    quantized.getcolors(maxcolors=128 * 128) or [],
                    reverse=True,
                )
                palette = []
                for _count, index in ranked:
                    offset = index * 3
                    if offset + 2 >= len(palette_data):
                        continue
                    color = "#{:02X}{:02X}{:02X}".format(
                        *palette_data[offset : offset + 3]
                    )
                    if color not in palette:
                        palette.append(color)
        except (OSError, SyntaxError, ValueError) as exc:
            raise ReferenceValidationError("Reference image is corrupt") from exc

    if width <= 0 or height <= 0:
        raise ReferenceValidationError("Reference image is corrupt")
    if not palette:
        palette = [_fallback_color(content)]

    return {
        "format": SUPPORTED_IMAGE_TYPES[content_type],
        "content_type": content_type,
        "size_bytes": len(content),
        "page_count": 1,
        "palette": palette[:6],
        "geometry": _geometry(width, height),
        "page_images": [{"media_type": content_type, "content": content}],
    }


def _analyze_pdf(content: bytes) -> dict[str, Any]:
    if not content.startswith(b"%PDF-") or b"%%EOF" not in content[-2048:]:
        raise ReferenceValidationError("Reference PDF is corrupt")
    page_count = len(re.findall(rb"/Type\s*/Page(?!s)\b", content))
    if page_count < 1:
        raise ReferenceValidationError("Reference PDF is corrupt")
    if page_count > MAX_PDF_PAGES:
        raise ReferenceValidationError(
            f"Reference PDF exceeds the {MAX_PDF_PAGES}-page limit"
        )

    return {
        "format": "pdf",
        "content_type": "application/pdf",
        "size_bytes": len(content),
        "page_count": page_count,
        "palette": [_fallback_color(content)],
        "geometry": {
            **_geometry(210, 297),
            "approximate": True,
            "unit": "mm",
        },
        # PDF rasterization is optional. An empty list deliberately triggers the
        # deterministic fallback instead of permanently storing the source.
        "page_images": [],
    }


def _geometry(width: int, height: int) -> dict[str, Any]:
    ratio = round(width / height, 4)
    if ratio > 1.05:
        orientation = "landscape"
    elif ratio < 0.95:
        orientation = "portrait"
    else:
        orientation = "square"
    return {
        "width": width,
        "height": height,
        "aspect_ratio": ratio,
        "orientation": orientation,
    }


def _minimal_dimensions(content: bytes, content_type: str) -> tuple[int, int]:
    if content_type == "image/png" and content.startswith(b"\x89PNG\r\n\x1a\n"):
        return struct.unpack(">II", content[16:24])
    if content_type == "image/jpeg":
        cursor = 2
        while cursor + 9 < len(content):
            if content[cursor] != 0xFF:
                cursor += 1
                continue
            marker = content[cursor + 1]
            cursor += 2
            if marker in {0xD8, 0xD9}:
                continue
            length = struct.unpack(">H", content[cursor : cursor + 2])[0]
            if marker in range(0xC0, 0xC4):
                height, width = struct.unpack(">HH", content[cursor + 3 : cursor + 7])
                return width, height
            cursor += length
    if content_type == "image/webp" and content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        if content[12:16] == b"VP8X" and len(content) >= 30:
            width = int.from_bytes(content[24:27], "little") + 1
            height = int.from_bytes(content[27:30], "little") + 1
            return width, height
    raise ValueError("Unsupported or corrupt image")


def _detect_content_type(content: bytes) -> str | None:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "image/webp"
    if content.startswith(b"%PDF-"):
        return "application/pdf"
    return None


def _normalized_content_type(content_type: str | None) -> str | None:
    if not content_type:
        return None
    return content_type.split(";", 1)[0].strip().lower() or None


def _content_type_from_filename(filename: str | None) -> str | None:
    if not filename or "." not in filename:
        return None
    extension = filename.rsplit(".", 1)[-1].casefold()
    return {
        "jpeg": "image/jpeg",
        "jpg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "pdf": "application/pdf",
    }.get(extension, f"unsupported/{extension}")


def _fallback_color(content: bytes) -> str:
    sample = content[:4096]
    channels = [sample[index::3] for index in range(3)]
    values = [sum(channel) // len(channel) if channel else 0 for channel in channels]
    return "#{:02X}{:02X}{:02X}".format(*values)
