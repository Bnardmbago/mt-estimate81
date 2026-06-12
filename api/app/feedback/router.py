import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.estimates.service import get_estimate
from app.feedback import service
from app.models.user import User
from app.schemas.estimate import EstimateDetail
from app.schemas.feedback import (
    ActualsInput,
    ActualsResponse,
    ActualsWithVariance,
    VarianceSummary,
)

router = APIRouter(prefix="/estimates", tags=["feedback"])


def _variance_for_estimate(estimate) -> VarianceSummary | None:
    if not estimate.calculation_result or not estimate.actuals:
        return None
    estimated = service.extract_estimated(estimate.calculation_result)
    actual = service.extract_actual(estimate.actuals)
    return VarianceSummary.model_validate(service.compute_variance(estimated, actual))


@router.post("/{estimate_id}/complete", response_model=EstimateDetail)
async def complete_estimate(
    estimate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await service.complete_estimate(db, user, estimate_id)


@router.put("/{estimate_id}/actuals", response_model=ActualsWithVariance)
async def upsert_actuals(
    estimate_id: uuid.UUID,
    body: ActualsInput,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    actuals = await service.upsert_actuals(db, user, estimate_id, body)
    estimate = await get_estimate(db, estimate_id)
    variance = _variance_for_estimate(estimate)
    return ActualsWithVariance(
        actuals=ActualsResponse.model_validate(actuals),
        variance=variance,
    )
