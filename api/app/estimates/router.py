import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionLocal
from app.dependencies import get_current_user, get_db
from app.estimates import extraction, service
from app.models.estimate import EstimateStatus
from app.models.user import User
from app.schemas.estimate import (
    AuditLogEntry,
    EstimateCreate,
    EstimateDetail,
    EstimateStatusResponse,
    EstimateSummary,
    EstimateUpdate,
    ExtractedDataUpdate,
    FeatureItemsUpdate,
)

router = APIRouter(prefix="/estimates", tags=["estimates"])


async def _run_extraction_background(estimate_id: uuid.UUID, user_id: uuid.UUID) -> None:
    async with SessionLocal() as db:
        await extraction.run_extraction(db, estimate_id, user_id)


@router.post("", response_model=EstimateDetail, status_code=201)
async def create_estimate(
    body: EstimateCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    estimate = await service.create_estimate(db, user, body)
    return estimate


@router.get("", response_model=list[EstimateSummary])
async def list_estimates(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await service.list_estimates(db)


@router.get("/{estimate_id}", response_model=EstimateDetail)
async def get_estimate(
    estimate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await service.get_estimate(db, estimate_id)


@router.patch("/{estimate_id}", response_model=EstimateDetail)
async def update_estimate(
    estimate_id: uuid.UUID,
    body: EstimateUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await service.update_estimate(db, user, estimate_id, body)


@router.post("/{estimate_id}/extract", status_code=202)
async def start_extraction(
    estimate_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    estimate = await service.get_estimate(db, estimate_id)

    if estimate.status not in (EstimateStatus.DRAFT.value, EstimateStatus.REVIEW.value):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Extraction can only be started from draft or review",
                "code": "INVALID_STATUS",
            },
        )

    if os.environ.get("EXTRACT_SYNC") == "1":
        await extraction.run_extraction(db, estimate_id, user.id)
    else:
        background_tasks.add_task(_run_extraction_background, estimate_id, user.id)

    return {"status": "accepted"}


@router.get("/{estimate_id}/status", response_model=EstimateStatusResponse)
async def get_estimate_status(
    estimate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await extraction.get_extraction_status(db, estimate_id)


@router.put("/{estimate_id}/feature-items", response_model=EstimateDetail)
async def update_feature_items(
    estimate_id: uuid.UUID,
    body: FeatureItemsUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await service.update_feature_items(db, user, estimate_id, body)


@router.patch("/{estimate_id}/extracted-data", response_model=EstimateDetail)
async def update_extracted_data(
    estimate_id: uuid.UUID,
    body: ExtractedDataUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await service.update_extracted_data(db, user, estimate_id, body)


@router.post("/{estimate_id}/calculate", response_model=EstimateDetail)
async def calculate_estimate_endpoint(
    estimate_id: uuid.UUID,
    recalculate_with_current_rates: bool = False,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await service.run_calculation(
        db,
        user,
        estimate_id,
        recalculate_with_current_rates=recalculate_with_current_rates,
    )


@router.get("/{estimate_id}/audit", response_model=list[AuditLogEntry])
async def get_estimate_audit(
    estimate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await service.get_audit_log(db, estimate_id)
