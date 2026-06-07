import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def log_change(
    db: AsyncSession,
    estimate_id: uuid.UUID,
    user_id: uuid.UUID,
    action: str,
    changes: dict,
) -> None:
    entry = AuditLog(
        estimate_id=estimate_id,
        user_id=user_id,
        action=action,
        changes=changes,
    )
    db.add(entry)
    await db.flush()
