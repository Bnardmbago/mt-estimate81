"""Lifecycle operations for editable presentation preset drafts."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import re
import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.i18n.localized_content import normalize_locale
from app.models.presentation import PresentationStyle, PresentationTemplate, PresentationTheme
from app.models.presentation_draft import PresentationPresetDraft
from app.presentation.seeds import (
    COMFORTABLE_STYLE,
    CORPORATE_NAVY_CONFIG,
    DEFAULT_COVER_DESIGN,
    DEFAULT_COVER_FIELDS,
)
from app.presentation.translate import PresentationTranslationError, ensure_preset_bilingual
from app.presentation.validators import clamp_cover_design, normalize_page
from app.presentation.asset_paths import (
    draft_prefixes_for,
    promote_destination,
)
from app.storage.factory import get_storage_backend

_AXES = (
    ("theme", PresentationTheme, "theme_draft", "target_theme_id"),
    ("style", PresentationStyle, "style_draft", "target_style_id"),
    ("template", PresentationTemplate, "template_draft", "target_template_id"),
)


async def create_blank_draft(
    db: AsyncSession,
    *,
    source_locale: str,
    target_theme_id: str | None = None,
    target_style_id: str | None = None,
    target_template_id: str | None = None,
) -> PresentationPresetDraft:
    theme_draft, style_draft, template_draft = _blank_axis_payloads(source_locale)
    draft = PresentationPresetDraft(
        source_locale=source_locale,
        theme_draft=theme_draft,
        style_draft=style_draft,
        template_draft=template_draft,
        target_theme_id=target_theme_id,
        target_style_id=target_style_id,
        target_template_id=target_template_id,
    )
    db.add(draft)
    await db.commit()
    await db.refresh(draft)
    return draft


async def update_draft_axis(
    db: AsyncSession,
    draft_id: uuid.UUID | str,
    *,
    theme_draft: dict[str, Any] | None = None,
    style_draft: dict[str, Any] | None = None,
    template_draft: dict[str, Any] | None = None,
) -> PresentationPresetDraft:
    draft = await _get_draft(db, draft_id)
    if draft.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft presentation presets can be edited")

    if theme_draft is not None:
        draft.theme_draft = deepcopy(theme_draft)
    if style_draft is not None:
        draft.style_draft = deepcopy(style_draft)
    if template_draft is not None:
        draft.template_draft = _normalize_template_draft(template_draft)
    draft.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(draft)
    return draft


async def approve_draft(
    db: AsyncSession,
    draft_id: uuid.UUID | str,
    *,
    source_locale: str,
) -> dict[str, str]:
    draft = await _get_draft(db, draft_id)
    if draft.status != "draft":
        raise HTTPException(status_code=409, detail="Presentation draft is not awaiting approval")

    template_payload = _normalize_template_draft(draft.template_draft)
    payloads = {
        "theme": deepcopy(draft.theme_draft),
        "style": deepcopy(draft.style_draft),
        "template": template_payload,
    }
    try:
        for kind in ("theme", "style", "template"):
            payloads[kind] = await ensure_preset_bilingual(
                db,
                payloads[kind],
                content_locale=source_locale,
            )
    except PresentationTranslationError as exc:
        draft.errors = [str(exc)]
        draft.updated_at = datetime.utcnow()
        await db.commit()
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    draft.theme_draft = payloads["theme"]
    draft.style_draft = payloads["style"]
    draft.template_draft = payloads["template"]
    template_payload = payloads["template"]
    template_id = draft.target_template_id or await _available_slug(
        db,
        PresentationTemplate,
        _payload_name(template_payload),
        fallback="template",
    )
    storage = get_storage_backend()
    draft_prefixes = draft_prefixes_for(str(draft.id))
    promoted, backups = await _promote_referenced_assets(
        storage,
        template_payload,
        draft_prefixes=draft_prefixes,
        template_id=template_id,
    )

    try:
        ids: dict[str, str] = {}
        for kind, model, _draft_attr, target_attr in _AXES:
            target_id = getattr(draft, target_attr)
            if kind == "template":
                preset_id = template_id
            else:
                preset_id = target_id or await _available_slug(
                    db,
                    model,
                    _payload_name(payloads[kind]),
                    fallback=kind,
                )
            row = await _upsert_preset(
                db,
                model,
                preset_id=preset_id,
                payload=payloads[kind],
                require_existing=target_id is not None,
            )
            ids[f"{kind}_id"] = row.id

        draft.status = "approved"
        draft.source_locale = source_locale
        draft.target_theme_id = ids["theme_id"]
        draft.target_style_id = ids["style_id"]
        draft.target_template_id = ids["template_id"]
        draft.template_draft = template_payload
        draft.updated_at = datetime.utcnow()
        await db.commit()
    except BaseException:
        await db.rollback()
        await _restore_promoted_assets(storage, promoted, backups)
        raise

    for prefix in draft_prefixes:
        await storage.delete_prefix(prefix)
    return ids


async def discard_draft(db: AsyncSession, draft_id: uuid.UUID | str) -> None:
    draft = await _get_draft(db, draft_id)
    prefixes = draft_prefixes_for(str(draft.id))
    await db.delete(draft)
    await db.commit()
    storage = get_storage_backend()
    for prefix in prefixes:
        await storage.delete_prefix(prefix)


async def _get_draft(
    db: AsyncSession,
    draft_id: uuid.UUID | str,
) -> PresentationPresetDraft:
    try:
        key = draft_id if isinstance(draft_id, uuid.UUID) else uuid.UUID(str(draft_id))
    except (TypeError, ValueError):
        raise HTTPException(status_code=404, detail="Presentation draft not found") from None
    draft = await db.get(PresentationPresetDraft, key)
    if draft is None:
        raise HTTPException(status_code=404, detail="Presentation draft not found")
    return draft


def _blank_axis_payloads(
    source_locale: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Seed blank drafts with named starter Theme/Style/Template payloads."""
    locale = normalize_locale(source_locale)
    if locale == "ja":
        names = ("新規テーマ", "新規スタイル", "新規テンプレート")
    else:
        names = ("New Theme", "New Style", "New Template")
    theme = {
        "name": names[0],
        "description": "",
        "is_active": True,
        "config": deepcopy(CORPORATE_NAVY_CONFIG),
    }
    style = {
        "name": names[1],
        "description": "",
        "is_active": True,
        "config": deepcopy(COMFORTABLE_STYLE),
    }
    template = {
        "name": names[2],
        "description": "",
        "is_active": True,
        "config": {
            "page": {"size": "A4", "orientation": "portrait"},
            "layout": "classic_linear",
            "cover": True,
            "cover_fields": deepcopy(DEFAULT_COVER_FIELDS),
            "cover_design": deepcopy(DEFAULT_COVER_DESIGN),
        },
    }
    return theme, style, template


def _normalize_template_draft(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(payload)
    config = normalized.get("config")
    if not isinstance(config, dict):
        config = {}
    else:
        config = deepcopy(config)
    config["page"] = normalize_page(config.get("page"))
    if "cover_design" in config:
        config["cover_design"] = clamp_cover_design(config.get("cover_design"))
    normalized["config"] = config
    return normalized


def _payload_name(payload: dict[str, Any]) -> str:
    value = payload.get("name")
    return value.strip() if isinstance(value, str) else ""


async def _available_slug(
    db: AsyncSession,
    model: type,
    name: str,
    *,
    fallback: str,
) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-") or fallback
    base = base[:64].rstrip("-") or fallback
    candidate = base
    suffix = 2
    while await db.get(model, candidate) is not None:
        tail = f"-{suffix}"
        candidate = f"{base[: 64 - len(tail)].rstrip('-')}{tail}"
        suffix += 1
    return candidate


async def _upsert_preset(
    db: AsyncSession,
    model: type,
    *,
    preset_id: str,
    payload: dict[str, Any],
    require_existing: bool,
) -> Any:
    row = await db.get(model, preset_id)
    if row is None and require_existing:
        raise HTTPException(status_code=404, detail=f"Target preset '{preset_id}' not found")

    name = _payload_name(payload)
    requested_active = bool(payload.get("is_active", True))
    is_active = requested_active and bool(name)
    description = payload.get("description")
    if not isinstance(description, str):
        description = None
    config = payload.get("config")
    if not isinstance(config, dict):
        config = {}
    else:
        config = deepcopy(config)
    content = payload.get("content")
    if isinstance(content, dict):
        config["content"] = deepcopy(content)

    if row is None:
        row = model(
            id=preset_id,
            name=name,
            description=description,
            config=deepcopy(config),
            is_active=is_active,
            is_default=False,
            updated_at=datetime.utcnow(),
        )
        db.add(row)
    else:
        row.name = name
        row.description = description
        row.config = deepcopy(config)
        row.is_active = is_active
        row.updated_at = datetime.utcnow()
    await db.flush()
    return row


async def _promote_referenced_assets(
    storage: Any,
    template_payload: dict[str, Any],
    *,
    draft_prefixes: tuple[str, ...],
    template_id: str,
) -> tuple[list[str], dict[str, bytes]]:
    candidate_paths: set[str] = set()
    for prefix in draft_prefixes:
        candidate_paths.update(await storage.list_prefix(prefix))
    referenced: set[str] = set()
    for prefix in draft_prefixes:
        referenced.update(_collect_candidate_paths(template_payload, prefix))
    promoted: list[str] = []
    backups: dict[str, bytes] = {}
    replacements: dict[str, str] = {}

    for source in sorted(referenced & candidate_paths):
        filename = source.rsplit("/", 1)[-1]
        destination = promote_destination(template_id, filename)
        if await storage.exists(destination):
            backups[destination] = await storage.read(destination)
        await storage.save(destination, await storage.read(source))
        promoted.append(destination)
        replacements[source] = destination

    _replace_asset_paths(template_payload, replacements)
    return promoted, backups


def _collect_candidate_paths(value: Any, prefix: str) -> set[str]:
    if isinstance(value, str):
        return {value} if value.startswith(f"{prefix}/") else set()
    if isinstance(value, dict):
        paths: set[str] = set()
        for child in value.values():
            paths.update(_collect_candidate_paths(child, prefix))
        return paths
    if isinstance(value, list):
        paths = set()
        for child in value:
            paths.update(_collect_candidate_paths(child, prefix))
        return paths
    return set()


def _replace_asset_paths(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(child, str) and child in replacements:
                value[key] = replacements[child]
            else:
                _replace_asset_paths(child, replacements)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            if isinstance(child, str) and child in replacements:
                value[index] = replacements[child]
            else:
                _replace_asset_paths(child, replacements)
    return value


async def _restore_promoted_assets(
    storage: Any,
    promoted: list[str],
    backups: dict[str, bytes],
) -> None:
    for path in promoted:
        if path in backups:
            await storage.save(path, backups[path])
        elif await storage.exists(path):
            await storage.delete(path)
