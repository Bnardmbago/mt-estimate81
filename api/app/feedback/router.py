import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
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
    VarianceDashboardRow,
    VarianceSummary,
)

router = APIRouter(prefix="/estimates", tags=["feedback"])


def _variance_for_estimate(estimate) -> VarianceSummary | None:
    if not estimate.calculation_result or not estimate.actuals:
        return None
    estimated = service.extract_estimated(estimate.calculation_result)
    actual = service.extract_actual(estimate.actuals)
    return VarianceSummary.model_validate(service.compute_variance(estimated, actual))


@router.get("/variance-dashboard", response_model=list[VarianceDashboardRow])
async def variance_dashboard(
    client: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    sort_metric: str = Query(default="effort_hours"),
    sort_order: str = Query(default="desc", pattern=r"^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = await service.list_variance_dashboard(
        db,
        client=client,
        date_from=date_from,
        date_to=date_to,
        sort_metric=sort_metric,
        sort_order=sort_order,
    )
    return [VarianceDashboardRow.model_validate(row) for row in rows]


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
