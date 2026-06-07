import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.audit.service import log_change
from app.models.audit import AuditLog
from app.models.estimate import Estimate, EstimateStatus
from app.models.user import User
from app.schemas.estimate import EstimateCreate, EstimateUpdate


async def create_estimate(
    db: AsyncSession,
    user: User,
    data: EstimateCreate,
) -> Estimate:
    estimate = Estimate(
        project_name=data.project_name,
        client_name=data.client_name,
        locale=data.locale,
        form_data=data.form_data,
        status=EstimateStatus.DRAFT.value,
        created_by=user.id,
    )
    db.add(estimate)
    await db.flush()

    await log_change(
        db,
        estimate_id=estimate.id,
        user_id=user.id,
        action="created",
        changes={
            "project_name": data.project_name,
            "client_name": data.client_name,
            "locale": data.locale,
            "status": EstimateStatus.DRAFT.value,
        },
    )
    await db.commit()
    return await get_estimate(db, estimate.id)


async def list_estimates(db: AsyncSession) -> list[Estimate]:
    result = await db.execute(select(Estimate).order_by(Estimate.updated_at.desc()))
    return list(result.scalars().all())


async def get_estimate(db: AsyncSession, estimate_id: uuid.UUID) -> Estimate:
    result = await db.execute(
        select(Estimate)
        .where(Estimate.id == estimate_id)
        .options(
            selectinload(Estimate.feature_items),
            selectinload(Estimate.documents),
        )
    )
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(
            status_code=404,
            detail={"error": "Estimate not found", "code": "ESTIMATE_NOT_FOUND"},
        )
    return estimate


async def update_estimate(
    db: AsyncSession,
    user: User,
    estimate_id: uuid.UUID,
    data: EstimateUpdate,
) -> Estimate:
    result = await db.execute(
        select(Estimate)
        .where(Estimate.id == estimate_id)
        .options(
            selectinload(Estimate.feature_items),
            selectinload(Estimate.documents),
        )
    )
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(
            status_code=404,
            detail={"error": "Estimate not found", "code": "ESTIMATE_NOT_FOUND"},
        )

    changes: dict[str, Any] = {}
    update_data = data.model_dump(exclude_unset=True)

    for field, new_value in update_data.items():
        old_value = getattr(estimate, field)
        if old_value != new_value:
            changes[field] = {"old": old_value, "new": new_value}
            setattr(estimate, field, new_value)

    if changes:
        await log_change(
            db,
            estimate_id=estimate.id,
            user_id=user.id,
            action="updated",
            changes=changes,
        )

    await db.commit()
    return await get_estimate(db, estimate.id)


async def get_audit_log(db: AsyncSession, estimate_id: uuid.UUID) -> list[AuditLog]:
    exists = await db.execute(select(Estimate.id).where(Estimate.id == estimate_id))
    if not exists.scalar_one_or_none():
        raise HTTPException(
            status_code=404,
            detail={"error": "Estimate not found", "code": "ESTIMATE_NOT_FOUND"},
        )

    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.estimate_id == estimate_id)
        .order_by(AuditLog.created_at.asc())
    )
    return list(result.scalars().all())
