import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.calculation.schemas import RateCardSettings
from app.dependencies import get_db, require_admin
from app.models.rate_card import RateCard, RateCardVersion
from app.models.user import User
from app.rate_cards.normalize import normalize_settings_dict
from app.rate_cards.system import ensure_system_rate_card, get_system_rate_card
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


async def _get_admin_system_rate_card(db: AsyncSession, admin: User) -> RateCard:
    rate_card = await get_system_rate_card(db)
    if rate_card:
        return rate_card
    rate_card = await ensure_system_rate_card(db, admin)
    await db.flush()
    return rate_card


def _to_active_response(rate_card: RateCard, version: RateCardVersion) -> ActiveRateCardResponse:
    return ActiveRateCardResponse(
        id=rate_card.id,
        name=rate_card.name,
        is_active=rate_card.is_active,
        is_system=rate_card.is_system,
        version_number=version.version_number,
        version_id=version.id,
        version_label=version.label,
        settings=normalize_settings_dict(version.settings),
        created_at=version.created_at,
    )


@router.get("/active", response_model=ActiveRateCardResponse)
async def get_active_rate_card(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    rate_card = await _get_admin_system_rate_card(db, admin)

    version = await _get_latest_version(db, rate_card.id)
    if not version:
        raise HTTPException(
            status_code=404,
            detail={"error": "System rate card has no versions", "code": "RATE_CARD_NOT_FOUND"},
        )

    return _to_active_response(rate_card, version)


@router.put("", response_model=ActiveRateCardResponse)
async def update_rate_card(
    body: RateCardUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    _validate_phase_percentages(body.settings)

    rate_card = await _get_admin_system_rate_card(db, admin)
    if body.name and not rate_card.is_system:
        rate_card.name = body.name.strip()

    result = await db.execute(
        select(func.max(RateCardVersion.version_number)).where(
            RateCardVersion.rate_card_id == rate_card.id
        )
    )
    max_version = result.scalar_one_or_none() or 0

    version = RateCardVersion(
        rate_card_id=rate_card.id,
        version_number=max_version + 1,
        label=body.version_label.strip() if body.version_label else None,
        settings=normalize_settings_dict(body.settings.model_dump()),
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)

    return _to_active_response(rate_card, version)


@router.get("/versions", response_model=list[RateCardVersionResponse])
async def list_rate_card_versions(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    rate_card = await _get_admin_system_rate_card(db, admin)

    result = await db.execute(
        select(RateCardVersion)
        .where(RateCardVersion.rate_card_id == rate_card.id)
        .order_by(RateCardVersion.version_number.desc())
    )
    return list(result.scalars().all())
