import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.calculation.development_approach import DevelopmentApproach
from app.models.rate_card import RateCard, RateCardVersion
from app.models.user import User
from app.rate_cards.access import require_rate_card_access
from app.rate_cards.normalize import normalize_settings_dict
from app.schemas.rate_card import RateCardOption, RateCardVersionOption


async def get_active_rate_card(db: AsyncSession, user: User) -> RateCard | None:
    query = select(RateCard).where(RateCard.is_active.is_(True))
    if not user.is_admin:
        query = query.where(RateCard.created_by == user.id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def deactivate_all_rate_cards(db: AsyncSession, user: User) -> None:
    result = await db.execute(select(RateCard))
    for card in result.scalars():
        if user.is_admin or card.created_by == user.id:
            card.is_active = False


async def set_active_rate_card(
    db: AsyncSession,
    rate_card_id: uuid.UUID,
    user: User,
) -> RateCard:
    rate_card = await get_rate_card_for_user(db, rate_card_id, user)
    await deactivate_all_rate_cards(db, user)
    rate_card.is_active = True
    return rate_card


async def count_rate_cards_for_user(db: AsyncSession, user: User) -> int:
    query = select(func.count()).select_from(RateCard)
    if not user.is_admin:
        query = query.where(RateCard.created_by == user.id)
    result = await db.execute(query)
    return int(result.scalar_one())


async def create_rate_card_with_settings(
    db: AsyncSession,
    *,
    user: User,
    name: str,
    settings: dict,
    activate: bool,
) -> tuple[RateCard, RateCardVersion]:
    from app.calculation.schemas import RateCardSettings

    normalized = normalize_settings_dict(settings)
    validated = RateCardSettings.model_validate(normalized)
    total = sum(phase.percentage for phase in validated.phases)
    if abs(total - 1.0) > 0.001:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Phase percentages must sum to 100% (got {total * 100:.1f}%)",
                "code": "INVALID_PHASE_SUM",
            },
        )

    if activate:
        await deactivate_all_rate_cards(db, user)

    card = RateCard(
        name=name.strip(),
        is_active=activate,
        created_by=user.id,
    )
    db.add(card)
    await db.flush()

    version = RateCardVersion(
        rate_card_id=card.id,
        version_number=1,
        settings=normalize_settings_dict(validated.model_dump()),
    )
    db.add(version)
    await db.flush()
    return card, version


async def list_rate_card_options(db: AsyncSession, user: User) -> list[RateCardOption]:
    query = select(RateCard).order_by(RateCard.name.asc())
    if not user.is_admin:
        query = query.where(RateCard.created_by == user.id)
    result = await db.execute(query)
    options: list[RateCardOption] = []
    for card in result.scalars().all():
        version = await get_latest_version_for_card(db, card.id)
        normalized = normalize_settings_dict(version.settings)
        approach_raw = normalized.get("development_approach", DevelopmentApproach.TRADITIONAL.value)
        options.append(
            RateCardOption(
                id=card.id,
                name=card.name,
                is_active=card.is_active,
                development_approach=DevelopmentApproach(approach_raw),
            )
        )
    return options


async def validate_rate_card_exists(db: AsyncSession, card_id: uuid.UUID) -> RateCard:
    card = await db.get(RateCard, card_id)
    if not card:
        raise HTTPException(
            status_code=404,
            detail={"error": "Rate card not found", "code": "RATE_CARD_NOT_FOUND"},
        )
    return card


async def get_rate_card_for_user(
    db: AsyncSession,
    card_id: uuid.UUID,
    user: User,
) -> RateCard:
    card = await validate_rate_card_exists(db, card_id)
    require_rate_card_access(card, user)
    return card


async def get_latest_version_for_card(
    db: AsyncSession,
    card_id: uuid.UUID,
) -> RateCardVersion:
    await validate_rate_card_exists(db, card_id)
    result = await db.execute(
        select(RateCardVersion)
        .where(RateCardVersion.rate_card_id == card_id)
        .order_by(RateCardVersion.version_number.desc())
        .limit(1)
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(
            status_code=404,
            detail={"error": "Rate card has no versions", "code": "RATE_CARD_NOT_FOUND"},
        )
    return version


async def get_rate_card_roles(
    db: AsyncSession,
    card_id: uuid.UUID,
    user: User,
) -> list[dict] | None:
    await get_rate_card_for_user(db, card_id, user)
    version = await get_latest_version_for_card(db, card_id)
    roles = version.settings.get("roles")
    return roles if isinstance(roles, list) else None


async def list_active_rate_card_version_options(
    db: AsyncSession,
    user: User,
) -> list[RateCardVersionOption]:
    rate_card = await get_active_rate_card(db, user)
    if not rate_card:
        return []

    result = await db.execute(
        select(RateCardVersion)
        .where(RateCardVersion.rate_card_id == rate_card.id)
        .order_by(RateCardVersion.version_number.desc())
    )
    return [
        RateCardVersionOption(
            id=version.id,
            version_number=version.version_number,
            label=version.label,
            rate_card_name=rate_card.name,
        )
        for version in result.scalars().all()
    ]


async def get_version_for_active_rate_card(
    db: AsyncSession,
    version_id: uuid.UUID,
    user: User,
) -> RateCardVersion:
    rate_card = await get_active_rate_card(db, user)
    if not rate_card:
        raise HTTPException(
            status_code=404,
            detail={"error": "No active rate card", "code": "RATE_CARD_NOT_FOUND"},
        )

    result = await db.execute(
        select(RateCardVersion).where(
            RateCardVersion.id == version_id,
            RateCardVersion.rate_card_id == rate_card.id,
        )
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(
            status_code=404,
            detail={"error": "Rate card version not found", "code": "RATE_CARD_VERSION_NOT_FOUND"},
        )
    return version
