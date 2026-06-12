import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.estimate import Estimate, EstimateStatus
from app.rate_cards.fingerprint import get_latest_rate_card_fingerprint

RATE_CARD_FINGERPRINT_KEY = "_rate_card_fingerprint"


def get_stored_rate_card_fingerprint(estimate: Estimate) -> str | None:
    assumptions = estimate.maintenance_assumptions or {}
    fingerprint = assumptions.get(RATE_CARD_FINGERPRINT_KEY)
    return fingerprint if isinstance(fingerprint, str) else None


async def get_extracted_rate_card_fingerprint(
    db: AsyncSession,
    estimate_id: uuid.UUID,
) -> str | None:
    result = await db.execute(
        select(AuditLog)
        .where(
            AuditLog.estimate_id == estimate_id,
            AuditLog.action == "extraction_completed",
        )
        .order_by(AuditLog.created_at.desc())
        .limit(1)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        return None
    fingerprint = entry.changes.get("rate_card_fingerprint")
    return fingerprint if isinstance(fingerprint, str) else None


async def has_completed_extraction(db: AsyncSession, estimate_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(AuditLog.id)
        .where(
            AuditLog.estimate_id == estimate_id,
            AuditLog.action == "extraction_completed",
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def resolve_extracted_rate_card_fingerprint(
    db: AsyncSession,
    estimate: Estimate,
) -> str | None:
    stored = get_stored_rate_card_fingerprint(estimate)
    if stored:
        return stored
    return await get_extracted_rate_card_fingerprint(db, estimate.id)


async def is_rate_card_stale_for_estimate(db: AsyncSession, estimate: Estimate) -> bool:
    if estimate.status not in (
        EstimateStatus.REVIEW.value,
        EstimateStatus.CALCULATED.value,
        EstimateStatus.EXPORTED.value,
    ):
        return False
    if not estimate.rate_card_id or not estimate.extracted_data:
        return False

    extracted_fingerprint = await resolve_extracted_rate_card_fingerprint(db, estimate)
    if not extracted_fingerprint:
        return await has_completed_extraction(db, estimate.id)

    current_fingerprint = await get_latest_rate_card_fingerprint(db, estimate.rate_card_id)
    if not current_fingerprint:
        return False

    return current_fingerprint != extracted_fingerprint
