import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.estimates import service
from app.models.user import User
from app.schemas.estimate import (
    AuditLogEntry,
    EstimateCreate,
    EstimateDetail,
    EstimateSummary,
    EstimateUpdate,
)

router = APIRouter(prefix="/estimates", tags=["estimates"])


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


@router.get("/{estimate_id}/audit", response_model=list[AuditLogEntry])
async def get_estimate_audit(
    estimate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await service.get_audit_log(db, estimate_id)
