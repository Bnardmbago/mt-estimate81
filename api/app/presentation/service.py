"""CRUD and catalog helpers for presentation presets."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, TypeVar

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.presentation import PresentationStyle, PresentationTemplate, PresentationTheme
from app.presentation.resolver import get_presentation_defaults
from app.storage.factory import get_storage_backend

CatalogKind = Literal["theme", "style", "template"]

ModelT = TypeVar("ModelT", PresentationTheme, PresentationStyle, PresentationTemplate)

_MODEL: dict[CatalogKind, type] = {
    "theme": PresentationTheme,
    "style": PresentationStyle,
    "template": PresentationTemplate,
}

LOGO_STORAGE_PREFIX = "system/presentation-themes"
MAX_LOGO_BYTES = 2 * 1024 * 1024
ALLOWED_LOGO_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/svg+xml", "image/webp"}


def _model(kind: CatalogKind):
    return _MODEL[kind]


async def list_presets(
    db: AsyncSession,
    kind: CatalogKind,
    *,
    active_only: bool = False,
) -> list[Any]:
    model = _model(kind)
    stmt = select(model).order_by(model.name)
    if active_only:
        stmt = stmt.where(model.is_active.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_preset(db: AsyncSession, kind: CatalogKind, preset_id: str) -> Any:
    model = _model(kind)
    result = await db.execute(select(model).where(model.id == preset_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail=f"{kind} '{preset_id}' not found")
    return row


async def create_preset(
    db: AsyncSession,
    kind: CatalogKind,
    *,
    preset_id: str,
    name: str,
    description: str | None,
    config: dict,
    is_active: bool = True,
    is_default: bool = False,
) -> Any:
    model = _model(kind)
    existing = await db.execute(select(model).where(model.id == preset_id))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail=f"{kind} id '{preset_id}' already exists")
    row = model(
        id=preset_id,
        name=name,
        description=description,
        config=config or {},
        is_active=is_active,
        is_default=False,
        updated_at=datetime.utcnow(),
    )
    db.add(row)
    await db.flush()
    if is_default:
        await set_default(db, kind, preset_id)
    else:
        await db.commit()
        await db.refresh(row)
    return await get_preset(db, kind, preset_id)


async def update_preset(
    db: AsyncSession,
    kind: CatalogKind,
    preset_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
    config: dict | None = None,
    is_active: bool | None = None,
) -> Any:
    row = await get_preset(db, kind, preset_id)
    if is_active is False and row.is_default:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot deactivate the default {kind}; promote another preset first",
        )
    if name is not None:
        row.name = name
    if description is not None:
        row.description = description
    if config is not None:
        row.config = config
    if is_active is not None:
        row.is_active = is_active
    row.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(row)
    return row


async def set_default(db: AsyncSession, kind: CatalogKind, preset_id: str) -> Any:
    model = _model(kind)
    row = await get_preset(db, kind, preset_id)
    if not row.is_active:
        raise HTTPException(status_code=400, detail=f"Cannot set inactive {kind} as default")
    await db.execute(update(model).values(is_default=False))
    row.is_default = True
    row.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(row)
    return row


async def set_defaults(
    db: AsyncSession,
    *,
    theme_id: str | None = None,
    style_id: str | None = None,
    template_id: str | None = None,
    cover_template_id: str | None = None,
    update_cover: bool = False,
) -> dict[str, str | None]:
    if theme_id:
        await set_default(db, "theme", theme_id)
    if style_id:
        await set_default(db, "style", style_id)
    if template_id:
        await set_default(db, "template", template_id)
    if update_cover:
        await set_default_cover_template(db, cover_template_id)
    return await get_presentation_defaults(db)


async def set_default_cover_template(
    db: AsyncSession,
    cover_template_id: str | None,
) -> None:
    from app.models.system_config import SystemConfig

    normalized = (cover_template_id or "").strip() or None
    if normalized:
        row = await get_preset(db, "template", normalized)
        if not row.is_active:
            raise HTTPException(
                status_code=400,
                detail="Cannot set inactive cover template as default",
            )
        config = row.config if isinstance(row.config, dict) else {}
        if not config.get("cover"):
            raise HTTPException(
                status_code=400,
                detail="Default cover must be a template with cover enabled",
            )
    result = await db.execute(select(SystemConfig).where(SystemConfig.id == 1))
    config_row = result.scalar_one_or_none()
    if config_row is None:
        config_row = SystemConfig(id=1)
        db.add(config_row)
        await db.flush()
    config_row.presentation_default_cover_template_id = normalized
    await db.commit()


async def delete_preset(db: AsyncSession, kind: CatalogKind, preset_id: str) -> None:
    row = await get_preset(db, kind, preset_id)
    if row.is_default:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete the default {kind}; promote another preset first",
        )
    if kind == "theme" and getattr(row, "logo_storage_path", None):
        storage = get_storage_backend()
        path = row.logo_storage_path
        if path and await storage.exists(path):
            await storage.delete(path)
    await db.delete(row)
    await db.commit()


def _logo_extension(filename: str | None, content_type: str | None) -> str:
    if filename and "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext in {"png", "jpg", "jpeg", "svg", "webp"}:
            return "jpg" if ext == "jpeg" else ext
    if content_type == "image/png":
        return "png"
    if content_type in {"image/jpeg", "image/jpg"}:
        return "jpg"
    if content_type == "image/svg+xml":
        return "svg"
    if content_type == "image/webp":
        return "webp"
    return "png"


async def save_theme_logo(
    db: AsyncSession,
    theme_id: str,
    *,
    content: bytes,
    filename: str | None,
    content_type: str | None,
) -> PresentationTheme:
    if not content:
        raise HTTPException(status_code=400, detail="Logo file is empty")
    if len(content) > MAX_LOGO_BYTES:
        raise HTTPException(status_code=400, detail="Logo file must be 2MB or smaller")
    if content_type and content_type not in ALLOWED_LOGO_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported logo content type")

    theme = await get_preset(db, "theme", theme_id)
    extension = _logo_extension(filename, content_type)
    storage_path = f"{LOGO_STORAGE_PREFIX}/{theme_id}.{extension}"
    storage = get_storage_backend()
    previous = (theme.logo_storage_path or "").strip()
    await storage.save(storage_path, content)
    theme.logo_storage_path = storage_path
    theme.updated_at = datetime.utcnow()
    await db.commit()
    if previous and previous != storage_path and await storage.exists(previous):
        await storage.delete(previous)
    await db.refresh(theme)
    return theme


async def clear_theme_logo(db: AsyncSession, theme_id: str) -> PresentationTheme:
    theme = await get_preset(db, "theme", theme_id)
    path = (theme.logo_storage_path or "").strip()
    if path:
        storage = get_storage_backend()
        if await storage.exists(path):
            await storage.delete(path)
    theme.logo_storage_path = None
    theme.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(theme)
    return theme


async def read_theme_logo_bytes(db: AsyncSession, theme_id: str) -> tuple[bytes, str] | None:
    theme = await get_preset(db, "theme", theme_id)
    path = (theme.logo_storage_path or "").strip()
    if not path:
        return None
    storage = get_storage_backend()
    if not await storage.exists(path):
        return None
    content = await storage.read(path)
    if path.endswith(".svg"):
        return content, "image/svg+xml"
    if path.endswith(".jpg") or path.endswith(".jpeg"):
        return content, "image/jpeg"
    if path.endswith(".webp"):
        return content, "image/webp"
    return content, "image/png"


async def assert_preset_ids_exist(
    db: AsyncSession,
    *,
    theme_id: str | None = None,
    style_id: str | None = None,
    template_id: str | None = None,
    cover_template_id: str | None = None,
) -> None:
    """Hard-fail when client sends an ID that never existed (malformed/unknown)."""
    if theme_id:
        result = await db.execute(select(PresentationTheme).where(PresentationTheme.id == theme_id))
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=400, detail=f"Unknown theme_id '{theme_id}'")
    if style_id:
        result = await db.execute(select(PresentationStyle).where(PresentationStyle.id == style_id))
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=400, detail=f"Unknown style_id '{style_id}'")
    if template_id:
        result = await db.execute(
            select(PresentationTemplate).where(PresentationTemplate.id == template_id)
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=400, detail=f"Unknown template_id '{template_id}'")
    if cover_template_id:
        result = await db.execute(
            select(PresentationTemplate).where(PresentationTemplate.id == cover_template_id)
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown cover_template_id '{cover_template_id}'",
            )
