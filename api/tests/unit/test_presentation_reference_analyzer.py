from __future__ import annotations

import base64

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.presentation_draft import PresentationPresetDraft
from app.presentation.generate import generate_reference_draft
from app.presentation.reference_analyzer import (
    MAX_PDF_PAGES,
    MAX_REFERENCE_BYTES,
    ReferenceValidationError,
    analyze_reference,
)


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
JPEG_1X1 = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkS"
    "Ew8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJ"
    "CQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIy"
    "MjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEA"
    "AAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIh"
    "MUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6"
    "Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZ"
    "mqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx"
    "8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREA"
    "AgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAV"
    "YnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hp"
    "anN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPE"
    "xcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDi"
    "6KKK+ZP3E//Z"
)


@pytest.mark.parametrize(
    ("content", "filename", "content_type", "expected_format"),
    [
        (PNG_1X1, "reference.png", "image/png", "png"),
        (JPEG_1X1, "reference.jpg", "image/jpeg", "jpeg"),
    ],
)
def test_analyze_reference_accepts_images_and_returns_deterministic_signals(
    content: bytes,
    filename: str,
    content_type: str,
    expected_format: str,
):
    result = analyze_reference(content, filename, content_type)

    assert result["format"] == expected_format
    assert result["geometry"]["width"] == 1
    assert result["geometry"]["height"] == 1
    assert result["geometry"]["orientation"] == "square"
    assert result["palette"]
    assert all(color.startswith("#") and len(color) == 7 for color in result["palette"])
    assert result["page_images"][0]["content"] == content


@pytest.mark.parametrize(
    ("content", "filename", "content_type", "message"),
    [
        (b"", "empty.png", "image/png", "empty"),
        (b"not an image", "bad.png", "image/png", "corrupt"),
        (b"GIF89a", "bad.gif", "image/gif", "unsupported"),
        (b"x" * (MAX_REFERENCE_BYTES + 1), "large.png", "image/png", "too large"),
        (b"%PDF-1.4\nnot-a-real-pdf", "bad.pdf", "application/pdf", "corrupt"),
    ],
)
def test_analyze_reference_rejects_invalid_inputs(
    content: bytes,
    filename: str,
    content_type: str,
    message: str,
):
    with pytest.raises(ReferenceValidationError, match=message):
        analyze_reference(content, filename, content_type)


def test_analyze_reference_rejects_pdf_over_page_limit():
    pages = b"\n".join(
        f"{index} 0 obj << /Type /Page >> endobj".encode()
        for index in range(1, MAX_PDF_PAGES + 2)
    )
    pdf = b"%PDF-1.4\n" + pages + b"\n%%EOF"

    with pytest.raises(ReferenceValidationError, match="page limit"):
        analyze_reference(pdf, "large.pdf", "application/pdf")


class NoVisionProvider:
    def supports_vision(self) -> bool:
        return False

    async def generate_presentation_draft(self, **kwargs):
        raise AssertionError("no-vision provider must not be called")


@pytest.mark.asyncio
async def test_no_vision_keeps_deterministic_draft_with_localized_warning(
    db_session: AsyncSession,
):
    draft = PresentationPresetDraft(source_locale="ja")
    db_session.add(draft)
    await db_session.commit()

    await generate_reference_draft(
        db_session,
        draft.id,
        content=PNG_1X1,
        filename="reference.png",
        content_type="image/png",
        provider=NoVisionProvider(),
    )

    await db_session.refresh(draft)
    assert draft.theme_draft["config"]["colors"]["primary"]
    assert draft.style_draft["config"]["line_spacing"] > 0
    assert draft.template_draft["config"]["page"] == {
        "size": "A4",
        "orientation": "portrait",
    }
    assert draft.generation_meta["status"] == "done"
    assert draft.generation_meta["vision_used"] is False
    assert any("ビジョン" in warning for warning in draft.errors)


class FailingVisionProvider:
    def supports_vision(self) -> bool:
        return True

    async def generate_presentation_draft(self, **kwargs):
        raise RuntimeError("multimodal unavailable")


@pytest.mark.asyncio
async def test_multimodal_failure_keeps_deterministic_draft(
    db_session: AsyncSession,
):
    draft = PresentationPresetDraft(source_locale="en")
    db_session.add(draft)
    await db_session.commit()

    await generate_reference_draft(
        db_session,
        draft.id,
        content=PNG_1X1,
        filename="reference.png",
        content_type="image/png",
        provider=FailingVisionProvider(),
    )

    await db_session.refresh(draft)
    assert draft.generation_meta["status"] == "done"
    assert draft.generation_meta["vision_used"] is False
    assert any("Vision analysis failed" in warning for warning in draft.errors)
