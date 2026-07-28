"""Admin + public routes for Theme / Style / Template presentation presets."""

from __future__ import annotations

import mimetypes
import uuid
from copy import deepcopy
from pathlib import Path, PurePosixPath

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, require_admin, require_full_account
from app.models.presentation import (
    PresentationStyle,
    PresentationTemplate,
    PresentationTheme,
)
from app.models.presentation_draft import PresentationPresetDraft
from app.models.user import User
from app.presentation import drafts as presentation_drafts
from app.presentation import service as presentation_service
from app.presentation.asset_paths import (
    draft_asset_path,
    draft_prefixes_for,
    find_asset_under_prefixes,
    is_presentation_asset_path,
    template_asset_path,
    template_prefixes_for,
)
from app.presentation.consistency import recommend_consistency
from app.presentation.generate import run_reference_generation, stage_reference_generation
from app.presentation.reference_analyzer import MAX_REFERENCE_BYTES
from app.presentation.resolver import get_presentation_defaults
from app.schemas.presentation import (
    PresentationDefaults,
    PresentationDefaultsUpdate,
    PresentationPresetCreate,
    PresentationPresetDetail,
    PresentationPresetSummary,
    PresentationPresetUpdate,
)
from app.schemas.presentation_draft import (
    PresentationApplySuggestions,
    PresentationConsistencyResponse,
    PresentationDraftApprovalResult,
    PresentationDraftApprove,
    PresentationDraftAsset,
    PresentationDraftCreate,
    PresentationDraftRead,
    PresentationDraftUpdate,
)
from app.storage.factory import get_storage_backend

admin_router = APIRouter(prefix="/admin/presentation", tags=["admin"])
public_router = APIRouter(prefix="/presentation", tags=["presentation"])


def _theme_to_detail(row: PresentationTheme) -> PresentationPresetDetail:
    colors = (row.config or {}).get("colors") or {}
    return PresentationPresetDetail(
        id=row.id,
        name=row.name,
        description=row.description,
        is_default=row.is_default,
        is_active=row.is_active,
        config=row.config or {},
        logo_storage_path=row.logo_storage_path,
        has_logo=bool(row.logo_storage_path),
        logo_url=f"/admin/presentation/themes/{row.id}/logo" if row.logo_storage_path else None,
        preview={
            "primary": colors.get("primary"),
            "accent": colors.get("accent"),
            "surface": colors.get("surface"),
        },
    )


def _style_to_detail(row: PresentationStyle) -> PresentationPresetDetail:
    return PresentationPresetDetail(
        id=row.id,
        name=row.name,
        description=row.description,
        is_default=row.is_default,
        is_active=row.is_active,
        config=row.config or {},
        preview={
            "base_font_size_pt": (row.config or {}).get("base_font_size_pt"),
            "line_spacing": (row.config or {}).get("line_spacing"),
        },
    )


def _template_to_detail(row: PresentationTemplate) -> PresentationPresetDetail:
    return PresentationPresetDetail(
        id=row.id,
        name=row.name,
        description=row.description,
        is_default=row.is_default,
        is_active=row.is_active,
        config=row.config or {},
        preview={
            "layout": (row.config or {}).get("layout"),
            "has_cover": bool((row.config or {}).get("cover")),
        },
    )


def _to_summary_theme(row: PresentationTheme) -> PresentationPresetSummary:
    colors = (row.config or {}).get("colors") or {}
    return PresentationPresetSummary(
        id=row.id,
        name=row.name,
        description=row.description,
        is_default=row.is_default,
        is_active=row.is_active,
        preview={
            "primary": colors.get("primary"),
            "accent": colors.get("accent"),
            "surface": colors.get("surface"),
        },
    )


def _to_summary_style(row: PresentationStyle) -> PresentationPresetSummary:
    return PresentationPresetSummary(
        id=row.id,
        name=row.name,
        description=row.description,
        is_default=row.is_default,
        is_active=row.is_active,
        preview={
            "base_font_size_pt": (row.config or {}).get("base_font_size_pt"),
            "line_spacing": (row.config or {}).get("line_spacing"),
        },
    )


def _to_summary_template(row: PresentationTemplate) -> PresentationPresetSummary:
    config = row.config or {}
    return PresentationPresetSummary(
        id=row.id,
        name=row.name,
        description=row.description,
        is_default=row.is_default,
        is_active=row.is_active,
        preview={
            "layout": config.get("layout"),
            "has_cover": bool(config.get("cover")),
        },
    )


def _draft_configs(
    draft: PresentationPresetDraft,
) -> tuple[dict, dict, dict]:
    theme = draft.theme_draft if isinstance(draft.theme_draft, dict) else {}
    style = draft.style_draft if isinstance(draft.style_draft, dict) else {}
    template = draft.template_draft if isinstance(draft.template_draft, dict) else {}
    theme_config = theme.get("config") if isinstance(theme.get("config"), dict) else {}
    style_config = style.get("config") if isinstance(style.get("config"), dict) else {}
    template_config = (
        template.get("config") if isinstance(template.get("config"), dict) else {}
    )
    return theme_config, style_config, template_config


def _consistency_suggestions(draft: PresentationPresetDraft) -> list[dict]:
    theme_config, style_config, template_config = _draft_configs(draft)
    cover_design = template_config.get("cover_design")
    return recommend_consistency(
        cover_design=cover_design if isinstance(cover_design, dict) else {},
        theme_draft=theme_config,
        style_draft=style_config,
    )


def _set_nested_value(target: dict, field_path: str, value: object) -> None:
    parts = [part for part in field_path.split(".") if part]
    if not parts:
        return
    cursor = target
    for part in parts[:-1]:
        child = cursor.get(part)
        if not isinstance(child, dict):
            child = {}
            cursor[part] = child
        cursor = child
    cursor[parts[-1]] = deepcopy(value)


# --- Public catalog ---


@public_router.get("/themes", response_model=list[PresentationPresetSummary])
async def list_themes_public(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_full_account),
):
    rows = await presentation_service.list_presets(db, "theme", active_only=True)
    return [_to_summary_theme(r) for r in rows]


@public_router.get("/styles", response_model=list[PresentationPresetSummary])
async def list_styles_public(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_full_account),
):
    rows = await presentation_service.list_presets(db, "style", active_only=True)
    return [_to_summary_style(r) for r in rows]


@public_router.get("/templates", response_model=list[PresentationPresetSummary])
async def list_templates_public(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_full_account),
):
    rows = await presentation_service.list_presets(db, "template", active_only=True)
    return [_to_summary_template(r) for r in rows]


@public_router.get(
    "/templates/{template_id}",
    response_model=PresentationPresetDetail,
)
async def get_template_public(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_full_account),
):
    row = await presentation_service.get_preset(db, "template", template_id)
    if not row.is_active:
        raise HTTPException(status_code=404, detail=f"template '{template_id}' not found")
    return _template_to_detail(row)


@public_router.get("/defaults", response_model=PresentationDefaults)
async def get_defaults_public(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_full_account),
):
    return PresentationDefaults(**(await get_presentation_defaults(db)))


# --- Admin: drafts ---


@admin_router.get("/drafts", response_model=list[PresentationDraftRead])
async def list_presentation_drafts(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(
        select(PresentationPresetDraft).order_by(
            PresentationPresetDraft.created_at.desc()
        )
    )
    return list(result.scalars().all())


@admin_router.post(
    "/drafts",
    response_model=PresentationDraftRead,
    status_code=201,
)
async def create_presentation_draft(
    body: PresentationDraftCreate | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    request = body or PresentationDraftCreate()
    return await presentation_drafts.create_blank_draft(
        db,
        source_locale=request.source_locale,
        target_theme_id=request.target_theme_id,
        target_style_id=request.target_style_id,
        target_template_id=request.target_template_id,
    )


@admin_router.post(
    "/drafts/from-reference",
    response_model=PresentationDraftRead,
    status_code=202,
)
async def create_presentation_draft_from_reference(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source_locale: str = Form("en"),
    target_theme_id: str | None = Form(None),
    target_style_id: str | None = Form(None),
    target_template_id: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    try:
        request = PresentationDraftCreate(
            source_locale=source_locale,
            target_theme_id=target_theme_id,
            target_style_id=target_style_id,
            target_template_id=target_template_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Reference file is empty")
    if len(content) > MAX_REFERENCE_BYTES:
        raise HTTPException(status_code=413, detail="Reference file is too large")
    draft = await presentation_drafts.create_blank_draft(
        db,
        source_locale=request.source_locale,
        target_theme_id=request.target_theme_id,
        target_style_id=request.target_style_id,
        target_template_id=request.target_template_id,
    )
    draft.generation_meta = {"status": "queued"}
    await db.commit()
    await db.refresh(draft)
    stage_reference_generation(
        draft.id,
        content=content,
        filename=file.filename,
        content_type=file.content_type,
    )
    background_tasks.add_task(run_reference_generation, draft.id)
    return draft


@admin_router.get("/drafts/{draft_id}", response_model=PresentationDraftRead)
async def get_presentation_draft(
    draft_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    return await presentation_drafts._get_draft(db, draft_id)


@admin_router.patch("/drafts/{draft_id}", response_model=PresentationDraftRead)
async def update_presentation_draft(
    draft_id: uuid.UUID,
    body: PresentationDraftUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    if (
        body.theme_draft is None
        and body.style_draft is None
        and body.template_draft is None
    ):
        raise HTTPException(status_code=400, detail="Provide at least one draft axis")
    return await presentation_drafts.update_draft_axis(
        db,
        draft_id,
        theme_draft=body.theme_draft,
        style_draft=body.style_draft,
        template_draft=body.template_draft,
    )


@admin_router.post(
    "/drafts/{draft_id}/consistency",
    response_model=PresentationConsistencyResponse,
)
async def check_presentation_draft_consistency(
    draft_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    draft = await presentation_drafts._get_draft(db, draft_id)
    return {"suggestions": _consistency_suggestions(draft)}


@admin_router.post(
    "/drafts/{draft_id}/apply-suggestions",
    response_model=PresentationDraftRead,
)
async def apply_presentation_draft_suggestions(
    draft_id: uuid.UUID,
    body: PresentationApplySuggestions,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    draft = await presentation_drafts._get_draft(db, draft_id)
    suggestions = _consistency_suggestions(draft)
    selected_ids = (
        {item["id"] for item in suggestions}
        if body.suggestion_ids is None
        else set(body.suggestion_ids)
    )
    known_ids = {item["id"] for item in suggestions}
    unknown_ids = selected_ids - known_ids
    if unknown_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown consistency suggestions: {', '.join(sorted(unknown_ids))}",
        )

    theme_draft = deepcopy(draft.theme_draft)
    style_draft = deepcopy(draft.style_draft)
    for suggestion in suggestions:
        if suggestion["id"] not in selected_ids:
            continue
        axis = theme_draft if suggestion["target"] == "theme" else style_draft
        config = axis.get("config")
        if not isinstance(config, dict):
            config = {}
            axis["config"] = config
        _set_nested_value(config, suggestion["field_path"], suggestion["after"])

    return await presentation_drafts.update_draft_axis(
        db,
        draft_id,
        theme_draft=theme_draft,
        style_draft=style_draft,
    )


@admin_router.post(
    "/drafts/{draft_id}/approve",
    response_model=PresentationDraftApprovalResult,
)
async def approve_presentation_draft(
    draft_id: uuid.UUID,
    body: PresentationDraftApprove | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    draft = await presentation_drafts._get_draft(db, draft_id)
    source_locale = body.source_locale if body and body.source_locale else draft.source_locale
    return await presentation_drafts.approve_draft(
        db,
        draft_id,
        source_locale=source_locale,
    )


@admin_router.delete("/drafts/{draft_id}", status_code=204)
async def discard_presentation_draft(
    draft_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    await presentation_drafts.discard_draft(db, draft_id)


@admin_router.post(
    "/drafts/{draft_id}/assets",
    response_model=PresentationDraftAsset,
    status_code=201,
)
async def upload_presentation_draft_asset(
    draft_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    draft = await presentation_drafts._get_draft(db, draft_id)
    if draft.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft assets can be uploaded")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Asset file is empty")
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Asset exceeds the 20 MB limit")
    extension = Path(file.filename or "").suffix.lower()
    if extension not in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
        raise HTTPException(status_code=400, detail="Unsupported presentation asset type")
    asset_id = str(uuid.uuid4())
    storage_path = draft_asset_path(str(draft.id), asset_id, extension)
    await get_storage_backend().save(storage_path, content)
    return PresentationDraftAsset(
        id=asset_id,
        storage_path=storage_path,
        filename=file.filename or f"{asset_id}{extension}",
        content_type=file.content_type,
        size_bytes=len(content),
    )


@admin_router.get("/drafts/{draft_id}/assets/{asset_id}")
async def get_presentation_draft_asset(
    draft_id: uuid.UUID,
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    draft = await presentation_drafts._get_draft(db, draft_id)
    storage = get_storage_backend()
    prefixes = draft_prefixes_for(str(draft_id))
    candidates: list[str] = []
    for prefix in prefixes:
        candidates.extend(await storage.list_prefix(prefix))
    storage_path = find_asset_under_prefixes(
        candidates,
        prefixes=prefixes,
        asset_id=str(asset_id),
    )
    if storage_path is None:
        storage_path = _draft_referenced_asset_path(draft, str(asset_id))
    if storage_path is None:
        raise HTTPException(status_code=404, detail="Draft asset not found")
    try:
        content = await storage.read(storage_path)
    except (FileNotFoundError, OSError):
        raise HTTPException(status_code=404, detail="Draft asset not found") from None
    media_type = mimetypes.guess_type(storage_path)[0] or "application/octet-stream"
    return Response(content=content, media_type=media_type)


@admin_router.delete("/drafts/{draft_id}/assets/{asset_id}", status_code=204)
async def delete_presentation_draft_asset(
    draft_id: uuid.UUID,
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    draft = await presentation_drafts._get_draft(db, draft_id)
    storage = get_storage_backend()
    prefixes = draft_prefixes_for(str(draft_id))
    candidates: list[str] = []
    for prefix in prefixes:
        candidates.extend(await storage.list_prefix(prefix))
    storage_path = find_asset_under_prefixes(
        candidates,
        prefixes=prefixes,
        asset_id=str(asset_id),
    )
    if storage_path is None:
        storage_path = _draft_referenced_asset_path(draft, str(asset_id))
    if storage_path and await storage.exists(storage_path):
        await storage.delete(storage_path)


def _draft_referenced_asset_path(draft: PresentationPresetDraft, asset_id: str) -> str | None:
    """Resolve promoted/persisted asset paths still referenced by an approved draft."""
    config = draft.template_draft.get("config") if isinstance(draft.template_draft, dict) else None
    if not isinstance(config, dict):
        return None
    design = config.get("cover_design")
    if not isinstance(design, dict):
        return None
    candidates: list[dict] = []
    background = design.get("background")
    if isinstance(background, dict):
        candidates.append(background)
    assets = design.get("assets")
    if isinstance(assets, list):
        candidates.extend(item for item in assets if isinstance(item, dict))
    for item in candidates:
        if str(item.get("id") or "") != asset_id:
            continue
        path = item.get("storage_path")
        if not isinstance(path, str) or not path:
            continue
        pure = PurePosixPath(path)
        if pure.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
            continue
        if is_presentation_asset_path(path):
            return path
    return None


# --- Admin: defaults ---


@admin_router.get("/defaults", response_model=PresentationDefaults)
async def get_defaults_admin(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    return PresentationDefaults(**(await get_presentation_defaults(db)))


@admin_router.put("/defaults", response_model=PresentationDefaults)
async def put_defaults_admin(
    body: PresentationDefaultsUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    if (
        body.theme_id is None
        and body.style_id is None
        and body.template_id is None
        and "cover_template_id" not in body.model_fields_set
    ):
        raise HTTPException(status_code=400, detail="Provide at least one default id")
    result = await presentation_service.set_defaults(
        db,
        theme_id=body.theme_id,
        style_id=body.style_id,
        template_id=body.template_id,
        cover_template_id=body.cover_template_id,
        update_cover="cover_template_id" in body.model_fields_set,
    )
    return PresentationDefaults(**result)


# --- Admin themes ---


@admin_router.get("/themes", response_model=list[PresentationPresetDetail])
async def list_themes_admin(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    rows = await presentation_service.list_presets(db, "theme")
    return [_theme_to_detail(r) for r in rows]


@admin_router.post("/themes", response_model=PresentationPresetDetail, status_code=201)
async def create_theme(
    body: PresentationPresetCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    row = await presentation_service.create_preset(
        db,
        "theme",
        preset_id=body.id,
        name=body.name,
        description=body.description,
        config=body.config,
        is_active=body.is_active,
        is_default=body.is_default,
    )
    return _theme_to_detail(row)


@admin_router.patch("/themes/{preset_id}", response_model=PresentationPresetDetail)
async def update_theme(
    preset_id: str,
    body: PresentationPresetUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    row = await presentation_service.update_preset(
        db,
        "theme",
        preset_id,
        name=body.name,
        description=body.description,
        config=body.config,
        is_active=body.is_active,
    )
    return _theme_to_detail(row)


@admin_router.post("/themes/{preset_id}/set-default", response_model=PresentationPresetDetail)
async def set_theme_default(
    preset_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    row = await presentation_service.set_default(db, "theme", preset_id)
    return _theme_to_detail(row)


@admin_router.delete("/themes/{preset_id}", status_code=204)
async def delete_theme(
    preset_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    await presentation_service.delete_preset(db, "theme", preset_id)


@admin_router.get("/themes/{preset_id}/logo")
async def get_theme_logo(
    preset_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    data = await presentation_service.read_theme_logo_bytes(db, preset_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Logo not found")
    content, media_type = data
    return Response(content=content, media_type=media_type)


@admin_router.post("/themes/{preset_id}/logo", response_model=PresentationPresetDetail)
async def upload_theme_logo(
    preset_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    content = await file.read()
    try:
        row = await presentation_service.save_theme_logo(
            db,
            preset_id,
            content=content,
            filename=file.filename,
            content_type=file.content_type,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _theme_to_detail(row)


@admin_router.delete("/themes/{preset_id}/logo", response_model=PresentationPresetDetail)
async def delete_theme_logo(
    preset_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    row = await presentation_service.clear_theme_logo(db, preset_id)
    return _theme_to_detail(row)


# --- Admin styles ---


@admin_router.get("/styles", response_model=list[PresentationPresetDetail])
async def list_styles_admin(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    rows = await presentation_service.list_presets(db, "style")
    return [_style_to_detail(r) for r in rows]


@admin_router.post("/styles", response_model=PresentationPresetDetail, status_code=201)
async def create_style(
    body: PresentationPresetCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    row = await presentation_service.create_preset(
        db,
        "style",
        preset_id=body.id,
        name=body.name,
        description=body.description,
        config=body.config,
        is_active=body.is_active,
        is_default=body.is_default,
    )
    return _style_to_detail(row)


@admin_router.patch("/styles/{preset_id}", response_model=PresentationPresetDetail)
async def update_style(
    preset_id: str,
    body: PresentationPresetUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    row = await presentation_service.update_preset(
        db,
        "style",
        preset_id,
        name=body.name,
        description=body.description,
        config=body.config,
        is_active=body.is_active,
    )
    return _style_to_detail(row)


@admin_router.post("/styles/{preset_id}/set-default", response_model=PresentationPresetDetail)
async def set_style_default(
    preset_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    row = await presentation_service.set_default(db, "style", preset_id)
    return _style_to_detail(row)


@admin_router.delete("/styles/{preset_id}", status_code=204)
async def delete_style(
    preset_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    await presentation_service.delete_preset(db, "style", preset_id)


# --- Admin templates ---


@admin_router.get("/templates", response_model=list[PresentationPresetDetail])
async def list_templates_admin(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    rows = await presentation_service.list_presets(db, "template")
    return [_template_to_detail(r) for r in rows]


@admin_router.post("/templates", response_model=PresentationPresetDetail, status_code=201)
async def create_template(
    body: PresentationPresetCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    row = await presentation_service.create_preset(
        db,
        "template",
        preset_id=body.id,
        name=body.name,
        description=body.description,
        config=body.config,
        is_active=body.is_active,
        is_default=body.is_default,
    )
    return _template_to_detail(row)


@admin_router.patch("/templates/{preset_id}", response_model=PresentationPresetDetail)
async def update_template(
    preset_id: str,
    body: PresentationPresetUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    row = await presentation_service.update_preset(
        db,
        "template",
        preset_id,
        name=body.name,
        description=body.description,
        config=body.config,
        is_active=body.is_active,
    )
    return _template_to_detail(row)


@admin_router.post("/templates/{preset_id}/set-default", response_model=PresentationPresetDetail)
async def set_template_default(
    preset_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    row = await presentation_service.set_default(db, "template", preset_id)
    return _template_to_detail(row)


@admin_router.delete("/templates/{preset_id}", status_code=204)
async def delete_template(
    preset_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    await presentation_service.delete_preset(db, "template", preset_id)


@admin_router.post(
    "/templates/{preset_id}/assets",
    response_model=PresentationDraftAsset,
    status_code=201,
)
async def upload_presentation_template_asset(
    preset_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    await presentation_service.get_preset(db, "template", preset_id)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Asset file is empty")
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Asset exceeds the 20 MB limit")
    extension = Path(file.filename or "").suffix.lower()
    if extension not in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
        raise HTTPException(status_code=400, detail="Unsupported presentation asset type")
    asset_id = str(uuid.uuid4())
    storage_path = template_asset_path(preset_id, asset_id, extension)
    await get_storage_backend().save(storage_path, content)
    return PresentationDraftAsset(
        id=asset_id,
        storage_path=storage_path,
        filename=file.filename or f"{asset_id}{extension}",
        content_type=file.content_type,
        size_bytes=len(content),
    )


@admin_router.get("/templates/{preset_id}/assets/{asset_id}")
async def get_presentation_template_asset(
    preset_id: str,
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    row = await presentation_service.get_preset(db, "template", preset_id)
    storage = get_storage_backend()
    prefixes = template_prefixes_for(preset_id)
    candidates: list[str] = []
    for prefix in prefixes:
        candidates.extend(await storage.list_prefix(prefix))
    storage_path = find_asset_under_prefixes(
        candidates,
        prefixes=prefixes,
        asset_id=str(asset_id),
    )
    if storage_path is None:
        storage_path = _template_referenced_asset_path(row, str(asset_id))
    if storage_path is None:
        raise HTTPException(status_code=404, detail="Template asset not found")
    try:
        content = await storage.read(storage_path)
    except (FileNotFoundError, OSError):
        raise HTTPException(status_code=404, detail="Template asset not found") from None
    media_type = mimetypes.guess_type(storage_path)[0] or "application/octet-stream"
    return Response(content=content, media_type=media_type)


@admin_router.delete("/templates/{preset_id}/assets/{asset_id}", status_code=204)
async def delete_presentation_template_asset(
    preset_id: str,
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    row = await presentation_service.get_preset(db, "template", preset_id)
    storage = get_storage_backend()
    prefixes = template_prefixes_for(preset_id)
    candidates: list[str] = []
    for prefix in prefixes:
        candidates.extend(await storage.list_prefix(prefix))
    storage_path = find_asset_under_prefixes(
        candidates,
        prefixes=prefixes,
        asset_id=str(asset_id),
    )
    if storage_path is None:
        storage_path = _template_referenced_asset_path(row, str(asset_id))
    if storage_path and await storage.exists(storage_path):
        await storage.delete(storage_path)


def _template_referenced_asset_path(row: PresentationTemplate, asset_id: str) -> str | None:
    config = row.config if isinstance(row.config, dict) else {}
    design = config.get("cover_design")
    if not isinstance(design, dict):
        return None
    candidates: list[dict] = []
    background = design.get("background")
    if isinstance(background, dict):
        candidates.append(background)
    assets = design.get("assets")
    if isinstance(assets, list):
        candidates.extend(item for item in assets if isinstance(item, dict))
    for item in candidates:
        if str(item.get("id") or "") != asset_id:
            continue
        path = item.get("storage_path")
        if not isinstance(path, str) or not path:
            continue
        pure = PurePosixPath(path)
        if pure.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
            continue
        if is_presentation_asset_path(path):
            return path
    return None
