import asyncio
import uuid
from typing import Any, Literal

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.factory import get_ai_provider
from app.ai.instruction_resolver import resolve_instructions
from app.ai.prompts import build_rate_card_system_prompt
from app.ai.schemas import GeneratedLineItem, GeneratedRateCardSuggestion
from app.audit.service import log_change
from app.calculation.schemas import RateCardSettings
from app.documents.service import run_extraction as run_document_extraction
from app.exceptions import AppError
from app.i18n.localized_content import resolve_localized_dict
from app.estimates.rate_card_stale import (
    get_rate_card_auto_tune_enabled,
    mark_rate_card_auto_tune_enabled,
)
from app.models.estimate import Estimate, EstimateDocument, EstimateStatus
from app.models.rate_card import RateCard
from app.models.user import User
from app.rate_cards.complexity import ProjectComplexityProfile, score_project_complexity
from app.rate_cards.cost_breakdown_hints import build_cost_breakdown_hints
from app.rate_cards.defaults import DEFAULT_RATE_CARD_SETTINGS
from app.rate_cards.normalize import normalize_settings_dict
from app.rate_cards.maintenance import apply_default_maintenance_to_settings
from app.rate_cards.regional_profiles import patch_roles_to_regional_standard
from app.rate_cards.service import create_rate_card_with_settings, get_latest_version_for_card
from app.rate_cards.standard_rates import ensure_standard_roles

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


def _feature_items_from_estimate(estimate: Estimate) -> list[dict[str, Any]]:
    return [
        {
            "name": item.name,
            "hours": float(item.hours),
            "phase": item.phase,
            "role": item.role,
            "description": item.description,
        }
        for item in sorted(estimate.feature_items, key=lambda row: row.sort_order)
    ]


def _build_rate_card_generation_context(
    estimate: Estimate,
    locale: Literal["ja", "en"],
    *,
    document_texts: list[str] | None = None,
    extracted_data: dict[str, Any] | None = None,
    feature_items: list[dict[str, Any]] | None = None,
    complexity_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    content_locale = estimate.locale if estimate.locale in ("ja", "en") else locale
    form_data = resolve_localized_dict(estimate.form_data, locale, content_locale)

    if extracted_data is None and estimate.extracted_data is not None:
        extracted_data = resolve_localized_dict(estimate.extracted_data, locale, content_locale)

    if feature_items is None and estimate.feature_items:
        feature_items = _feature_items_from_estimate(estimate)

    if (
        complexity_profile is None
        and extracted_data is not None
        and isinstance(extracted_data.get("complexity_profile"), dict)
    ):
        complexity_profile = extracted_data["complexity_profile"]
    elif (
        complexity_profile is None
        and feature_items is not None
        and extracted_data is not None
    ):
        complexity_profile = score_project_complexity(
            feature_items=feature_items,
            extracted_data=extracted_data,
            form_data=form_data,
        ).model_dump()

    if document_texts is None:
        document_texts = _collect_document_texts(list(estimate.documents))

    cost_breakdown_hints = build_cost_breakdown_hints(
        form_data,
        extracted_data,
        complexity_profile,
    )

    return {
        "project_name": estimate.project_name,
        "client_name": estimate.client_name,
        "form_data": form_data,
        "document_texts": document_texts,
        "feature_items": feature_items,
        "extracted_data": extracted_data,
        "complexity_profile": complexity_profile,
        "cost_breakdown_hints": cost_breakdown_hints,
    }


async def _count_estimates_for_rate_card(db: AsyncSession, rate_card_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(Estimate)
        .where(Estimate.rate_card_id == rate_card_id)
    )
    return int(result.scalar_one())


async def is_estimate_owned_rate_card(db: AsyncSession, estimate: Estimate) -> bool:
    if not estimate.rate_card_id:
        return False
    rate_card = await db.get(RateCard, estimate.rate_card_id)
    if rate_card is None or rate_card.is_system:
        return False
    linked_count = await _count_estimates_for_rate_card(db, estimate.rate_card_id)
    return linked_count <= 1


async def should_tune_rate_card_on_extract(db: AsyncSession, estimate: Estimate) -> bool:
    if not estimate.rate_card_id:
        return False
    if not get_rate_card_auto_tune_enabled(estimate):
        return False
    return True


async def should_auto_tune_rate_card(db: AsyncSession, estimate: Estimate) -> bool:
    if not estimate.rate_card_id:
        return False
    if not get_rate_card_auto_tune_enabled(estimate):
        return False
    rate_card = await db.get(RateCard, estimate.rate_card_id)
    if rate_card is not None and rate_card.is_system:
        return False
    linked_count = await _count_estimates_for_rate_card(db, estimate.rate_card_id)
    return linked_count <= 1


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


def _line_item_from_suggestion(item: GeneratedLineItem) -> dict[str, Any]:
    row: dict[str, Any] = {
        "name": item.name.strip(),
        "amount": int(item.amount_jpy),
    }
    if item.service_description and item.service_description.strip():
        row["service_description"] = item.service_description.strip()
    return row


def _suggestion_to_settings_dict(suggestion: GeneratedRateCardSuggestion) -> dict[str, Any]:
    roles = []
    for role in suggestion.roles:
        hourly = int(role.hourly_rate_jpy)
        roles.append(
            {
                "name": role.name.strip(),
                "hourly_rate": hourly,
                "daily_rate": hourly * HOURS_PER_DAY,
            }
        )

    monthly_items = [
        _line_item_from_suggestion(item)
        for item in suggestion.monthly_rc_items
        if item.name.strip()
    ]

    return ensure_standard_roles(
        normalize_settings_dict(
            {
                "cost_breakdown_mode": "flexible",
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
                    _line_item_from_suggestion(item)
                    for item in suggestion.setup_cost_items
                    if item.name.strip()
                ],
                "monthly_rc_items": monthly_items,
            }
        )
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

    settings_dict["cost_breakdown_mode"] = "flexible"
    settings_dict, _ = patch_roles_to_regional_standard(settings_dict)

    return normalize_settings_dict(settings_dict), sorted(set(default_fields))


async def _call_generate_rate_card(
    db: AsyncSession,
    context: dict[str, Any],
    locale: Literal["ja", "en"],
) -> GeneratedRateCardSuggestion:
    provider = await get_ai_provider(db)
    has_extraction_context = bool(
        context.get("feature_items")
        or context.get("extracted_data")
        or context.get("complexity_profile")
    )
    instructions = await resolve_instructions(
        db,
        "rate_card_generation",
        locale,
        build_base_system=build_rate_card_system_prompt,
        system_kwargs={
            "locale": locale,
            "has_extraction_context": has_extraction_context,
        },
    )
    return await provider.generate_rate_card(
        project_name=context["project_name"],
        client_name=context["client_name"],
        form_data=context["form_data"],
        document_texts=context["document_texts"],
        locale=locale,
        feature_items=context.get("feature_items"),
        extracted_data=context.get("extracted_data"),
        complexity_profile=context.get("complexity_profile"),
        cost_breakdown_hints=context.get("cost_breakdown_hints"),
        instructions=instructions,
    )


async def _apply_generated_settings_to_estimate_card(
    db: AsyncSession,
    estimate: Estimate,
    user_id: uuid.UUID,
    generated: dict[str, Any],
    *,
    audit_action: str = "rate_card_regenerated",
    maintenance_assumptions: dict[str, Any] | None = None,
) -> None:
    if not estimate.rate_card_id:
        return

    rate_card = await db.get(RateCard, estimate.rate_card_id)
    if not rate_card:
        return

    version = await get_latest_version_for_card(db, rate_card.id)
    version.settings = apply_default_maintenance_to_settings(
        generated["settings"],
        maintenance_assumptions,
    )
    await log_change(
        db,
        estimate_id=estimate.id,
        user_id=user_id,
        action=audit_action,
        changes={
            "rate_card_id": str(rate_card.id),
            "generation_notes": generated.get("generation_notes", ""),
            "used_defaults": generated.get("used_defaults", False),
            "complexity_level": (generated.get("complexity_profile") or {}).get("level"),
        },
    )


def _generation_result_from_suggestion(
    card_name: str,
    suggestion: GeneratedRateCardSuggestion,
    *,
    document_texts: list[str],
    complexity_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings_dict, default_fields = _merge_with_defaults(suggestion)
    settings = _validate_settings(settings_dict)
    used_defaults = bool(default_fields) or not document_texts
    return {
        "name": card_name,
        "settings": normalize_settings_dict(settings.model_dump()),
        "generation_notes": suggestion.generation_notes.strip(),
        "used_defaults": used_defaults,
        "default_fields": default_fields,
        "complexity_profile": complexity_profile,
    }


async def generate_rate_card_for_estimate(
    db: AsyncSession,
    estimate_id: uuid.UUID,
    user: User,
) -> dict[str, Any]:
    from app.estimates.service import get_estimate_for_user

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
        .options(
            selectinload(Estimate.documents),
            selectinload(Estimate.feature_items),
        )
    )
    estimate = result.scalar_one()
    locale: Literal["ja", "en"] = "ja" if estimate.locale == "ja" else "en"
    context = _build_rate_card_generation_context(estimate, locale)

    try:
        suggestion = await _call_generate_rate_card(db, context, locale)
        return _generation_result_from_suggestion(
            card_name,
            suggestion,
            document_texts=context["document_texts"],
            complexity_profile=context.get("complexity_profile"),
        )
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


async def _fork_rate_card_from_shared(
    db: AsyncSession,
    estimate: Estimate,
    user_id: uuid.UUID,
    generated: dict[str, Any],
    *,
    source_rate_card_id: uuid.UUID,
    maintenance_assumptions: dict[str, Any] | None = None,
) -> None:
    user = await db.get(User, user_id)
    if not user:
        return

    current_settings: dict[str, Any] = {}
    version = await get_latest_version_for_card(db, source_rate_card_id)
    if version and version.settings:
        current_settings = dict(version.settings)

    merged_settings = normalize_settings_dict(
        {
            **normalize_settings_dict(current_settings),
            **generated["settings"],
        }
    )
    merged_settings = apply_default_maintenance_to_settings(
        merged_settings,
        maintenance_assumptions,
    )

    card_name = generated.get("name") or estimate.project_name.strip() or "Generated Rate Card"
    card, _version = await create_rate_card_with_settings(
        db,
        user=user,
        name=card_name,
        settings=merged_settings,
        activate=False,
    )
    estimate.rate_card_id = card.id
    await log_change(
        db,
        estimate_id=estimate.id,
        user_id=user_id,
        action="rate_card_forked_from_shared",
        changes={
            "source_rate_card_id": str(source_rate_card_id),
            "new_rate_card_id": str(card.id),
            "generation_notes": generated.get("generation_notes", ""),
            "used_defaults": generated.get("used_defaults", False),
            "complexity_level": (generated.get("complexity_profile") or {}).get("level"),
        },
    )


async def regenerate_rate_card_after_extraction(
    db: AsyncSession,
    estimate_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    complexity_profile: ProjectComplexityProfile | dict[str, Any],
    maintenance_assumptions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = await db.execute(
        select(Estimate)
        .where(Estimate.id == estimate_id)
        .options(
            selectinload(Estimate.documents),
            selectinload(Estimate.feature_items),
        )
    )
    estimate = result.scalar_one()
    locale: Literal["ja", "en"] = "ja" if estimate.locale == "ja" else "en"
    profile_dict = (
        complexity_profile.model_dump()
        if isinstance(complexity_profile, ProjectComplexityProfile)
        else complexity_profile
    )
    context = _build_rate_card_generation_context(
        estimate,
        locale,
        complexity_profile=profile_dict,
    )
    card_name = estimate.project_name.strip() or "Generated Rate Card"
    suggestion = await _call_generate_rate_card(db, context, locale)
    generated = _generation_result_from_suggestion(
        card_name,
        suggestion,
        document_texts=context["document_texts"],
        complexity_profile=profile_dict,
    )
    if not await is_estimate_owned_rate_card(db, estimate):
        source_rate_card_id = estimate.rate_card_id
        await _fork_rate_card_from_shared(
            db,
            estimate,
            user_id,
            generated,
            source_rate_card_id=source_rate_card_id,
            maintenance_assumptions=maintenance_assumptions,
        )
    else:
        await _apply_generated_settings_to_estimate_card(
            db,
            estimate,
            user_id,
            generated,
            audit_action="rate_card_auto_tuned",
            maintenance_assumptions=maintenance_assumptions,
        )
    return generated


async def ensure_rate_card_for_estimate(
    db: AsyncSession,
    estimate_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    regenerate: bool = False,
    fast_bootstrap: bool = False,
) -> uuid.UUID:
    result = await db.execute(select(Estimate).where(Estimate.id == estimate_id))
    estimate = result.scalar_one()

    if estimate.rate_card_id and not regenerate:
        return estimate.rate_card_id

    user = await db.get(User, user_id)
    if not user:
        raise AppError("User not found", "USER_NOT_FOUND", status_code=404)

    card_name = estimate.project_name.strip() or "Generated Rate Card"
    if fast_bootstrap:
        generated = _default_generation_result(
            card_name,
            notes=(
                "Standard default rate card applied for faster requirement extraction. "
                "Use Generate rate card on the estimate page to customize rates with AI."
            ),
            default_fields=["all"],
        )
    else:
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
    estimate.maintenance_assumptions = mark_rate_card_auto_tune_enabled(
        estimate.maintenance_assumptions or {},
        enabled=True,
    )

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
            "auto_tune": True,
        },
    )
    await db.commit()
    return card.id
