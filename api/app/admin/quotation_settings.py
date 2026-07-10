from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.quotation_company_config import (
    clear_quotation_logo,
    get_quotation_company_config,
    read_quotation_logo_bytes,
    save_quotation_logo,
    update_quotation_company_config,
)
from app.admin.quotation_notes_config import (
    get_quotation_notes_config,
    update_quotation_notes_config,
)
from app.exports.quotation_number import (
    preview_next_registration_number,
    resolved_contact_person,
    set_registration_sequence_from_value,
)
from app.dependencies import get_db, require_admin
from app.models.system_config import SystemConfig
from app.models.user import User

router = APIRouter(prefix="/admin/quotation-settings", tags=["admin"])


class QuotationSettingsResponse(BaseModel):
    special_notes_title_ja: str
    special_notes_title_en: str
    special_notes_body_ja: str
    special_notes_body_en: str
    invoice_registration_number: str
    contact_person: str
    company_postal_code: str
    company_address: str
    company_tel: str
    company_email: str
    bank_details_ja: str
    bank_details_en: str
    has_custom_logo: bool
    logo_url: str


class QuotationSettingsUpdate(BaseModel):
    special_notes_title_ja: str | None = Field(default=None, max_length=200)
    special_notes_title_en: str | None = Field(default=None, max_length=200)
    special_notes_body_ja: str | None = Field(default=None, max_length=4000)
    special_notes_body_en: str | None = Field(default=None, max_length=4000)
    invoice_registration_number: str | None = Field(default=None, max_length=32)
    contact_person: str | None = Field(default=None, max_length=255)
    company_postal_code: str | None = Field(default=None, max_length=32)
    company_address: str | None = Field(default=None, max_length=1000)
    company_tel: str | None = Field(default=None, max_length=64)
    company_email: str | None = Field(default=None, max_length=255)
    bank_details_ja: str | None = Field(default=None, max_length=2000)
    bank_details_en: str | None = Field(default=None, max_length=2000)


async def _get_config_row(db: AsyncSession) -> SystemConfig:
    from sqlalchemy import select

    result = await db.execute(select(SystemConfig).where(SystemConfig.id == 1))
    row = result.scalar_one_or_none()
    if row is None:
        row = SystemConfig(id=1)
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


def _to_response(
    notes_config,
    company_config,
    next_registration_number: str,
    contact_person: str,
) -> QuotationSettingsResponse:
    return QuotationSettingsResponse(
        special_notes_title_ja=notes_config.title_ja,
        special_notes_title_en=notes_config.title_en,
        special_notes_body_ja=notes_config.body_ja,
        special_notes_body_en=notes_config.body_en,
        invoice_registration_number=next_registration_number,
        contact_person=contact_person,
        company_postal_code=company_config.postal_code,
        company_address=company_config.address,
        company_tel=company_config.tel,
        company_email=company_config.email,
        bank_details_ja=company_config.bank_details_ja,
        bank_details_en=company_config.bank_details_en,
        has_custom_logo=company_config.has_custom_logo,
        logo_url="/admin/quotation-settings/logo",
    )


@router.get("", response_model=QuotationSettingsResponse)
async def get_quotation_settings(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    notes_config = await get_quotation_notes_config(db)
    company_config = await get_quotation_company_config(db)
    system_config = await _get_config_row(db)
    return _to_response(
        notes_config,
        company_config,
        preview_next_registration_number(system_config),
        resolved_contact_person(system_config),
    )


@router.patch("", response_model=QuotationSettingsResponse)
async def patch_quotation_settings(
    body: QuotationSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    if all(
        value is None
        for value in (
            body.special_notes_title_ja,
            body.special_notes_title_en,
            body.special_notes_body_ja,
            body.special_notes_body_en,
            body.invoice_registration_number,
            body.contact_person,
            body.company_postal_code,
            body.company_address,
            body.company_tel,
            body.company_email,
            body.bank_details_ja,
            body.bank_details_en,
        )
    ):
        raise HTTPException(
            status_code=400,
            detail={"error": "At least one field must be provided", "code": "INVALID_SETTINGS"},
        )

    notes_config = await update_quotation_notes_config(
        db,
        title_ja=body.special_notes_title_ja,
        title_en=body.special_notes_title_en,
        body_ja=body.special_notes_body_ja,
        body_en=body.special_notes_body_en,
    )

    company_fields = any(
        value is not None
        for value in (
            body.company_postal_code,
            body.company_address,
            body.company_tel,
            body.company_email,
            body.bank_details_ja,
            body.bank_details_en,
        )
    )
    if company_fields:
        company_config = await update_quotation_company_config(
            db,
            postal_code=body.company_postal_code,
            address=body.company_address,
            tel=body.company_tel,
            email=body.company_email,
            bank_details_ja=body.bank_details_ja,
            bank_details_en=body.bank_details_en,
        )
    else:
        company_config = await get_quotation_company_config(db)

    system_config = await _get_config_row(db)
    system_fields_updated = False
    if body.invoice_registration_number is not None:
        try:
            set_registration_sequence_from_value(
                system_config,
                body.invoice_registration_number,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail={"error": str(exc), "code": "INVALID_REGISTRATION_NUMBER"},
            ) from exc
        system_fields_updated = True
    if body.contact_person is not None:
        system_config.quotation_contact_person = body.contact_person.strip() or None
        system_fields_updated = True
    if system_fields_updated:
        await db.commit()

    system_config = await _get_config_row(db)
    return _to_response(
        notes_config,
        company_config,
        preview_next_registration_number(system_config),
        resolved_contact_person(system_config),
    )


@router.get("/logo")
async def get_quotation_logo(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    try:
        content, media_type = await read_quotation_logo_bytes(db)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": str(exc), "code": "LOGO_NOT_FOUND"},
        ) from exc
    return Response(content=content, media_type=media_type)


@router.post("/logo", response_model=QuotationSettingsResponse)
async def upload_quotation_logo(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    content = await file.read()
    try:
        company_config = await save_quotation_logo(
            db,
            content=content,
            filename=file.filename,
            content_type=file.content_type,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": str(exc), "code": "INVALID_LOGO"},
        ) from exc

    notes_config = await get_quotation_notes_config(db)
    system_config = await _get_config_row(db)
    return _to_response(
        notes_config,
        company_config,
        preview_next_registration_number(system_config),
        resolved_contact_person(system_config),
    )


@router.delete("/logo", response_model=QuotationSettingsResponse)
async def delete_quotation_logo(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    company_config = await clear_quotation_logo(db)
    notes_config = await get_quotation_notes_config(db)
    system_config = await _get_config_row(db)
    return _to_response(
        notes_config,
        company_config,
        preview_next_registration_number(system_config),
        resolved_contact_person(system_config),
    )
