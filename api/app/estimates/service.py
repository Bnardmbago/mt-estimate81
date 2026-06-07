import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.audit.service import log_change
from app.models.audit import AuditLog
from app.models.estimate import Estimate, EstimateStatus
from app.models.user import User
from app.models.estimate import FeatureItem
from app.schemas.estimate import (
    EstimateCreate,
    EstimateUpdate,
    ExtractedDataUpdate,
    FeatureItemsUpdate,
)


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


async def update_feature_items(
    db: AsyncSession,
    user: User,
    estimate_id: uuid.UUID,
    data: FeatureItemsUpdate,
) -> Estimate:
    estimate = await get_estimate(db, estimate_id)

    if estimate.status not in (
        EstimateStatus.REVIEW.value,
        EstimateStatus.CALCULATED.value,
    ):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Feature items can only be edited during review",
                "code": "INVALID_STATUS",
            },
        )

    existing_ids = {item.id for item in estimate.feature_items}
    incoming_ids = {item.id for item in data.items if item.id is not None}
    removed_ids = existing_ids - incoming_ids

    if removed_ids:
        await db.execute(
            delete(FeatureItem).where(
                FeatureItem.estimate_id == estimate_id,
                FeatureItem.id.in_(removed_ids),
            )
        )

    items_by_id = {item.id: item for item in estimate.feature_items}
    updated_items: list[FeatureItem] = []

    for index, item_data in enumerate(data.items):
        if item_data.id and item_data.id in items_by_id:
            item = items_by_id[item_data.id]
            item.sort_order = index
            item.name = item_data.name
            item.description = item_data.description
            item.hours = item_data.hours
            item.phase = item_data.phase
            item.role = item_data.role
            item.is_ai_generated = item_data.is_ai_generated
            updated_items.append(item)
        else:
            item = FeatureItem(
                estimate_id=estimate_id,
                sort_order=index,
                name=item_data.name,
                description=item_data.description,
                hours=item_data.hours,
                phase=item_data.phase,
                role=item_data.role,
                is_ai_generated=item_data.is_ai_generated,
            )
            db.add(item)
            updated_items.append(item)

    await log_change(
        db,
        estimate_id=estimate.id,
        user_id=user.id,
        action="feature_items_updated",
        changes={"count": len(updated_items)},
    )
    await db.commit()
    return await get_estimate(db, estimate_id)


async def update_extracted_data(
    db: AsyncSession,
    user: User,
    estimate_id: uuid.UUID,
    data: ExtractedDataUpdate,
) -> Estimate:
    estimate = await get_estimate(db, estimate_id)

    if estimate.status not in (
        EstimateStatus.REVIEW.value,
        EstimateStatus.CALCULATED.value,
    ):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Extracted data can only be edited during review",
                "code": "INVALID_STATUS",
            },
        )

    current = dict(estimate.extracted_data or {})
    update_data = data.model_dump(exclude_unset=True)
    current.update(update_data)
    estimate.extracted_data = current

    await log_change(
        db,
        estimate_id=estimate.id,
        user_id=user.id,
        action="extracted_data_updated",
        changes={"fields": list(update_data.keys())},
    )
    await db.commit()
    return await get_estimate(db, estimate_id)


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
