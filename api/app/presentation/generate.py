"""Reference-to-draft generation with deterministic vision fallback."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import logging
from typing import Any, Literal, NamedTuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_ai_provider
from app.ai.schemas_presentation import PresentationDraftAI
from app.database import SessionLocal
from app.models.presentation_draft import PresentationPresetDraft
from app.presentation.reference_analyzer import (
    ReferenceValidationError,
    analyze_reference,
)
from app.presentation.validators import clamp_cover_design, normalize_page

logger = logging.getLogger(__name__)
Locale = Literal["ja", "en"]


class _EphemeralSource(NamedTuple):
    content: bytes
    filename: str | None
    content_type: str | None


_EPHEMERAL_SOURCES: dict[str, _EphemeralSource] = {}


def stage_reference_generation(
    draft_id: uuid.UUID | str,
    *,
    content: bytes,
    filename: str | None,
    content_type: str | None,
) -> None:
    """Stage source bytes in process memory until the background task consumes them."""
    _EPHEMERAL_SOURCES[str(draft_id)] = _EphemeralSource(
        bytes(content),
        filename,
        content_type,
    )


async def run_reference_generation(draft_id: uuid.UUID | str) -> None:
    """Background entrypoint using an independent database session."""
    source = _EPHEMERAL_SOURCES.pop(str(draft_id), None)
    if source is None:
        logger.warning("No ephemeral presentation source found for draft %s", draft_id)
        return

    async with SessionLocal() as db:
        try:
            await generate_reference_draft(
                db,
                draft_id,
                content=source.content,
                filename=source.filename,
                content_type=source.content_type,
            )
        except ReferenceValidationError as exc:
            await _mark_generation_failed(db, draft_id, str(exc))
        except Exception as exc:
            logger.exception("Presentation reference generation failed for %s", draft_id)
            await _mark_generation_failed(db, draft_id, str(exc))


async def generate_reference_draft(
    db: AsyncSession,
    draft_id: uuid.UUID | str,
    *,
    content: bytes,
    filename: str | None,
    content_type: str | None,
    provider: Any | None = None,
) -> PresentationPresetDraft:
    """Analyze ephemeral bytes and persist normalized draft JSON only."""
    analysis = analyze_reference(content, filename, content_type)
    draft = await _get_draft(db, draft_id)
    if draft is None:
        raise LookupError("Presentation draft not found")

    locale: Locale = "ja" if draft.source_locale == "ja" else "en"
    page_images = analysis.get("page_images") or []
    signals = {
        key: deepcopy(value)
        for key, value in analysis.items()
        if key != "page_images"
    }
    theme, style, template = _deterministic_payloads(signals, locale)
    warnings: list[str] = []
    vision_used = False

    if provider is None:
        try:
            provider = await get_ai_provider(db)
        except Exception as exc:
            logger.warning("AI provider unavailable for presentation draft: %s", exc)
            warnings.append(_vision_failure_warning(locale))

    supports_vision = bool(
        provider is not None
        and callable(getattr(provider, "supports_vision", None))
        and provider.supports_vision()
    )
    if supports_vision and page_images:
        try:
            ai_result = await provider.generate_presentation_draft(
                source_locale=locale,
                signals=signals,
                page_images=page_images,
            )
            if not isinstance(ai_result, PresentationDraftAI):
                ai_result = PresentationDraftAI.model_validate(ai_result)
            theme, style, template = ai_result.to_draft_payloads()
            vision_used = True
        except Exception:
            logger.exception("Multimodal presentation generation failed")
            warnings.append(_vision_failure_warning(locale))
    elif not warnings:
        warnings.append(_no_vision_warning(locale))

    theme, style, template = _normalize_payloads(theme, style, template)
    draft.theme_draft = theme
    draft.style_draft = style
    draft.template_draft = template
    draft.errors = warnings
    draft.generation_meta = {
        "status": "done",
        "vision_used": vision_used,
        "source": {
            "format": signals["format"],
            "content_type": signals["content_type"],
            "size_bytes": signals["size_bytes"],
            "page_count": signals["page_count"],
        },
        "signals": {
            "palette": signals["palette"],
            "geometry": signals["geometry"],
        },
        "completed_at": datetime.utcnow().isoformat() + "Z",
    }
    draft.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(draft)
    return draft


def _deterministic_payloads(
    signals: dict[str, Any],
    locale: Locale,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    palette = [
        str(value).removeprefix("#").upper()
        for value in signals.get("palette", [])
        if isinstance(value, str)
    ]
    primary = palette[0] if palette else "1E3A5F"
    accent = palette[1] if len(palette) > 1 else primary
    orientation = signals.get("geometry", {}).get("orientation")
    page_orientation = "landscape" if orientation == "landscape" else "portrait"
    names = (
        ("参照テーマ", "参照スタイル", "参照テンプレート")
        if locale == "ja"
        else ("Reference Theme", "Reference Style", "Reference Template")
    )
    theme = {
        "name": names[0],
        "description": "",
        "is_active": False,
        "config": {
            "colors": {
                "primary": primary,
                "accent": accent,
                "surface": "FFFFFF",
                "text_body": "111827",
            }
        },
    }
    style = {
        "name": names[1],
        "description": "",
        "is_active": False,
        "config": {
            "density": "comfortable",
            "margins": {
                "top_mm": 18,
                "right_mm": 16,
                "bottom_mm": 18,
                "left_mm": 16,
            },
            "line_spacing": 1.4,
            "base_font_size_pt": 10,
        },
    }
    template = {
        "name": names[2],
        "description": "",
        "is_active": False,
        "config": {
            "page": {"size": "A4", "orientation": page_orientation},
            "layout": "executive_cover",
            "cover": True,
            "cover_fields": [],
            "cover_design": {
                "alignment": "left",
                "padding_mm": 24,
                "typography": {"title_pt": 30, "metadata_pt": 10},
                "colors": {"primary": primary, "accent": accent},
                "assets": [],
            },
        },
    }
    return theme, style, template


def _normalize_payloads(
    theme: dict[str, Any],
    style: dict[str, Any],
    template: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    normalized_theme = deepcopy(theme)
    normalized_style = deepcopy(style)
    normalized_template = deepcopy(template)
    config = normalized_template.get("config")
    if not isinstance(config, dict):
        config = {}
    else:
        config = deepcopy(config)
    config["page"] = normalize_page(config.get("page"))
    config["cover_design"] = clamp_cover_design(config.get("cover_design"))
    fields = config.get("cover_fields")
    config["cover_fields"] = fields if isinstance(fields, list) else []
    normalized_template["config"] = config
    return normalized_theme, normalized_style, normalized_template


async def _get_draft(
    db: AsyncSession,
    draft_id: uuid.UUID | str,
) -> PresentationPresetDraft | None:
    try:
        key = draft_id if isinstance(draft_id, uuid.UUID) else uuid.UUID(str(draft_id))
    except (TypeError, ValueError):
        return None
    return await db.get(PresentationPresetDraft, key)


async def _mark_generation_failed(
    db: AsyncSession,
    draft_id: uuid.UUID | str,
    error: str,
) -> None:
    draft = await _get_draft(db, draft_id)
    if draft is None:
        return
    draft.generation_meta = {
        "status": "failed",
        "completed_at": datetime.utcnow().isoformat() + "Z",
    }
    draft.errors = [error]
    draft.updated_at = datetime.utcnow()
    await db.commit()


def _no_vision_warning(locale: Locale) -> str:
    if locale == "ja":
        return "ビジョン対応AIが利用できないため、決定論的な分析結果を使用しました。"
    return "Vision-capable AI is unavailable; deterministic analysis was used."


def _vision_failure_warning(locale: Locale) -> str:
    if locale == "ja":
        return "ビジョン分析に失敗したため、決定論的な分析結果を使用しました。"
    return "Vision analysis failed; deterministic analysis was used."
