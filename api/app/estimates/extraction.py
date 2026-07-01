import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Literal

from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.factory import get_ai_provider
from app.ai.schemas import ExtractedRequirements
from app.audit.service import log_change
from app.documents.service import run_extraction as run_document_extraction
from app.exceptions import AppError
from app.i18n.localized_content import (
    normalize_locale,
    resolve_localized_dict,
    store_feature_item_localization,
    store_localized_dict,
)
from app.estimates.access import require_estimate_access
from app.models.audit import AuditLog
from app.models.estimate import Estimate, EstimateDocument, EstimateStatus, FeatureItem
from app.models.user import User
from app.estimates.rate_card_stale import (
    RATE_CARD_AUTO_TUNE_KEY,
    RATE_CARD_FINGERPRINT_KEY,
    RATE_CARD_TUNE_RECOMMENDED_KEY,
    has_completed_extraction,
    mark_rate_card_auto_tune_enabled,
    mark_rate_card_tune_recommended,
)
from app.rate_cards.complexity import score_project_complexity
from app.rate_cards.fingerprint import get_latest_rate_card_fingerprint
from app.rate_cards.generation import (
    regenerate_rate_card_after_extraction,
    should_tune_rate_card_on_extract,
)

logger = logging.getLogger(__name__)

STUCK_EXTRACTION_MINUTES = 5
EXTRACTION_AI_TIMEOUT_SECONDS = 120.0
STUCK_EXTRACTION_ERROR = (
    "Extraction was interrupted or timed out. Please try again."
)


def is_extraction_stuck(estimate: Estimate, *, minutes: int = STUCK_EXTRACTION_MINUTES) -> bool:
    if estimate.status != EstimateStatus.EXTRACTING.value:
        return False
    threshold = datetime.utcnow() - timedelta(minutes=minutes)
    updated_at = estimate.updated_at
    if updated_at.tzinfo is not None:
        updated_at = updated_at.replace(tzinfo=None)
    return updated_at < threshold


async def _recover_stuck_extraction(
    db: AsyncSession,
    estimate: Estimate,
    user_id: uuid.UUID,
) -> None:
    estimate.status = EstimateStatus.DRAFT.value
    await log_change(
        db,
        estimate_id=estimate.id,
        user_id=user_id,
        action="extraction_failed",
        changes={
            "status": EstimateStatus.DRAFT.value,
            "error": STUCK_EXTRACTION_ERROR,
            "recovered": True,
        },
    )
    await db.commit()


async def _get_rate_card_roles(
    db: AsyncSession,
    rate_card_id: uuid.UUID,
    user: User,
) -> list[dict[str, Any]] | None:
    from app.rate_cards.service import get_rate_card_roles

    return await get_rate_card_roles(db, rate_card_id, user)


async def _log_extraction_phase(
    db: AsyncSession,
    estimate_id: uuid.UUID,
    user_id: uuid.UUID,
    phase: Literal["documents", "rate_card", "ai", "rate_card_tune"],
) -> None:
    result = await db.execute(select(Estimate).where(Estimate.id == estimate_id))
    estimate = result.scalar_one_or_none()
    if estimate is not None:
        estimate.updated_at = datetime.utcnow()
    await log_change(
        db,
        estimate_id=estimate_id,
        user_id=user_id,
        action="extraction_phase",
        changes={"phase": phase},
    )
    await db.commit()


async def _get_extraction_phase(db: AsyncSession, estimate_id: uuid.UUID) -> str:
    result = await db.execute(
        select(AuditLog)
        .where(
            AuditLog.estimate_id == estimate_id,
            AuditLog.action == "extraction_phase",
        )
        .order_by(AuditLog.created_at.desc())
        .limit(1)
    )
    entry = result.scalar_one_or_none()
    if entry and isinstance(entry.changes.get("phase"), str):
        return entry.changes["phase"]
    return "ai"


async def _extract_pending_documents(db: AsyncSession, estimate_id: uuid.UUID) -> bool:
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
        return True
    return False


def _collect_document_texts(documents: list[EstimateDocument]) -> tuple[list[str], list[str]]:
    texts: list[str] = []
    skipped: list[str] = []

    for document in documents:
        if document.extraction_status == "done" and document.extracted_text:
            texts.append(document.extracted_text)
        elif document.extraction_status == "failed":
            skipped.append(document.original_filename)

    return texts, skipped


def _is_timeout_error(exc: BaseException) -> bool:
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return True
    name = type(exc).__name__
    return "Timeout" in name


async def _call_ai_provider(
    db: AsyncSession,
    form_data: dict[str, Any],
    document_texts: list[str],
    locale: Literal["ja", "en"],
    rate_card_roles: list[dict[str, Any]] | None,
) -> ExtractedRequirements:
    provider = await get_ai_provider(db)
    last_error: ValidationError | None = None

    for attempt in range(2):
        try:
            return await asyncio.wait_for(
                provider.extract_requirements(
                    form_data,
                    document_texts,
                    locale,
                    rate_card_roles=rate_card_roles,
                ),
                timeout=EXTRACTION_AI_TIMEOUT_SECONDS,
            )
        except ValidationError as exc:
            last_error = exc
            logger.warning(
                "Extraction AI validation failed (attempt %s/2): %s",
                attempt + 1,
                exc,
            )
        except asyncio.TimeoutError as exc:
            raise AppError(
                "AI request timed out",
                "AI_TIMEOUT",
                status_code=504,
            ) from exc
        except Exception as exc:
            if _is_timeout_error(exc):
                raise AppError(
                    "AI request timed out",
                    "AI_TIMEOUT",
                    status_code=504,
                ) from exc
            raise

    assert last_error is not None
    raise AppError(
        "AI returned invalid JSON",
        "AI_INVALID_JSON",
        status_code=502,
        details={"validation_errors": last_error.errors()},
    )


def _build_extracted_data(result: ExtractedRequirements, skipped_docs: list[str]) -> dict[str, Any]:
    confidence_notes = result.confidence_notes
    if skipped_docs:
        skipped_note = f"Skipped failed documents: {', '.join(skipped_docs)}"
        confidence_notes = f"{confidence_notes}\n{skipped_note}".strip()

    return {
        "functional_requirements": result.functional_requirements,
        "non_functional_requirements": result.non_functional_requirements,
        "user_roles": result.user_roles,
        "modules": result.modules,
        "external_systems": result.external_systems,
        "risks": result.risks,
        "gaps": result.gaps,
        "confidence_notes": confidence_notes,
        "confidence_score": result.confidence_score,
        "accuracy_level": result.accuracy_level,
        "confidence_factors": result.confidence_factors,
        "missing_inputs": result.missing_inputs,
        "recommendations": result.recommendations,
        "estimation_warnings": result.estimation_warnings,
        "assumption_risks": result.assumption_risks,
        "estimate_exclusions": result.estimate_exclusions,
        "estimate_type": result.estimate_type,
        "cost_drivers": [item.model_dump() for item in result.cost_drivers],
    }


async def begin_extraction(
    db: AsyncSession,
    estimate_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Literal["accepted", "already_running"]:
    """Mark an estimate as extracting before background work starts."""
    result = await db.execute(select(Estimate).where(Estimate.id == estimate_id))
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise AppError("Estimate not found", "NOT_FOUND", status_code=404)

    user = await db.get(User, user_id)
    if user is None:
        raise AppError("User not found", "NOT_FOUND", status_code=404)
    require_estimate_access(estimate, user)

    if estimate.status == EstimateStatus.EXTRACTING.value:
        if is_extraction_stuck(estimate):
            await _recover_stuck_extraction(db, estimate, user_id)
        else:
            return "already_running"

    if estimate.status not in (
        EstimateStatus.DRAFT.value,
        EstimateStatus.REVIEW.value,
        EstimateStatus.CALCULATED.value,
        EstimateStatus.EXPORTED.value,
    ):
        raise AppError(
            "Extraction can only be started from draft, review, calculated, or exported",
            "INVALID_STATUS",
            status_code=400,
        )

    estimate.status = EstimateStatus.EXTRACTING.value
    await log_change(
        db,
        estimate_id=estimate.id,
        user_id=user_id,
        action="extraction_started",
        changes={"status": EstimateStatus.EXTRACTING.value},
    )
    await db.commit()
    return "accepted"


async def run_extraction(
    db: AsyncSession,
    estimate_id: uuid.UUID,
    user_id: uuid.UUID,
    content_locale: str | None = None,
) -> None:
    result = await db.execute(
        select(Estimate)
        .where(Estimate.id == estimate_id)
        .options(
            selectinload(Estimate.feature_items),
            selectinload(Estimate.documents),
        )
    )
    estimate = result.scalar_one_or_none()
    if not estimate:
        return

    user = await db.get(User, user_id)
    if user is None:
        return
    require_estimate_access(estimate, user)

    if estimate.status != EstimateStatus.EXTRACTING.value:
        return

    from app.rate_cards.generation import ensure_rate_card_for_estimate

    had_prior_extraction = await has_completed_extraction(db, estimate_id)
    needs_rate_card = estimate.rate_card_id is None

    prior_maintenance = dict(estimate.maintenance_assumptions or {})
    preserved_flags = {
        key: prior_maintenance[key]
        for key in (RATE_CARD_AUTO_TUNE_KEY, RATE_CARD_TUNE_RECOMMENDED_KEY)
        if key in prior_maintenance
    }

    await db.execute(delete(FeatureItem).where(FeatureItem.estimate_id == estimate_id))
    estimate.extracted_data = None
    estimate.maintenance_assumptions = preserved_flags
    estimate.calculation_result = None
    estimate.rate_card_version_id = None
    await db.commit()

    try:
        extracted_documents = await _extract_pending_documents(db, estimate_id)
        if extracted_documents:
            await _log_extraction_phase(db, estimate_id, user_id, "documents")

        await ensure_rate_card_for_estimate(
            db,
            estimate_id,
            user_id,
            regenerate=False,
            fast_bootstrap=needs_rate_card,
        )

        await _log_extraction_phase(db, estimate_id, user_id, "ai")

        result = await db.execute(
            select(Estimate)
            .where(Estimate.id == estimate_id)
            .options(
                selectinload(Estimate.feature_items),
                selectinload(Estimate.documents),
            )
        )
        estimate = result.scalar_one()
        document_texts, skipped_docs = _collect_document_texts(list(estimate.documents))
        if not estimate.rate_card_id:
            raise AppError(
                "A rate card must be selected before extraction",
                "RATE_CARD_REQUIRED",
                status_code=400,
            )
        rate_card_roles = await _get_rate_card_roles(db, estimate.rate_card_id, user)
        locale: Literal["ja", "en"] = normalize_locale(content_locale, estimate.locale)  # type: ignore[assignment]
        estimate.locale = locale
        form_data = resolve_localized_dict(estimate.form_data, locale, estimate.locale)

        doc_chars = sum(len(text) for text in document_texts)
        logger.info(
            "Starting extraction AI for estimate %s (%s document chars, locale=%s)",
            estimate_id,
            doc_chars,
            locale,
        )
        ai_started = time.monotonic()
        ai_result = await _call_ai_provider(
            db,
            form_data,
            document_texts,
            locale,
            rate_card_roles,
        )
        logger.info(
            "Extraction AI completed for estimate %s in %.1fs (%s feature items)",
            estimate_id,
            time.monotonic() - ai_started,
            len(ai_result.feature_items),
        )

        await db.execute(delete(FeatureItem).where(FeatureItem.estimate_id == estimate_id))

        for index, item in enumerate(ai_result.feature_items):
            db.add(
                FeatureItem(
                    estimate_id=estimate_id,
                    sort_order=index,
                    name=item.name,
                    description=item.description,
                    hours=item.suggested_hours,
                    phase=item.phase,
                    role=item.role,
                    is_ai_generated=True,
                    localizations=store_feature_item_localization(
                        None,
                        locale,
                        name=item.name,
                        description=item.description,
                        phase=item.phase,
                        role=item.role,
                    ),
                )
            )

        extracted_payload = _build_extracted_data(ai_result, skipped_docs)
        feature_items_for_score = [
            {
                "name": item.name,
                "hours": float(item.suggested_hours),
                "phase": item.phase,
                "role": item.role,
            }
            for item in ai_result.feature_items
        ]
        complexity_profile = score_project_complexity(
            feature_items=feature_items_for_score,
            extracted_data=extracted_payload,
            form_data=form_data,
        )
        extracted_payload["complexity_profile"] = complexity_profile.model_dump()
        estimate.extracted_data = store_localized_dict(
            estimate.extracted_data,
            locale,
            extracted_payload,
        )
        maintenance_assumptions = ai_result.maintenance_assumptions.model_dump()
        prior_maintenance = estimate.maintenance_assumptions or {}
        if RATE_CARD_AUTO_TUNE_KEY in prior_maintenance:
            maintenance_assumptions[RATE_CARD_AUTO_TUNE_KEY] = prior_maintenance[RATE_CARD_AUTO_TUNE_KEY]
        estimate.status = EstimateStatus.REVIEW.value

        await db.flush()

        rate_card_auto_tuned = False
        rate_card_tune_recommended = False
        if await should_tune_rate_card_on_extract(db, estimate) and not had_prior_extraction:
            await _log_extraction_phase(db, estimate_id, user_id, "rate_card_tune")
            try:
                await regenerate_rate_card_after_extraction(
                    db,
                    estimate_id,
                    user_id,
                    complexity_profile=complexity_profile,
                    maintenance_assumptions=maintenance_assumptions,
                )
                rate_card_auto_tuned = True
                maintenance_assumptions = mark_rate_card_auto_tune_enabled(
                    maintenance_assumptions,
                    enabled=True,
                )
                maintenance_assumptions = mark_rate_card_tune_recommended(
                    maintenance_assumptions,
                    recommended=False,
                )
                result = await db.execute(
                    select(Estimate).where(Estimate.id == estimate_id)
                )
                estimate = result.scalar_one()
                if estimate.rate_card_id:
                    from app.estimates.feature_roles import align_feature_items_to_rate_card

                    await align_feature_items_to_rate_card(
                        db,
                        estimate_id,
                        estimate.rate_card_id,
                        user,
                        locale=locale,
                    )
            except Exception as exc:
                await log_change(
                    db,
                    estimate_id=estimate.id,
                    user_id=user_id,
                    action="rate_card_tune_failed",
                    changes={"error": str(exc)[:200]},
                )
                maintenance_assumptions = mark_rate_card_tune_recommended(
                    maintenance_assumptions,
                    recommended=True,
                )
        else:
            rate_card_tune_recommended = bool(estimate.rate_card_id)
            maintenance_assumptions = mark_rate_card_tune_recommended(
                maintenance_assumptions,
                recommended=rate_card_tune_recommended,
            )

        rate_card_fingerprint = None
        if estimate.rate_card_id:
            rate_card_fingerprint = await get_latest_rate_card_fingerprint(
                db,
                estimate.rate_card_id,
            )
        if rate_card_fingerprint:
            maintenance_assumptions[RATE_CARD_FINGERPRINT_KEY] = rate_card_fingerprint
        estimate.maintenance_assumptions = maintenance_assumptions

        await log_change(
            db,
            estimate_id=estimate.id,
            user_id=user_id,
            action="extraction_completed",
            changes={
                "status": EstimateStatus.REVIEW.value,
                "feature_item_count": len(ai_result.feature_items),
                "rate_card_fingerprint": rate_card_fingerprint,
                "complexity_level": complexity_profile.level,
                "rate_card_auto_tuned": rate_card_auto_tuned,
                "rate_card_tune_recommended": rate_card_tune_recommended,
            },
        )
        await db.commit()
    except Exception as exc:
        await db.rollback()
        result = await db.execute(select(Estimate).where(Estimate.id == estimate_id))
        estimate = result.scalar_one_or_none()
        if estimate:
            estimate.status = EstimateStatus.DRAFT.value
            friendly_error = _friendly_extraction_error(str(exc))
            await log_change(
                db,
                estimate_id=estimate.id,
                user_id=user_id,
                action="extraction_failed",
                changes={"status": EstimateStatus.DRAFT.value, "error": friendly_error},
            )
            await db.commit()


def _friendly_extraction_error(message: str) -> str:
    lowered = message.lower()
    if "rate limit" in lowered or "error code: 429" in lowered or "429" in message:
        return (
            "AI rate limit reached. Wait a minute and try again, "
            "or switch to gpt-4o-mini in Admin → AI settings."
        )
    if "invalid api key" in lowered or "authentication" in lowered or "401" in message:
        return "Invalid API key. Check Admin → AI settings."
    if "credit balance" in lowered or "purchase credits" in lowered:
        return (
            "Anthropic API credits are exhausted. Add credits at console.anthropic.com "
            "or switch to OpenAI in Admin → AI settings."
        )
    if "invalid schema" in lowered or "response_format" in lowered:
        return "AI configuration error. Contact your administrator."
    if "timeout" in lowered:
        return "AI request timed out. Please try again."
    if len(message) > 240:
        return message[:240] + "…"
    return message


async def _get_last_extraction_error(db: AsyncSession, estimate_id: uuid.UUID) -> str | None:
    result = await db.execute(
        select(AuditLog)
        .where(
            AuditLog.estimate_id == estimate_id,
            AuditLog.action.in_(
                ("extraction_failed", "extraction_completed", "extraction_started")
            ),
        )
        .order_by(AuditLog.created_at.desc())
        .limit(1)
    )
    entry = result.scalar_one_or_none()
    if not entry or entry.action != "extraction_failed":
        return None

    error = entry.changes.get("error")
    if not isinstance(error, str) or not error.strip():
        return "Extraction failed"
    return _friendly_extraction_error(error)


async def get_extraction_status(
    db: AsyncSession,
    estimate_id: uuid.UUID,
    user: User,
) -> dict[str, Any]:
    from app.estimates.service import get_estimate_for_user

    estimate = await get_estimate_for_user(db, estimate_id, user)

    if is_extraction_stuck(estimate):
        await _recover_stuck_extraction(db, estimate, user.id)
        return {
            "status": EstimateStatus.DRAFT.value,
            "extraction_progress": None,
            "extraction_error": STUCK_EXTRACTION_ERROR,
        }

    documents = list(estimate.documents)
    documents_done = sum(
        1 for doc in documents if doc.extraction_status in ("done", "failed")
    )
    documents_in_progress = any(
        doc.extraction_status in ("pending", "processing") for doc in documents
    )

    extraction_progress: dict[str, Any] | None = None
    if estimate.status == EstimateStatus.EXTRACTING.value:
        phase = await _get_extraction_phase(db, estimate_id)
        if documents_in_progress:
            phase = "documents"
        extraction_progress = {
            "documents_total": len(documents),
            "documents_done": documents_done,
            "phase": phase,
        }

    return {
        "status": estimate.status,
        "extraction_progress": extraction_progress,
        "extraction_error": await _get_last_extraction_error(db, estimate_id)
        if estimate.status == EstimateStatus.DRAFT.value
        else None,
    }
