from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.discount_config import (
    get_estimate_discount_rate,
    get_estimate_markup_rate,
    update_estimate_discount_rate,
    update_estimate_markup_rate,
)
from app.dependencies import get_db, require_admin
from app.models.user import User

router = APIRouter(prefix="/admin/discount-settings", tags=["admin"])


class DiscountSettingsResponse(BaseModel):
    estimate_discount_rate: float = Field(ge=0.0, le=1.0)
    estimate_markup_rate: float = Field(ge=0.0, le=1.0)


class DiscountSettingsUpdate(BaseModel):
    estimate_discount_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    estimate_markup_rate: float | None = Field(default=None, ge=0.0, le=1.0)


@router.get("", response_model=DiscountSettingsResponse)
async def get_discount_settings(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    discount_rate = await get_estimate_discount_rate(db)
    markup_rate = await get_estimate_markup_rate(db)
    return DiscountSettingsResponse(
        estimate_discount_rate=discount_rate,
        estimate_markup_rate=markup_rate,
    )


@router.patch("", response_model=DiscountSettingsResponse)
async def patch_discount_settings(
    body: DiscountSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    if body.estimate_discount_rate is None and body.estimate_markup_rate is None:
        raise HTTPException(
            status_code=400,
            detail={"error": "At least one rate must be provided", "code": "INVALID_SETTINGS"},
        )

    discount_rate = await get_estimate_discount_rate(db)
    markup_rate = await get_estimate_markup_rate(db)

    try:
        if body.estimate_discount_rate is not None:
            discount_rate = await update_estimate_discount_rate(db, body.estimate_discount_rate)
        if body.estimate_markup_rate is not None:
            markup_rate = await update_estimate_markup_rate(db, body.estimate_markup_rate)
    except ValueError as exc:
        code = (
            "INVALID_MARKUP_RATE"
            if "markup" in str(exc)
            else "INVALID_DISCOUNT_RATE"
        )
        raise HTTPException(
            status_code=400,
            detail={"error": str(exc), "code": code},
        ) from exc

    return DiscountSettingsResponse(
        estimate_discount_rate=discount_rate,
        estimate_markup_rate=markup_rate,
    )
