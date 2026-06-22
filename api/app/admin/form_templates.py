import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, require_admin
from app.form_templates import service
from app.models.user import User
from app.schemas.form_template import (
    FormTemplateCreate,
    FormTemplateOption,
    FormTemplateResponse,
    FormTemplateSummary,
    FormTemplateUpdate,
)

router = APIRouter(prefix="/admin/form-templates", tags=["admin"])


@router.get("", response_model=list[FormTemplateSummary])
async def list_form_templates(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    return await service.list_templates(db)


@router.post("", response_model=FormTemplateResponse, status_code=201)
async def create_form_template(
    body: FormTemplateCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    return await service.create_template(db, body)


@router.get("/{template_id}", response_model=FormTemplateResponse)
async def get_form_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    return await service.get_template_detail(db, template_id)


@router.patch("/{template_id}", response_model=FormTemplateResponse)
async def update_form_template(
    template_id: uuid.UUID,
    body: FormTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    return await service.update_template(db, template_id, body)


@router.delete("/{template_id}", status_code=204)
async def delete_form_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    await service.delete_template(db, template_id)


@router.post("/{template_id}/duplicate", response_model=FormTemplateResponse, status_code=201)
async def duplicate_form_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    return await service.duplicate_template(db, template_id)


public_router = APIRouter(prefix="/form-templates", tags=["form-templates"])


@public_router.get("/options", response_model=list[FormTemplateOption])
async def list_form_template_options(
    locale: str | None = None,
    nature_of_work_category: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await service.list_template_options(
        db,
        locale=locale,
        nature_of_work_category=nature_of_work_category,
    )
