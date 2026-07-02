import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rate_card import RateCard, RateCardVersion
from app.models.user import User
from app.rate_cards.defaults import DEFAULT_RATE_CARD_NAME, DEFAULT_RATE_CARD_SETTINGS
from app.rate_cards.normalize import normalize_settings_dict
from app.rate_cards.service import create_rate_card_with_settings, get_latest_version_for_card


def system_rate_card_settings_drifted(settings: dict | None) -> bool:
    if not settings:
        return True
    normalized = normalize_settings_dict(settings)
    defaults = normalize_settings_dict(DEFAULT_RATE_CARD_SETTINGS)
    if normalized.get("development_approach") != defaults.get("development_approach"):
        return True
    current_roles = normalized.get("roles") or []
    default_roles = defaults.get("roles") or []
    if len(current_roles) != len(default_roles):
        return True
    current_names = {str(role.get("name", "")).strip() for role in current_roles}
    default_names = {str(role.get("name", "")).strip() for role in default_roles}
    return current_names != default_names


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
        existing.name = DEFAULT_RATE_CARD_NAME
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


async def sync_system_rate_card_from_defaults(db: AsyncSession, *, admin: User) -> RateCard:
    rate_card = await ensure_system_rate_card(db, admin)
    rate_card.is_system = True
    rate_card.is_active = True
    rate_card.name = DEFAULT_RATE_CARD_NAME

    latest = await get_latest_version_for_card(db, rate_card.id)
    if not system_rate_card_settings_drifted(latest.settings):
        return rate_card

    max_version = await db.scalar(
        select(func.max(RateCardVersion.version_number)).where(
            RateCardVersion.rate_card_id == rate_card.id
        )
    )
    next_version = int(max_version or 0) + 1
    version = RateCardVersion(
        rate_card_id=rate_card.id,
        version_number=next_version,
        settings=normalize_settings_dict(DEFAULT_RATE_CARD_SETTINGS),
    )
    db.add(version)
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
