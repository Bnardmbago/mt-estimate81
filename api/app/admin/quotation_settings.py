from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.quotation_notes_config import (
    get_quotation_notes_config,
    update_quotation_notes_config,
)
from app.dependencies import get_db, require_admin
from app.models.user import User

router = APIRouter(prefix="/admin/quotation-settings", tags=["admin"])


class QuotationSettingsResponse(BaseModel):
    special_notes_title_ja: str
    special_notes_title_en: str
    special_notes_body_ja: str
    special_notes_body_en: str


class QuotationSettingsUpdate(BaseModel):
    special_notes_title_ja: str | None = Field(default=None, max_length=200)
    special_notes_title_en: str | None = Field(default=None, max_length=200)
    special_notes_body_ja: str | None = Field(default=None, max_length=4000)
    special_notes_body_en: str | None = Field(default=None, max_length=4000)


def _to_response(config) -> QuotationSettingsResponse:
    return QuotationSettingsResponse(
        special_notes_title_ja=config.title_ja,
        special_notes_title_en=config.title_en,
        special_notes_body_ja=config.body_ja,
        special_notes_body_en=config.body_en,
    )


@router.get("", response_model=QuotationSettingsResponse)
async def get_quotation_settings(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    config = await get_quotation_notes_config(db)
    return _to_response(config)


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
        )
    ):
        raise HTTPException(
            status_code=400,
            detail={"error": "At least one field must be provided", "code": "INVALID_SETTINGS"},
        )

    config = await update_quotation_notes_config(
        db,
        title_ja=body.special_notes_title_ja,
        title_en=body.special_notes_title_en,
        body_ja=body.special_notes_body_ja,
        body_en=body.special_notes_body_en,
    )
    return _to_response(config)
