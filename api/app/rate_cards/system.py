import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rate_card import RateCard, RateCardVersion
from app.models.user import User
from app.rate_cards.defaults import DEFAULT_RATE_CARD_NAME, DEFAULT_RATE_CARD_SETTINGS
from app.rate_cards.service import create_rate_card_with_settings, get_latest_version_for_card


async def get_system_rate_card(db: AsyncSession) -> RateCard | None:
    result = await db.execute(
        select(RateCard).where(RateCard.is_system.is_(True)).order_by(RateCard.created_at.asc())
    )
    return result.scalars().first()


async def ensure_system_rate_card(db: AsyncSession, admin: User) -> RateCard:
    existing = await get_system_rate_card(db)
    if existing:
        if not existing.is_active:
            existing.is_active = True
        return existing

    rate_card, _version = await create_rate_card_with_settings(
        db,
        user=admin,
        name=DEFAULT_RATE_CARD_NAME,
        settings=DEFAULT_RATE_CARD_SETTINGS,
        activate=True,
    )
    rate_card.is_system = True
    await db.flush()
    return rate_card


async def attach_system_rate_card(db: AsyncSession, estimate) -> None:
    from app.models.estimate import Estimate

    if not isinstance(estimate, Estimate):
        raise TypeError("estimate must be an Estimate instance")

    if estimate.rate_card_id:
        return

    system_card = await get_system_rate_card(db)
    if not system_card:
        admin_row = await db.execute(
            select(User).where(User.is_admin.is_(True), User.is_active.is_(True)).limit(1)
        )
        admin = admin_row.scalar_one_or_none()
        if not admin:
            raise RuntimeError("No admin user available to seed system rate card")
        system_card = await ensure_system_rate_card(db, admin)

    version = await get_latest_version_for_card(db, system_card.id)
    estimate.rate_card_id = system_card.id
    estimate.rate_card_version_id = version.id
