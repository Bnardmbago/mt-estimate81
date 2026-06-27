import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.calculation.development_approach import DevelopmentApproach
from app.calculation.schemas import RateCardSettings
from app.dependencies import get_db, require_full_account
from app.estimates.access import can_access_estimate
from app.estimates.rate_card_stale import mark_rate_card_auto_tune_enabled
from app.models.estimate import Estimate
from app.models.rate_card import RateCard, RateCardVersion
from app.models.user import User
from app.rate_cards.normalize import normalize_settings_dict
from app.rate_cards.defaults import DEFAULT_RATE_CARD_SETTINGS, Currency
from app.rate_cards.regional_profiles import apply_regional_standard
from app.fx import get_fx_service
from app.rate_cards import service as rate_card_service
from app.rate_cards.ai_suggest import suggest_rate_card_section_for_card
from app.schemas.rate_card import (
    ActiveRateCardResponse,
    ApplyRegionalRatesRequest,
    ApplyRegionalRatesResponse,
    FxRatesResponse,
    RateCardAiSuggestRequest,
    RateCardAiSuggestResponse,
    RateCardCreate,
    RateCardDuplicate,
    RateCardEstimateUsage,
    RateCardOption,
    RateCardSummary,
    RateCardUpdate,
    RateCardVersionLabelUpdate,
    RateCardVersionResponse,
    RateCardVersionUpdate,
)

router = APIRouter(tags=["rate-cards"])


def _validate_phase_percentages(settings: RateCardSettings) -> None:
    total = sum(phase.percentage for phase in settings.phases)
    if abs(total - 1.0) > 0.001:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Phase percentages must sum to 100% (got {total * 100:.1f}%)",
                "code": "INVALID_PHASE_SUM",
            },
        )


def _serialize_settings(settings: RateCardSettings) -> dict:
    return normalize_settings_dict(settings.model_dump())


async def _get_duplicated_from_name(db: AsyncSession, rate_card: RateCard) -> str | None:
    if not rate_card.duplicated_from_rate_card_id:
        return None
    source = await db.get(RateCard, rate_card.duplicated_from_rate_card_id)
    return source.name if source else None


async def _to_active_response(
    db: AsyncSession,
    rate_card: RateCard,
    version: RateCardVersion,
) -> ActiveRateCardResponse:
    estimate_count = await _count_estimates_using_card(db, rate_card.id)
    return ActiveRateCardResponse(
        id=rate_card.id,
        name=rate_card.name,
        is_active=rate_card.is_active,
        version_number=version.version_number,
        version_id=version.id,
        version_label=version.label,
        settings=normalize_settings_dict(version.settings),
        created_at=version.created_at,
        estimate_count=estimate_count,
        is_locked=False,
        duplicated_from_name=await _get_duplicated_from_name(db, rate_card),
    )


async def _to_card_summary(db: AsyncSession, card: RateCard) -> RateCardSummary:
    latest = await _get_latest_version(db, card.id)
    estimate_count = await _count_estimates_using_card(db, card.id)
    approach_raw = DevelopmentApproach.TRADITIONAL.value
    if latest:
        normalized = normalize_settings_dict(latest.settings)
        approach_raw = normalized.get("development_approach", approach_raw)
    return RateCardSummary(
        id=card.id,
        name=card.name,
        is_active=card.is_active,
        development_approach=DevelopmentApproach(approach_raw),
        version_count=await _count_versions(db, card.id),
        latest_version_number=latest.version_number if latest else 0,
        created_at=card.created_at,
        estimate_count=estimate_count,
        is_locked=False,
        duplicated_from_name=await _get_duplicated_from_name(db, card),
    )


async def _get_latest_version(
    db: AsyncSession, rate_card_id: uuid.UUID
) -> RateCardVersion | None:
    result = await db.execute(
        select(RateCardVersion)
        .where(RateCardVersion.rate_card_id == rate_card_id)
        .order_by(RateCardVersion.version_number.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_version_for_rate_card(
    db: AsyncSession,
    rate_card_id: uuid.UUID,
    version_id: uuid.UUID,
) -> RateCardVersion:
    result = await db.execute(
        select(RateCardVersion).where(
            RateCardVersion.id == version_id,
            RateCardVersion.rate_card_id == rate_card_id,
        )
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(
            status_code=404,
            detail={"error": "Rate card version not found", "code": "RATE_CARD_VERSION_NOT_FOUND"},
        )
    return version


async def _count_estimates_using_version(db: AsyncSession, version_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(Estimate)
        .where(Estimate.rate_card_version_id == version_id)
    )
    return int(result.scalar_one())


async def _count_estimates_using_card(db: AsyncSession, rate_card_id: uuid.UUID) -> int:
    version_result = await db.execute(
        select(func.count())
        .select_from(Estimate)
        .join(RateCardVersion, Estimate.rate_card_version_id == RateCardVersion.id)
        .where(RateCardVersion.rate_card_id == rate_card_id)
    )
    assigned_result = await db.execute(
        select(func.count())
        .select_from(Estimate)
        .where(Estimate.rate_card_id == rate_card_id)
    )
    return max(int(version_result.scalar_one()), int(assigned_result.scalar_one()))


def _to_version_response(
    version: RateCardVersion,
    *,
    estimate_count: int,
) -> RateCardVersionResponse:
    return RateCardVersionResponse(
        id=version.id,
        rate_card_id=version.rate_card_id,
        version_number=version.version_number,
        label=version.label,
        settings=normalize_settings_dict(version.settings),
        created_at=version.created_at,
        estimate_count=estimate_count,
    )


async def _count_versions(db: AsyncSession, rate_card_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(RateCardVersion)
        .where(RateCardVersion.rate_card_id == rate_card_id)
    )
    return int(result.scalar_one())


@router.get("/fx-rates", response_model=FxRatesResponse)
async def get_fx_rates(
    user: User = Depends(require_full_account),
):
    rates = await get_fx_service().get_public_rates()
    return FxRatesResponse(rates=rates)


@router.post("/apply-regional-standard", response_model=ApplyRegionalRatesResponse)
async def apply_regional_standard_rates(
    body: ApplyRegionalRatesRequest,
    user: User = Depends(require_full_account),
):
    currency = body.currency or body.settings.currency
    updated, roles_updated = await apply_regional_standard(
        body.settings,
        body.region,
        currency,
        get_fx_service(),
    )
    return ApplyRegionalRatesResponse(
        settings=normalize_settings_dict(updated.model_dump()),
        roles_updated=roles_updated,
    )


@router.get("/cards/options", response_model=list[RateCardOption])
async def list_rate_card_options(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
):
    return await rate_card_service.list_rate_card_options(db, user)


@router.get("/cards", response_model=list[RateCardSummary])
async def list_rate_cards(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
):
    query = select(RateCard).order_by(RateCard.is_active.desc(), RateCard.created_at.desc())
    if not user.is_admin:
        query = query.where(RateCard.created_by == user.id)
    result = await db.execute(query)
    cards = list(result.scalars().all())
    summaries: list[RateCardSummary] = []
    for card in cards:
        summaries.append(await _to_card_summary(db, card))
    return summaries


@router.get("/cards/{card_id}", response_model=ActiveRateCardResponse)
async def get_rate_card_by_id(
    card_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
):
    rate_card = await rate_card_service.get_rate_card_for_user(db, card_id, user)
    version = await _get_latest_version(db, rate_card.id)
    if not version:
        raise HTTPException(
            status_code=404,
            detail={"error": "Rate card has no versions", "code": "RATE_CARD_NOT_FOUND"},
        )
    return await _to_active_response(db, rate_card, version)


@router.put("/cards/{card_id}", response_model=ActiveRateCardResponse)
async def update_rate_card_by_id(
    card_id: uuid.UUID,
    body: RateCardUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
):
    _validate_phase_percentages(body.settings)

    rate_card = await rate_card_service.get_rate_card_for_user(db, card_id, user)
    version = await _get_latest_version(db, rate_card.id)
    if not version:
        raise HTTPException(
            status_code=404,
            detail={"error": "Rate card has no versions", "code": "RATE_CARD_NOT_FOUND"},
        )

    if body.name:
        rate_card.name = body.name.strip()

    version.settings = _serialize_settings(body.settings)
    if body.version_label is not None:
        version.label = body.version_label.strip() or None

    for estimate in await _list_estimates_for_card(db, rate_card.id):
        estimate.maintenance_assumptions = mark_rate_card_auto_tune_enabled(
            estimate.maintenance_assumptions or {},
            enabled=False,
        )

    await db.commit()
    await db.refresh(version)

    return await _to_active_response(db, rate_card, version)


@router.post("/cards", response_model=ActiveRateCardResponse, status_code=201)
async def create_rate_card(
    body: RateCardCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
):
    name = body.name.strip()

    if body.activate:
        await rate_card_service.deactivate_all_rate_cards(db, user)

    rate_card = RateCard(
        name=name,
        is_active=body.activate,
        created_by=user.id,
    )
    db.add(rate_card)
    await db.flush()

    settings = normalize_settings_dict(
        {
            **DEFAULT_RATE_CARD_SETTINGS,
            "development_approach": body.development_approach.value,
        }
    )

    version = RateCardVersion(
        rate_card_id=rate_card.id,
        version_number=1,
        settings=settings,
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)

    return await _to_active_response(db, rate_card, version)


async def _list_estimates_for_card(
    db: AsyncSession,
    card_id: uuid.UUID,
) -> list[Estimate]:
    via_version = await db.execute(
        select(Estimate)
        .join(RateCardVersion, Estimate.rate_card_version_id == RateCardVersion.id)
        .where(RateCardVersion.rate_card_id == card_id)
    )
    via_assignment = await db.execute(
        select(Estimate).where(Estimate.rate_card_id == card_id)
    )

    by_id: dict[uuid.UUID, Estimate] = {}
    for estimate in via_version.scalars().all():
        by_id[estimate.id] = estimate
    for estimate in via_assignment.scalars().all():
        by_id[estimate.id] = estimate

    return sorted(by_id.values(), key=lambda row: row.updated_at, reverse=True)


@router.get("/cards/{card_id}/estimates", response_model=list[RateCardEstimateUsage])
async def list_rate_card_estimates(
    card_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
):
    await rate_card_service.get_rate_card_for_user(db, card_id, user)

    estimates = await _list_estimates_for_card(db, card_id)
    if not user.is_admin:
        estimates = [estimate for estimate in estimates if can_access_estimate(estimate, user)]

    return [
        RateCardEstimateUsage(
            estimate_id=estimate.id,
            project_name=estimate.project_name,
            client_name=estimate.client_name,
            status=estimate.status,
            updated_at=estimate.updated_at,
        )
        for estimate in estimates
    ]


@router.post("/cards/{card_id}/ai/suggest", response_model=RateCardAiSuggestResponse)
async def suggest_rate_card_section(
    card_id: uuid.UUID,
    body: RateCardAiSuggestRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
):
    return await suggest_rate_card_section_for_card(db, card_id, body, user)


@router.post("/cards/{card_id}/duplicate", response_model=ActiveRateCardResponse, status_code=201)
async def duplicate_rate_card(
    card_id: uuid.UUID,
    body: RateCardDuplicate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
):
    source = await rate_card_service.get_rate_card_for_user(db, card_id, user)
    source_version = await _get_latest_version(db, source.id)
    if not source_version:
        raise HTTPException(
            status_code=404,
            detail={"error": "Rate card has no versions", "code": "RATE_CARD_NOT_FOUND"},
        )

    await rate_card_service.deactivate_all_rate_cards(db, user)

    new_card = RateCard(
        name=body.name.strip(),
        is_active=True,
        created_by=user.id,
        duplicated_from_rate_card_id=source.id,
    )
    db.add(new_card)
    await db.flush()

    version = RateCardVersion(
        rate_card_id=new_card.id,
        version_number=1,
        settings=normalize_settings_dict(source_version.settings),
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)

    return await _to_active_response(db, new_card, version)


@router.post("/cards/{card_id}/activate", response_model=ActiveRateCardResponse)
async def activate_rate_card(
    card_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
):
    rate_card = await rate_card_service.set_active_rate_card(db, card_id, user)

    version = await _get_latest_version(db, rate_card.id)
    if not version:
        raise HTTPException(
            status_code=404,
            detail={"error": "Rate card has no versions", "code": "RATE_CARD_NOT_FOUND"},
        )

    await db.commit()
    await db.refresh(version)

    return await _to_active_response(db, rate_card, version)


@router.delete("/cards/{card_id}", status_code=204)
async def delete_rate_card(
    card_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
):
    rate_card = await rate_card_service.get_rate_card_for_user(db, card_id, user)

    usage_count = await _count_estimates_using_card(db, card_id)
    if usage_count > 0:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Cannot delete rate card used by {usage_count} estimate(s)",
                "code": "RATE_CARD_IN_USE",
                "details": {"estimate_count": usage_count},
            },
        )

    if await rate_card_service.count_rate_cards_for_user(db, user) <= 1:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Cannot delete the only rate card",
                "code": "RATE_CARD_LAST",
            },
        )

    if rate_card.is_active:
        replacement_query = (
            select(RateCard)
            .where(RateCard.id != card_id)
            .order_by(RateCard.created_at.desc())
            .limit(1)
        )
        if not user.is_admin:
            replacement_query = replacement_query.where(RateCard.created_by == user.id)
        result = await db.execute(replacement_query)
        replacement = result.scalar_one_or_none()
        if not replacement:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Cannot delete the only rate card",
                    "code": "RATE_CARD_LAST",
                },
            )
        await rate_card_service.set_active_rate_card(db, replacement.id, user)

    await db.delete(rate_card)
    await db.commit()


@router.get("/active", response_model=ActiveRateCardResponse)
async def get_active_rate_card(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
):
    rate_card = await rate_card_service.get_active_rate_card(db, user)
    if not rate_card:
        raise HTTPException(
            status_code=404,
            detail={"error": "No active rate card", "code": "RATE_CARD_NOT_FOUND"},
        )

    version = await _get_latest_version(db, rate_card.id)
    if not version:
        raise HTTPException(
            status_code=404,
            detail={"error": "Active rate card has no versions", "code": "RATE_CARD_NOT_FOUND"},
        )

    return await _to_active_response(db, rate_card, version)


@router.get("/versions", response_model=list[RateCardVersionResponse])
async def list_rate_card_versions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
):
    rate_card = await rate_card_service.get_active_rate_card(db, user)
    if not rate_card:
        raise HTTPException(
            status_code=404,
            detail={"error": "No active rate card", "code": "RATE_CARD_NOT_FOUND"},
        )

    result = await db.execute(
        select(RateCardVersion)
        .where(RateCardVersion.rate_card_id == rate_card.id)
        .order_by(RateCardVersion.version_number.desc())
    )
    versions = list(result.scalars().all())
    responses: list[RateCardVersionResponse] = []
    for version in versions:
        estimate_count = await _count_estimates_using_version(db, version.id)
        responses.append(_to_version_response(version, estimate_count=estimate_count))
    return responses


@router.get("/versions/{version_id}", response_model=ActiveRateCardResponse)
async def get_rate_card_version(
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
):
    rate_card = await rate_card_service.get_active_rate_card(db, user)
    if not rate_card:
        raise HTTPException(
            status_code=404,
            detail={"error": "No active rate card", "code": "RATE_CARD_NOT_FOUND"},
        )

    version = await _get_version_for_rate_card(db, rate_card.id, version_id)
    return await _to_active_response(db, rate_card, version)


@router.patch("/versions/{version_id}", response_model=RateCardVersionResponse)
async def rename_rate_card_version(
    version_id: uuid.UUID,
    body: RateCardVersionLabelUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
):
    rate_card = await rate_card_service.get_active_rate_card(db, user)
    if not rate_card:
        raise HTTPException(
            status_code=404,
            detail={"error": "No active rate card", "code": "RATE_CARD_NOT_FOUND"},
        )

    version = await _get_version_for_rate_card(db, rate_card.id, version_id)
    version.label = body.label.strip()
    await db.commit()
    await db.refresh(version)

    estimate_count = await _count_estimates_using_version(db, version.id)
    return _to_version_response(version, estimate_count=estimate_count)


@router.put("/versions/{version_id}", response_model=ActiveRateCardResponse)
async def update_rate_card_version(
    version_id: uuid.UUID,
    body: RateCardVersionUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
):
    _validate_phase_percentages(body.settings)

    rate_card = await rate_card_service.get_active_rate_card(db, user)
    if not rate_card:
        raise HTTPException(
            status_code=404,
            detail={"error": "No active rate card", "code": "RATE_CARD_NOT_FOUND"},
        )

    version = await _get_version_for_rate_card(db, rate_card.id, version_id)

    if body.name:
        rate_card.name = body.name.strip()

    version.settings = _serialize_settings(body.settings)
    if body.label is not None:
        version.label = body.label.strip() or None

    await db.commit()
    await db.refresh(version)

    return await _to_active_response(db, rate_card, version)


@router.delete("/versions/{version_id}", status_code=204)
async def delete_rate_card_version(
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
):
    rate_card = await rate_card_service.get_active_rate_card(db, user)
    if not rate_card:
        raise HTTPException(
            status_code=404,
            detail={"error": "No active rate card", "code": "RATE_CARD_NOT_FOUND"},
        )

    version = await _get_version_for_rate_card(db, rate_card.id, version_id)

    if await _count_versions(db, rate_card.id) <= 1:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Cannot delete the only rate card version",
                "code": "RATE_CARD_VERSION_LAST",
            },
        )

    usage_count = await _count_estimates_using_version(db, version_id)
    if usage_count > 0:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Cannot delete version used by {usage_count} estimate(s)",
                "code": "RATE_CARD_VERSION_IN_USE",
                "details": {"estimate_count": usage_count},
            },
        )

    await db.delete(version)
    await db.commit()


@router.put("/", response_model=ActiveRateCardResponse)
async def update_rate_card(
    body: RateCardUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
):
    _validate_phase_percentages(body.settings)

    rate_card = await rate_card_service.get_active_rate_card(db, user)
    if not rate_card:
        raise HTTPException(
            status_code=404,
            detail={"error": "No active rate card", "code": "RATE_CARD_NOT_FOUND"},
        )

    if body.name:
        rate_card.name = body.name.strip()

    result = await db.execute(
        select(func.max(RateCardVersion.version_number)).where(
            RateCardVersion.rate_card_id == rate_card.id
        )
    )
    max_version = result.scalar_one_or_none() or 0

    version = RateCardVersion(
        rate_card_id=rate_card.id,
        version_number=max_version + 1,
        label=body.version_label.strip() if body.version_label else None,
        settings=_serialize_settings(body.settings),
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)

    return await _to_active_response(db, rate_card, version)
