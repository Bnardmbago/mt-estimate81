from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.discount_config import get_estimate_discount_rate, update_estimate_discount_rate
from app.dependencies import get_db, require_admin
from app.models.user import User

router = APIRouter(prefix="/admin/discount-settings", tags=["admin"])


class DiscountSettingsResponse(BaseModel):
    estimate_discount_rate: float = Field(ge=0.0, le=1.0)


class DiscountSettingsUpdate(BaseModel):
    estimate_discount_rate: float = Field(ge=0.0, le=1.0)


@router.get("", response_model=DiscountSettingsResponse)
async def get_discount_settings(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    rate = await get_estimate_discount_rate(db)
    return DiscountSettingsResponse(estimate_discount_rate=rate)


@router.patch("", response_model=DiscountSettingsResponse)
async def patch_discount_settings(
    body: DiscountSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    try:
        rate = await update_estimate_discount_rate(db, body.estimate_discount_rate)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": str(exc), "code": "INVALID_DISCOUNT_RATE"},
        ) from exc
    return DiscountSettingsResponse(estimate_discount_rate=rate)
