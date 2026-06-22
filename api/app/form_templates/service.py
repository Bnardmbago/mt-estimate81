import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.estimates.form_fields import snapshot_fields
from app.form_templates.categories import (
    category_sort_key,
    languages_for_locale,
    validate_nature_of_work_category,
    validate_template_language,
)
from app.models.estimate import Estimate
from app.models.form_template import FormTemplate
from app.schemas.form_template import (
    FormTemplateCreate,
    FormTemplateOption,
    FormTemplateResponse,
    FormTemplateSummary,
    FormTemplateUpdate,
)


async def get_default_template(db: AsyncSession) -> FormTemplate:
    result = await db.execute(
        select(FormTemplate).where(FormTemplate.is_default.is_(True)).limit(1)
    )
    template = result.scalar_one_or_none()
    if template:
        return template

    result = await db.execute(select(FormTemplate).order_by(FormTemplate.created_at.asc()).limit(1))
    template = result.scalar_one_or_none()
    if template:
        return template

    raise HTTPException(
        status_code=500,
        detail={"error": "No form template configured", "code": "FORM_TEMPLATE_NOT_FOUND"},
    )


async def get_template_or_404(db: AsyncSession, template_id: uuid.UUID) -> FormTemplate:
    result = await db.execute(select(FormTemplate).where(FormTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(
            status_code=404,
            detail={"error": "Form template not found", "code": "FORM_TEMPLATE_NOT_FOUND"},
        )
    return template


async def resolve_template(
    db: AsyncSession,
    template_id: uuid.UUID | None,
) -> FormTemplate:
    if template_id is not None:
        return await get_template_or_404(db, template_id)
    return await get_default_template(db)


def template_to_response(template: FormTemplate) -> FormTemplateResponse:
    return FormTemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        fields=snapshot_fields(template.fields),
        nature_of_work_category=template.nature_of_work_category,
        language=template.language,
        is_default=template.is_default,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


def template_to_summary(template: FormTemplate) -> FormTemplateSummary:
    return FormTemplateSummary(
        id=template.id,
        name=template.name,
        description=template.description,
        nature_of_work_category=template.nature_of_work_category,
        language=template.language,
        is_default=template.is_default,
        field_count=len(snapshot_fields(template.fields)),
    )


def _build_template_query(
    *,
    locale: str | None = None,
    nature_of_work_category: str | None = None,
):
    query = select(FormTemplate)
    if locale is not None:
        query = query.where(FormTemplate.language.in_(languages_for_locale(locale)))
    if nature_of_work_category is not None:
        query = query.where(
            FormTemplate.nature_of_work_category
            == validate_nature_of_work_category(nature_of_work_category)
        )
    return query


def _sort_templates(templates: list[FormTemplate]) -> list[FormTemplate]:
    return sorted(
        templates,
        key=lambda template: (
            not template.is_default,
            category_sort_key(template.nature_of_work_category),
            template.name.lower(),
        ),
    )


async def list_templates(db: AsyncSession) -> list[FormTemplateSummary]:
    result = await db.execute(select(FormTemplate))
    templates = _sort_templates(list(result.scalars().all()))
    return [template_to_summary(template) for template in templates]


async def list_template_options(
    db: AsyncSession,
    *,
    locale: str | None = None,
    nature_of_work_category: str | None = None,
) -> list[FormTemplateOption]:
    result = await db.execute(
        _build_template_query(
            locale=locale,
            nature_of_work_category=nature_of_work_category,
        )
    )
    templates = _sort_templates(list(result.scalars().all()))
    return [
        FormTemplateOption(
            id=template.id,
            name=template.name,
            nature_of_work_category=template.nature_of_work_category,
            language=template.language,
            is_default=template.is_default,
        )
        for template in templates
    ]


async def get_template_detail(db: AsyncSession, template_id: uuid.UUID) -> FormTemplateResponse:
    template = await get_template_or_404(db, template_id)
    return template_to_response(template)


async def _clear_default_flag(db: AsyncSession, except_id: uuid.UUID | None = None) -> None:
    query = update(FormTemplate).where(FormTemplate.is_default.is_(True))
    if except_id is not None:
        query = query.where(FormTemplate.id != except_id)
    await db.execute(query.values(is_default=False))


async def create_template(db: AsyncSession, body: FormTemplateCreate) -> FormTemplateResponse:
    existing = await db.execute(select(FormTemplate).where(FormTemplate.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail={"error": "Template name already exists", "code": "FORM_TEMPLATE_NAME_EXISTS"},
        )

    fields = snapshot_fields(body.fields)
    if body.is_default:
        await _clear_default_flag(db)

    template = FormTemplate(
        name=body.name,
        description=body.description,
        fields=fields,
        nature_of_work_category=body.nature_of_work_category,
        language=body.language,
        is_default=body.is_default,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template_to_response(template)


async def update_template(
    db: AsyncSession,
    template_id: uuid.UUID,
    body: FormTemplateUpdate,
) -> FormTemplateResponse:
    template = await get_template_or_404(db, template_id)

    if body.name and body.name != template.name:
        existing = await db.execute(select(FormTemplate).where(FormTemplate.name == body.name))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail={"error": "Template name already exists", "code": "FORM_TEMPLATE_NAME_EXISTS"},
            )
        template.name = body.name

    if body.description is not None:
        template.description = body.description

    if body.fields is not None:
        template.fields = snapshot_fields(body.fields)

    if body.nature_of_work_category is not None:
        template.nature_of_work_category = body.nature_of_work_category

    if body.language is not None:
        template.language = body.language

    if body.is_default is True:
        await _clear_default_flag(db, except_id=template.id)
        template.is_default = True
    elif body.is_default is False and template.is_default:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Cannot unset the only default template",
                "code": "FORM_TEMPLATE_DEFAULT_REQUIRED",
            },
        )

    await db.commit()
    await db.refresh(template)
    return template_to_response(template)


async def delete_template(db: AsyncSession, template_id: uuid.UUID) -> None:
    template = await get_template_or_404(db, template_id)
    if template.is_default:
        raise HTTPException(
            status_code=400,
            detail={"error": "Cannot delete the default template", "code": "FORM_TEMPLATE_DEFAULT_DELETE"},
        )

    usage = await db.execute(
        select(func.count()).select_from(Estimate).where(Estimate.form_template_id == template.id)
    )
    if int(usage.scalar_one()) > 0:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Template is in use by existing estimates",
                "code": "FORM_TEMPLATE_IN_USE",
            },
        )

    await db.delete(template)
    await db.commit()


async def duplicate_template(db: AsyncSession, template_id: uuid.UUID) -> FormTemplateResponse:
    source = await get_template_or_404(db, template_id)
    base_name = f"{source.name} (copy)"
    name = base_name
    suffix = 2
    while True:
        existing = await db.execute(select(FormTemplate).where(FormTemplate.name == name))
        if not existing.scalar_one_or_none():
            break
        name = f"{base_name} {suffix}"
        suffix += 1

    duplicate = FormTemplate(
        name=name,
        description=source.description,
        fields=snapshot_fields(source.fields),
        nature_of_work_category=source.nature_of_work_category,
        language=source.language,
        is_default=False,
    )
    db.add(duplicate)
    await db.commit()
    await db.refresh(duplicate)
    return template_to_response(duplicate)
