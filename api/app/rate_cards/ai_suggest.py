import uuid
from typing import Any, Literal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.factory import get_ai_provider
from app.ai.instruction_resolver import ResolvedInstructions, merge_user_message, resolve_instructions
from app.ai.prompts import build_rate_card_section_system_prompt
from app.ai.schemas import (
    GeneratedLineItem,
    GeneratedPhasePercentage,
    GeneratedRoleRate,
)
from app.estimates.access import require_estimate_access
from app.rate_cards.access import require_rate_card_access
from app.exceptions import AppError
from app.models.user import User
from app.i18n.localized_content import resolve_localized_dict
from app.models.estimate import Estimate
from app.models.rate_card import RateCard, RateCardVersion
from app.rate_cards.generation import _collect_document_texts, _extract_pending_documents
from app.schemas.rate_card import (
    RateCardAiSuggestRequest,
    RateCardAiSuggestResponse,
    RateCardAiSection,
    RateCardEstimateUsage,
)

HOURS_PER_DAY = 8


async def _get_rate_card(db: AsyncSession, card_id: uuid.UUID) -> RateCard:
    result = await db.execute(select(RateCard).where(RateCard.id == card_id))
    rate_card = result.scalar_one_or_none()
    if not rate_card:
        raise HTTPException(
            status_code=404,
            detail={"error": "Rate card not found", "code": "RATE_CARD_NOT_FOUND"},
        )
    return rate_card


async def _get_latest_version(
    db: AsyncSession,
    rate_card_id: uuid.UUID,
) -> RateCardVersion | None:
    result = await db.execute(
        select(RateCardVersion)
        .where(RateCardVersion.rate_card_id == rate_card_id)
        .order_by(RateCardVersion.version_number.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _estimate_linked_to_card(
    db: AsyncSession,
    estimate: Estimate,
    card_id: uuid.UUID,
) -> bool:
    if estimate.rate_card_id == card_id:
        return True
    if estimate.rate_card_version_id:
        version = await db.get(RateCardVersion, estimate.rate_card_version_id)
        if version and version.rate_card_id == card_id:
            return True
    return False


def _normalize_name(value: str) -> str:
    return value.strip().casefold()


def _build_estimate_context(estimate: Estimate, locale: Literal["ja", "en"]) -> dict[str, Any]:
    content_locale = estimate.locale if estimate.locale in ("ja", "en") else locale
    form_data = resolve_localized_dict(estimate.form_data, locale, content_locale)
    extracted_data = resolve_localized_dict(estimate.extracted_data, locale, content_locale)
    maintenance = resolve_localized_dict(estimate.maintenance_assumptions, locale, content_locale)

    feature_items = [
        {
            "name": item.name,
            "hours": float(item.hours),
            "phase": item.phase,
            "role": item.role,
            "description": item.description,
        }
        for item in sorted(estimate.feature_items, key=lambda row: row.sort_order)
    ]

    calculation_summary: dict[str, Any] | None = None
    if estimate.calculation_result:
        result = estimate.calculation_result
        nrc = result.get("nrc") if isinstance(result.get("nrc"), dict) else {}
        rc = result.get("rc") if isinstance(result.get("rc"), dict) else {}
        calculation_summary = {
            "total_effort_hours": result.get("total_effort_hours"),
            "nrc_total_jpy": nrc.get("total_jpy"),
            "rc_monthly_jpy": rc.get("monthly_jpy"),
            "rc_annual_jpy": rc.get("annual_jpy"),
            "first_year_total_jpy": result.get("first_year_total_jpy"),
            "rate_card_version_id": result.get("rate_card_version_id"),
        }

    return {
        "project_name": estimate.project_name,
        "client_name": estimate.client_name,
        "status": estimate.status,
        "form_data": form_data,
        "extracted_data": extracted_data,
        "maintenance_assumptions": maintenance,
        "feature_items": feature_items,
        "calculation_summary": calculation_summary,
    }


def _roles_to_items(roles: list[GeneratedRoleRate]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for role in roles:
        hourly = int(role.hourly_rate_jpy)
        items.append(
            {
                "name": role.name.strip(),
                "hourly_rate_jpy": hourly,
                "daily_rate_jpy": hourly * HOURS_PER_DAY,
            }
        )
    return items


def _phases_to_items(phases: list[GeneratedPhasePercentage]) -> list[dict[str, Any]]:
    return [
        {"name": phase.name.strip(), "percentage": float(phase.percentage)}
        for phase in phases
        if phase.name.strip()
    ]


def _line_items_to_items(items: list[GeneratedLineItem]) -> list[dict[str, Any]]:
    return [
        {"name": item.name.strip(), "amount_jpy": int(item.amount_jpy)}
        for item in items
        if item.name.strip()
    ]


def _filter_new_items(
    section: RateCardAiSection,
    current_section: list[dict[str, Any]],
    suggested_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    existing_names = {_normalize_name(str(item.get("name", ""))) for item in current_section}
    return [
        item
        for item in suggested_items
        if _normalize_name(str(item.get("name", ""))) not in existing_names
    ]


def _post_process_section_items(
    section: RateCardAiSection,
    current_section: list[dict[str, Any]],
    raw_items: list[dict[str, Any]],
    replace_all: bool,
) -> tuple[list[dict[str, Any]], bool]:
    if section == "phases" and replace_all:
        total = sum(float(item.get("percentage", 0)) for item in raw_items)
        if abs(total - 1.0) <= 0.001:
            return raw_items, True
        return _filter_new_items(section, current_section, raw_items), False

    return _filter_new_items(section, current_section, raw_items), False


async def suggest_rate_card_section_for_card(
    db: AsyncSession,
    card_id: uuid.UUID,
    body: RateCardAiSuggestRequest,
    user: User,
) -> RateCardAiSuggestResponse:
    rate_card = await _get_rate_card(db, card_id)
    require_rate_card_access(rate_card, user)

    version = await _get_latest_version(db, rate_card.id)
    if not version:
        raise HTTPException(
            status_code=404,
            detail={"error": "Rate card has no versions", "code": "RATE_CARD_NOT_FOUND"},
        )

    settings = version.settings or {}
    current_section = list(settings.get(body.section, []))
    free_form = body.estimate_id is None
    estimate_usage: RateCardEstimateUsage | None = None
    document_texts: list[str] = []
    estimate_context: dict[str, Any] = {}
    locale: Literal["ja", "en"] = body.locale or "en"

    if not free_form:
        result = await db.execute(
            select(Estimate)
            .where(Estimate.id == body.estimate_id)
            .options(
                selectinload(Estimate.documents),
                selectinload(Estimate.feature_items),
            )
        )
        estimate = result.scalar_one_or_none()
        if not estimate:
            raise AppError("Estimate not found", "ESTIMATE_NOT_FOUND", status_code=404)
        require_estimate_access(estimate, user)

        if not await _estimate_linked_to_card(db, estimate, card_id):
            raise AppError(
                "Estimate is not linked to this rate card",
                "ESTIMATE_NOT_LINKED",
                status_code=404,
            )

        locale = body.locale or ("ja" if estimate.locale == "ja" else "en")

        await _extract_pending_documents(db, estimate.id)
        result = await db.execute(
            select(Estimate)
            .where(Estimate.id == estimate.id)
            .options(
                selectinload(Estimate.documents),
                selectinload(Estimate.feature_items),
            )
        )
        estimate = result.scalar_one()
        document_texts = _collect_document_texts(list(estimate.documents))
        estimate_context = _build_estimate_context(estimate, locale)
        estimate_usage = RateCardEstimateUsage(
            estimate_id=estimate.id,
            project_name=estimate.project_name,
            client_name=estimate.client_name,
            status=estimate.status,
            updated_at=estimate.updated_at,
        )

    try:
        provider = await get_ai_provider(db)
        instructions = await resolve_instructions(
            db,
            "rate_card_section",
            locale,
            build_base_system=build_rate_card_section_system_prompt,
            system_kwargs={
                "locale": locale,
                "section": body.section,
                "free_form": free_form,
            },
        )
        runtime_prompt = merge_user_message(instructions.user_prefix, body.prompt.strip())
        instructions_for_adapter = ResolvedInstructions(
            system=instructions.system,
            user_prefix="",
            parameters=instructions.parameters,
        )
        suggestion = await provider.suggest_rate_card_section(
            section=body.section,
            prompt=runtime_prompt,
            current_section=current_section,
            estimate_context=estimate_context,
            document_texts=document_texts,
            locale=locale,
            free_form=free_form,
            instructions=instructions_for_adapter,
        )
    except Exception as exc:
        raise AppError(
            "AI suggestion is unavailable",
            "AI_UNAVAILABLE",
            status_code=503,
            details={"message": str(exc)[:200]},
        ) from exc

    if body.section == "roles":
        raw_items = _roles_to_items(suggestion.items)
        replace_all = False
        generation_notes = suggestion.generation_notes
    elif body.section == "phases":
        raw_items = _phases_to_items(suggestion.items)
        replace_all = bool(getattr(suggestion, "replace_all", False))
        generation_notes = suggestion.generation_notes
    else:
        raw_items = _line_items_to_items(suggestion.items)
        replace_all = False
        generation_notes = suggestion.generation_notes

    items, replace_all = _post_process_section_items(
        body.section,
        current_section,
        raw_items,
        replace_all,
    )

    return RateCardAiSuggestResponse(
        section=body.section,
        items=items,
        generation_notes=generation_notes.strip(),
        replace_all=replace_all,
        estimate=estimate_usage,
    )
