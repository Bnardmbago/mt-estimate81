import uuid

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.audit import AuditLog
from app.models.contact_magic_link import ContactMagicLink
from app.models.estimate import Actuals, Estimate, Export
from app.models.rate_card import RateCard
from app.models.user import User
from app.storage.factory import get_storage_backend


async def _purge_estimate_files(estimate: Estimate) -> None:
    storage = get_storage_backend()
    for document in estimate.documents:
        if await storage.exists(document.storage_path):
            await storage.delete(document.storage_path)
    for export in estimate.exports:
        if await storage.exists(export.storage_path):
            await storage.delete(export.storage_path)


async def _delete_user_estimates(db: AsyncSession, user_id: uuid.UUID) -> None:
    result = await db.execute(
        select(Estimate)
        .where(Estimate.created_by == user_id)
        .options(
            selectinload(Estimate.documents),
            selectinload(Estimate.exports),
        )
    )
    for estimate in result.scalars().all():
        await _purge_estimate_files(estimate)
        await db.delete(estimate)


async def _delete_orphaned_exports(db: AsyncSession, user_id: uuid.UUID) -> None:
    result = await db.execute(
        select(Export)
        .where(Export.generated_by == user_id)
        .options(selectinload(Export.estimate))
    )
    storage = get_storage_backend()
    for export in result.scalars().all():
        if await storage.exists(export.storage_path):
            await storage.delete(export.storage_path)
        await db.delete(export)


async def _delete_orphaned_actuals(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(delete(Actuals).where(Actuals.entered_by == user_id))


async def _delete_user_rate_cards(db: AsyncSession, user_id: uuid.UUID) -> None:
    result = await db.execute(select(RateCard).where(RateCard.created_by == user_id))
    rate_cards = list(result.scalars().all())
    if not rate_cards:
        return

    card_ids = [card.id for card in rate_cards]
    in_use = await db.scalar(
        select(func.count())
        .select_from(Estimate)
        .where(Estimate.rate_card_id.in_(card_ids))
    )
    if in_use:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Cannot delete user while their rate cards are used by estimates",
                "code": "USER_RATE_CARDS_IN_USE",
                "details": {"estimate_count": int(in_use)},
            },
        )

    for rate_card in rate_cards:
        await db.delete(rate_card)


async def delete_user_and_dependencies(db: AsyncSession, user: User) -> None:
    """Remove a user and all rows that reference them."""
    await _delete_user_estimates(db, user.id)
    await db.execute(delete(ContactMagicLink).where(ContactMagicLink.user_id == user.id))
    await db.execute(delete(AuditLog).where(AuditLog.user_id == user.id))
    await _delete_orphaned_exports(db, user.id)
    await _delete_orphaned_actuals(db, user.id)
    await _delete_user_rate_cards(db, user.id)
    await db.delete(user)
    await db.commit()
