import os
import uuid
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionLocal
from app.dependencies import get_content_locale, get_current_user, get_db, get_display_locale
from app.estimates import ai_suggest_form, extraction, service
from app.models.user import User
from app.schemas.estimate import (
    AuditLogEntry,
    CalculateEstimateRequest,
    CreateEstimateRateCardRequest,
    EstimateAiSuggestFormRequest,
    EstimateAiSuggestFormResponse,
    EstimateCreate,
    EstimateDetail,
    EstimateStatusResponse,
    EstimateSummary,
    EstimateUpdate,
    ExtractedDataUpdate,
    FeatureItemsUpdate,
    GenerateRateCardResponse,
    GanttTimelineResponse,
)

router = APIRouter(prefix="/estimates", tags=["estimates"])


async def _run_extraction_background(
    estimate_id: uuid.UUID,
    user_id: uuid.UUID,
    content_locale: str | None = None,
) -> None:
    import logging

    logger = logging.getLogger(__name__)
    try:
        async with SessionLocal() as db:
            await extraction.run_extraction(db, estimate_id, user_id, content_locale=content_locale)
    except Exception:
        logger.exception("Extraction background task failed for estimate %s", estimate_id)
        raise


@router.post("", response_model=EstimateDetail, status_code=201)
async def create_estimate(
    body: EstimateCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    estimate = await service.create_estimate(db, user, body)
    return await service.estimate_to_detail(db, estimate)


@router.get("", response_model=list[EstimateSummary])
async def list_estimates(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await service.list_estimates(db, user)


@router.get("/{estimate_id}", response_model=EstimateDetail)
async def get_estimate(
    estimate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    display_locale: str | None = Depends(get_display_locale),
):
    estimate = await service.get_estimate_for_user(db, estimate_id, user)
    return await service.estimate_to_detail(db, estimate, display_locale=display_locale)


@router.patch("/{estimate_id}", response_model=EstimateDetail)
async def update_estimate(
    estimate_id: uuid.UUID,
    body: EstimateUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    content_locale: str | None = Depends(get_content_locale),
    display_locale: str | None = Depends(get_display_locale),
):
    estimate = await service.update_estimate(
        db,
        user,
        estimate_id,
        body,
        content_locale=content_locale,
    )
    return await service.estimate_to_detail(db, estimate, display_locale=display_locale)


@router.delete("/{estimate_id}", status_code=204)
async def delete_estimate(
    estimate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await service.delete_estimate(db, estimate_id, user)


@router.post("/{estimate_id}/extract", status_code=202)
async def start_extraction(
    estimate_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    content_locale: str | None = Depends(get_content_locale),
):
    begin_result = await extraction.begin_extraction(db, estimate_id, user.id)

    if begin_result == "already_running":
        return {"status": "already_running"}

    if os.environ.get("EXTRACT_SYNC") == "1":
        await extraction.run_extraction(db, estimate_id, user.id, content_locale=content_locale)
    else:
        background_tasks.add_task(
            _run_extraction_background,
            estimate_id,
            user.id,
            content_locale,
        )

    return {"status": "accepted"}


@router.post("/{estimate_id}/ai/suggest-form", response_model=EstimateAiSuggestFormResponse)
async def suggest_estimate_form(
    estimate_id: uuid.UUID,
    body: EstimateAiSuggestFormRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await ai_suggest_form.suggest_form_for_estimate(db, estimate_id, body, user)


@router.post("/{estimate_id}/rate-card/generate", response_model=GenerateRateCardResponse)
async def generate_estimate_rate_card(
    estimate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.rate_cards.generation import generate_rate_card_for_estimate

    return await generate_rate_card_for_estimate(db, estimate_id, user)


@router.post("/{estimate_id}/rate-card", response_model=EstimateDetail)
async def create_estimate_rate_card(
    estimate_id: uuid.UUID,
    body: CreateEstimateRateCardRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    estimate = await service.create_rate_card_for_estimate(db, user, estimate_id, body)
    return await service.estimate_to_detail(db, estimate)


@router.get("/{estimate_id}/status", response_model=EstimateStatusResponse)
async def get_estimate_status(
    estimate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await extraction.get_extraction_status(db, estimate_id, user)


@router.put("/{estimate_id}/feature-items", response_model=EstimateDetail)
async def update_feature_items(
    estimate_id: uuid.UUID,
    body: FeatureItemsUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    content_locale: str | None = Depends(get_content_locale),
    display_locale: str | None = Depends(get_display_locale),
):
    estimate = await service.update_feature_items(
        db,
        user,
        estimate_id,
        body,
        content_locale=content_locale,
    )
    return await service.estimate_to_detail(db, estimate, display_locale=display_locale)


@router.patch("/{estimate_id}/extracted-data", response_model=EstimateDetail)
async def update_extracted_data(
    estimate_id: uuid.UUID,
    body: ExtractedDataUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    content_locale: str | None = Depends(get_content_locale),
    display_locale: str | None = Depends(get_display_locale),
):
    estimate = await service.update_extracted_data(
        db,
        user,
        estimate_id,
        body,
        content_locale=content_locale,
    )
    return await service.estimate_to_detail(db, estimate, display_locale=display_locale)


@router.get("/{estimate_id}/gantt", response_model=GanttTimelineResponse)
async def get_estimate_gantt(
    estimate_id: uuid.UUID,
    start_date: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    display_locale: str | None = Depends(get_display_locale),
):
    gantt = await service.get_gantt_timeline(
        db,
        estimate_id,
        user,
        start_date=start_date,
        display_locale=display_locale,
    )
    return GanttTimelineResponse(gantt=gantt)


@router.post("/{estimate_id}/calculate", response_model=EstimateDetail)
async def calculate_estimate_endpoint(
    estimate_id: uuid.UUID,
    recalculate_with_current_rates: bool = False,
    body: CalculateEstimateRequest | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project_start_date = body.project_start_date if body else None
    estimate = await service.run_calculation(
        db,
        user,
        estimate_id,
        recalculate_with_current_rates=recalculate_with_current_rates,
        project_start_date=project_start_date,
    )
    return await service.estimate_to_detail(db, estimate)


@router.get("/{estimate_id}/audit", response_model=list[AuditLogEntry])
async def get_estimate_audit(
    estimate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await service.get_audit_log(db, estimate_id, user)
