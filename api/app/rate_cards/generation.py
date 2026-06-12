import asyncio
import uuid
from typing import Any, Literal

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.factory import get_ai_provider
from app.ai.schemas import GeneratedRateCardSuggestion
from app.calculation.schemas import RateCardSettings
from app.documents.service import run_extraction as run_document_extraction
from app.exceptions import AppError
from app.i18n.localized_content import resolve_localized_dict
from app.estimates.service import get_estimate_for_user
from app.models.estimate import Estimate, EstimateDocument, EstimateStatus
from app.models.user import User
from app.rate_cards.defaults import DEFAULT_RATE_CARD_SETTINGS
from app.rate_cards.normalize import normalize_settings_dict

HOURS_PER_DAY = 8
DEFAULT_PHASES = DEFAULT_RATE_CARD_SETTINGS["phases"]


async def _extract_pending_documents(db: AsyncSession, estimate_id: uuid.UUID) -> None:
    result = await db.execute(
        select(EstimateDocument.id).where(
            EstimateDocument.estimate_id == estimate_id,
            EstimateDocument.extraction_status == "pending",
        )
    )
    pending_ids = list(result.scalars().all())
    await db.commit()

    if pending_ids:
        await asyncio.gather(*[run_document_extraction(doc_id) for doc_id in pending_ids])


def _collect_document_texts(documents: list) -> list[str]:
    texts: list[str] = []
    for document in documents:
        if document.extraction_status == "done" and document.extracted_text:
            texts.append(document.extracted_text)
    return texts


def _normalize_phase_percentages(phases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not phases:
        return list(DEFAULT_PHASES)

    total = sum(float(phase.get("percentage", 0)) for phase in phases)
    if total <= 0:
        return list(DEFAULT_PHASES)

    if abs(total - 1.0) <= 0.001:
        return phases

    return [
        {
            "name": phase["name"],
            "percentage": round(float(phase["percentage"]) / total, 4),
        }
        for phase in phases
    ]


def _suggestion_to_settings_dict(suggestion: GeneratedRateCardSuggestion) -> dict[str, Any]:
    roles = []
    for role in suggestion.roles:
        hourly = int(role.hourly_rate_jpy)
        roles.append(
            {
                "name": role.name.strip(),
                "hourly_rate_jpy": hourly,
                "daily_rate_jpy": hourly * HOURS_PER_DAY,
            }
        )

    return normalize_settings_dict(
        {
            "development_approach": suggestion.development_approach,
            "roles": roles,
            "phases": _normalize_phase_percentages(
                [{"name": phase.name, "percentage": phase.percentage} for phase in suggestion.phases]
            ),
            "contingency_rate": float(suggestion.contingency_rate),
            "overhead_rate": float(suggestion.overhead_rate),
            "tax_rate": float(suggestion.tax_rate),
            "productivity": {
                "hours_per_feature_default": int(suggestion.productivity.hours_per_feature_default),
            },
            "setup_cost_items": [
                {"name": item.name.strip(), "amount_jpy": int(item.amount_jpy)}
                for item in suggestion.setup_cost_items
                if item.name.strip()
            ],
            "monthly_rc_items": [
                {"name": item.name.strip(), "amount_jpy": int(item.amount_jpy)}
                for item in suggestion.monthly_rc_items
                if item.name.strip()
            ],
        }
    )


def _validate_settings(settings_dict: dict[str, Any]) -> RateCardSettings:
    normalized = normalize_settings_dict(settings_dict)
    settings = RateCardSettings.model_validate(normalized)

    total = sum(phase.percentage for phase in settings.phases)
    if abs(total - 1.0) > 0.001:
        raise ValidationError.from_exception_data(
            "RateCardSettings",
            [{"type": "value_error", "loc": ("phases",), "msg": "Phase percentages must sum to 1.0"}],
        )
    return settings


def _default_generation_result(name: str, *, notes: str, default_fields: list[str]) -> dict[str, Any]:
    settings = _validate_settings(DEFAULT_RATE_CARD_SETTINGS)
    return {
        "name": name,
        "settings": normalize_settings_dict(settings.model_dump()),
        "generation_notes": notes,
        "used_defaults": True,
        "default_fields": default_fields,
    }


def _merge_with_defaults(suggestion: GeneratedRateCardSuggestion) -> tuple[dict[str, Any], list[str]]:
    default_fields: list[str] = list(suggestion.used_default_assumptions)
    settings_dict = _suggestion_to_settings_dict(suggestion)

    if not settings_dict.get("roles"):
        settings_dict["roles"] = DEFAULT_RATE_CARD_SETTINGS["roles"]
        default_fields.append("roles")

    if not settings_dict.get("setup_cost_items"):
        settings_dict["setup_cost_items"] = DEFAULT_RATE_CARD_SETTINGS["setup_cost_items"]
        default_fields.append("setup_cost_items")

    if not settings_dict.get("monthly_rc_items"):
        settings_dict["monthly_rc_items"] = DEFAULT_RATE_CARD_SETTINGS["monthly_rc_items"]
        default_fields.append("monthly_rc_items")

    return normalize_settings_dict(settings_dict), sorted(set(default_fields))


async def generate_rate_card_for_estimate(
    db: AsyncSession,
    estimate_id: uuid.UUID,
    user: User,
) -> dict[str, Any]:
    estimate = await get_estimate_for_user(db, estimate_id, user)

    if estimate.status not in (EstimateStatus.DRAFT.value, EstimateStatus.REVIEW.value):
        raise AppError(
            "Rate card generation is only available for draft or review estimates",
            "INVALID_STATUS",
            status_code=400,
        )

    card_name = estimate.project_name.strip() or "Generated Rate Card"

    await _extract_pending_documents(db, estimate_id)

    result = await db.execute(
        select(Estimate)
        .where(Estimate.id == estimate_id)
        .options(selectinload(Estimate.documents))
    )
    estimate = result.scalar_one()
    document_texts = _collect_document_texts(list(estimate.documents))
    locale: Literal["ja", "en"] = "ja" if estimate.locale == "ja" else "en"

    try:
        provider = await get_ai_provider(db)
        suggestion = await provider.generate_rate_card(
            project_name=estimate.project_name,
            client_name=estimate.client_name,
            form_data=resolve_localized_dict(estimate.form_data, locale, estimate.locale),
            document_texts=document_texts,
            locale=locale,
        )
        settings_dict, default_fields = _merge_with_defaults(suggestion)
        settings = _validate_settings(settings_dict)
        used_defaults = bool(default_fields) or not document_texts
        return {
            "name": card_name,
            "settings": normalize_settings_dict(settings.model_dump()),
            "generation_notes": suggestion.generation_notes.strip(),
            "used_defaults": used_defaults,
            "default_fields": default_fields,
        }
    except Exception as exc:
        note = (
            "Insufficient project information or AI unavailable. "
            "Predefined default rate card values were applied."
        )
        if str(exc).strip():
            note = f"{note} ({str(exc).strip()[:200]})"
        return _default_generation_result(
            card_name,
            notes=note,
            default_fields=["all"],
        )


async def ensure_rate_card_for_estimate(
    db: AsyncSession,
    estimate_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    regenerate: bool = False,
) -> uuid.UUID:
    from app.audit.service import log_change
    from app.models.estimate import Estimate
    from app.models.rate_card import RateCard
    from app.rate_cards.service import create_rate_card_with_settings, get_latest_version_for_card

    result = await db.execute(select(Estimate).where(Estimate.id == estimate_id))
    estimate = result.scalar_one()

    if estimate.rate_card_id and not regenerate:
        return estimate.rate_card_id

    user = await db.get(User, user_id)
    if not user:
        raise AppError("User not found", "USER_NOT_FOUND", status_code=404)
    generated = await generate_rate_card_for_estimate(db, estimate_id, user)

    result = await db.execute(select(Estimate).where(Estimate.id == estimate_id))
    estimate = result.scalar_one()

    settings = generated["settings"]
    generated_name = generated["name"]

    if estimate.rate_card_id:
        rate_card = await db.get(RateCard, estimate.rate_card_id)
        if rate_card:
            version = await get_latest_version_for_card(db, rate_card.id)
            version.settings = settings
            await log_change(
                db,
                estimate_id=estimate.id,
                user_id=user_id,
                action="rate_card_regenerated",
                changes={
                    "rate_card_id": str(rate_card.id),
                    "generation_notes": generated.get("generation_notes", ""),
                    "used_defaults": generated.get("used_defaults", False),
                },
            )
            await db.commit()
            return rate_card.id

    card, _version = await create_rate_card_with_settings(
        db,
        user=user,
        name=generated_name,
        settings=settings,
        activate=False,
    )
    estimate.rate_card_id = card.id

    await log_change(
        db,
        estimate_id=estimate.id,
        user_id=user_id,
        action="rate_card_created",
        changes={
            "rate_card_id": str(card.id),
            "rate_card_name": card.name,
            "generation_notes": generated.get("generation_notes", ""),
            "used_defaults": generated.get("used_defaults", False),
        },
    )
    await db.commit()
    return card.id
