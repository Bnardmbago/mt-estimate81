from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.audit.service import log_change
from app.estimates.service import get_estimate
from app.models.estimate import Actuals, Estimate, EstimateStatus
from app.models.user import User
from app.schemas.feedback import ActualsInput


def compute_variance(estimated: dict, actual: dict) -> dict:
    def row(key: str) -> dict[str, Any]:
        est = estimated[key]
        act = actual[key]
        pct = ((act - est) / est * 100) if est else 0
        severity = "green" if abs(pct) <= 10 else "amber" if abs(pct) <= 25 else "red"
        return {
            "estimated": est,
            "actual": act,
            "variance_pct": round(pct, 1),
            "severity": severity,
        }

    return {
        "effort_hours": row("effort_hours"),
        "effort_days": row("effort_days"),
        "nrc_jpy": row("nrc_jpy"),
        "rc_monthly_jpy": row("rc_monthly_jpy"),
    }


def extract_estimated(calculation_result: dict) -> dict[str, float | int]:
    nrc = calculation_result.get("nrc") or {}
    rc = calculation_result.get("rc") or {}
    return {
        "effort_hours": float(calculation_result.get("total_effort_hours") or 0),
        "effort_days": float(calculation_result.get("total_effort_days") or 0),
        "nrc_jpy": int(nrc.get("total_jpy") or 0),
        "rc_monthly_jpy": int(rc.get("monthly_total_jpy") or 0),
    }


def extract_actual(actuals: Actuals) -> dict[str, float | int]:
    return {
        "effort_hours": float(actuals.actual_effort_hours),
        "effort_days": float(actuals.actual_duration_days),
        "nrc_jpy": actuals.actual_nrc_jpy,
        "rc_monthly_jpy": actuals.actual_rc_monthly_jpy,
    }


def primary_variance_pct(variance: dict) -> float:
    return abs(variance["effort_hours"]["variance_pct"])


async def complete_estimate(
    db: AsyncSession,
    user: User,
    estimate_id,
) -> Estimate:
    estimate = await get_estimate(db, estimate_id)

    if estimate.status not in (
        EstimateStatus.CALCULATED.value,
        EstimateStatus.EXPORTED.value,
    ):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Only calculated or exported estimates can be marked complete",
                "code": "INVALID_STATUS",
            },
        )

    if not estimate.calculation_result:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Calculation result is required before completion",
                "code": "CALCULATION_REQUIRED",
            },
        )

    estimate.status = EstimateStatus.COMPLETED.value

    await log_change(
        db,
        estimate_id=estimate.id,
        user_id=user.id,
        action="completed",
        changes={"status": EstimateStatus.COMPLETED.value},
    )
    await db.commit()
    return await get_estimate(db, estimate_id)


async def upsert_actuals(
    db: AsyncSession,
    user: User,
    estimate_id,
    data: ActualsInput,
) -> Actuals:
    result = await db.execute(
        select(Estimate)
        .where(Estimate.id == estimate_id)
        .options(selectinload(Estimate.actuals))
    )
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(
            status_code=404,
            detail={"error": "Estimate not found", "code": "ESTIMATE_NOT_FOUND"},
        )

    if estimate.status not in (
        EstimateStatus.CALCULATED.value,
        EstimateStatus.EXPORTED.value,
        EstimateStatus.COMPLETED.value,
    ):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Actuals can only be entered after calculation",
                "code": "INVALID_STATUS",
            },
        )

    if estimate.actuals:
        actuals = estimate.actuals
        actuals.actual_effort_hours = data.actual_effort_hours
        actuals.actual_duration_days = data.actual_duration_days
        actuals.actual_nrc_jpy = data.actual_nrc_jpy
        actuals.actual_rc_monthly_jpy = data.actual_rc_monthly_jpy
        actuals.variance_notes = data.variance_notes
        actuals.entered_by = user.id
        actuals.entered_at = datetime.utcnow()
        action = "actuals_updated"
    else:
        actuals = Actuals(
            estimate_id=estimate_id,
            actual_effort_hours=data.actual_effort_hours,
            actual_duration_days=data.actual_duration_days,
            actual_nrc_jpy=data.actual_nrc_jpy,
            actual_rc_monthly_jpy=data.actual_rc_monthly_jpy,
            variance_notes=data.variance_notes,
            entered_by=user.id,
        )
        db.add(actuals)
        action = "actuals_entered"

    await log_change(
        db,
        estimate_id=estimate.id,
        user_id=user.id,
        action=action,
        changes={
            "actual_effort_hours": data.actual_effort_hours,
            "actual_nrc_jpy": data.actual_nrc_jpy,
        },
    )
    await db.commit()
    await db.refresh(actuals)
    return actuals


async def list_variance_dashboard(
    db: AsyncSession,
    *,
    client: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort_metric: str = "effort_hours",
    sort_order: str = "desc",
) -> list[dict[str, Any]]:
    result = await db.execute(
        select(Estimate)
        .where(Estimate.status == EstimateStatus.COMPLETED.value)
        .options(selectinload(Estimate.actuals))
        .order_by(Estimate.updated_at.desc())
    )
    estimates = list(result.scalars().all())

    rows: list[dict[str, Any]] = []
    for estimate in estimates:
        if client and client.lower() not in estimate.client_name.lower():
            continue

        entered_at = estimate.actuals.entered_at if estimate.actuals else estimate.updated_at
        if date_from and entered_at < date_from:
            continue
        if date_to and entered_at > date_to:
            continue

        variance = None
        if estimate.calculation_result and estimate.actuals:
            estimated = extract_estimated(estimate.calculation_result)
            actual = extract_actual(estimate.actuals)
            variance = compute_variance(estimated, actual)

        row = {
            "estimate_id": estimate.id,
            "project_name": estimate.project_name,
            "client_name": estimate.client_name,
            "completed_at": estimate.updated_at,
            "actuals_entered_at": estimate.actuals.entered_at if estimate.actuals else None,
            "variance": variance,
            "variance_notes": estimate.actuals.variance_notes if estimate.actuals else None,
        }
        if variance and sort_metric in variance:
            row["_sort_pct"] = abs(variance[sort_metric]["variance_pct"])
        else:
            row["_sort_pct"] = -1.0
        rows.append(row)

    reverse = sort_order.lower() != "asc"
    rows.sort(key=lambda item: item["_sort_pct"], reverse=reverse)
    for row in rows:
        row.pop("_sort_pct", None)
    return rows
