import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.calculation.schemas import RateCardSettings
from app.dependencies import get_db, require_admin
from app.models.rate_card import RateCard, RateCardVersion
from app.models.user import User
from app.schemas.rate_card import ActiveRateCardResponse, RateCardUpdate, RateCardVersionResponse

router = APIRouter(prefix="/admin/rate-cards", tags=["admin"])


def _validate_phase_percentages(settings: RateCardSettings) -> None:
    total = sum(phase.percentage for phase in settings.phases)
    if abs(total - 1.0) > 0.001:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Phase percentages must sum to 100% (got {total * 100:.1f}%)",
                "code": "INVALID_PHASE_SUM",
            },
        )


async def _get_active_rate_card(db: AsyncSession) -> RateCard | None:
    result = await db.execute(select(RateCard).where(RateCard.is_active.is_(True)))
    return result.scalar_one_or_none()


async def _get_latest_version(
    db: AsyncSession, rate_card_id: uuid.UUID
) -> RateCardVersion | None:
    result = await db.execute(
        select(RateCardVersion)
        .where(RateCardVersion.rate_card_id == rate_card_id)
        .order_by(RateCardVersion.version_number.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


@router.get("/active", response_model=ActiveRateCardResponse)
async def get_active_rate_card(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    rate_card = await _get_active_rate_card(db)
    if not rate_card:
        raise HTTPException(
            status_code=404,
            detail={"error": "No active rate card", "code": "RATE_CARD_NOT_FOUND"},
        )

    version = await _get_latest_version(db, rate_card.id)
    if not version:
        raise HTTPException(
            status_code=404,
            detail={"error": "Active rate card has no versions", "code": "RATE_CARD_NOT_FOUND"},
        )

    return ActiveRateCardResponse(
        id=rate_card.id,
        name=rate_card.name,
        is_active=rate_card.is_active,
        version_number=version.version_number,
        version_id=version.id,
        settings=version.settings,
        created_at=version.created_at,
    )


@router.put("", response_model=ActiveRateCardResponse)
async def update_rate_card(
    body: RateCardUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    _validate_phase_percentages(body.settings)

    rate_card = await _get_active_rate_card(db)
    if not rate_card:
        raise HTTPException(
            status_code=404,
            detail={"error": "No active rate card", "code": "RATE_CARD_NOT_FOUND"},
        )

    result = await db.execute(
        select(func.max(RateCardVersion.version_number)).where(
            RateCardVersion.rate_card_id == rate_card.id
        )
    )
    max_version = result.scalar_one_or_none() or 0

    version = RateCardVersion(
        rate_card_id=rate_card.id,
        version_number=max_version + 1,
        settings=body.settings.model_dump(),
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)

    return ActiveRateCardResponse(
        id=rate_card.id,
        name=rate_card.name,
        is_active=rate_card.is_active,
        version_number=version.version_number,
        version_id=version.id,
        settings=version.settings,
        created_at=version.created_at,
    )


@router.get("/versions", response_model=list[RateCardVersionResponse])
async def list_rate_card_versions(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    rate_card = await _get_active_rate_card(db)
    if not rate_card:
        raise HTTPException(
            status_code=404,
            detail={"error": "No active rate card", "code": "RATE_CARD_NOT_FOUND"},
        )

    result = await db.execute(
        select(RateCardVersion)
        .where(RateCardVersion.rate_card_id == rate_card.id)
        .order_by(RateCardVersion.version_number.desc())
    )
    return list(result.scalars().all())
