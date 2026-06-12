import asyncio
import uuid
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
from app.estimates.rate_card_stale import RATE_CARD_FINGERPRINT_KEY
from app.rate_cards.fingerprint import get_latest_rate_card_fingerprint


async def _get_rate_card_roles(
    db: AsyncSession,
    rate_card_id: uuid.UUID,
    user: User,
) -> list[dict[str, Any]] | None:
    from app.rate_cards.service import get_rate_card_roles

    return await get_rate_card_roles(db, rate_card_id, user)


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

    for _ in range(2):
        try:
            return await provider.extract_requirements(
                form_data,
                document_texts,
                locale,
                rate_card_roles=rate_card_roles,
            )
        except ValidationError as exc:
            last_error = exc
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

    if estimate.status not in (
        EstimateStatus.DRAFT.value,
        EstimateStatus.REVIEW.value,
        EstimateStatus.CALCULATED.value,
        EstimateStatus.EXPORTED.value,
    ):
        return

    from app.rate_cards.generation import ensure_rate_card_for_estimate

    await ensure_rate_card_for_estimate(
        db,
        estimate_id,
        user_id,
        regenerate=False,
    )

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

    await db.execute(delete(FeatureItem).where(FeatureItem.estimate_id == estimate_id))
    estimate.extracted_data = None
    estimate.maintenance_assumptions = {}
    estimate.calculation_result = None
    estimate.rate_card_version_id = None

    estimate.status = EstimateStatus.EXTRACTING.value
    await log_change(
        db,
        estimate_id=estimate.id,
        user_id=user_id,
        action="extraction_started",
        changes={"status": EstimateStatus.EXTRACTING.value},
    )
    await db.commit()

    try:
        await _extract_pending_documents(db, estimate_id)

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

        ai_result = await _call_ai_provider(
            db,
            form_data,
            document_texts,
            locale,
            rate_card_roles,
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
        estimate.extracted_data = store_localized_dict(
            estimate.extracted_data,
            locale,
            extracted_payload,
        )
        maintenance_assumptions = ai_result.maintenance_assumptions.model_dump()
        estimate.status = EstimateStatus.REVIEW.value

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
    if "invalid api key" in lowered or "authentication" in lowered or "401" in message:
        return "Invalid API key. Check Admin → AI settings."
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
    documents = list(estimate.documents)
    documents_done = sum(
        1 for doc in documents if doc.extraction_status in ("done", "failed")
    )

    extraction_progress: dict[str, Any] | None = None
    if estimate.status == EstimateStatus.EXTRACTING.value:
        extraction_progress = {
            "documents_total": len(documents),
            "documents_done": documents_done,
        }

    return {
        "status": estimate.status,
        "extraction_progress": extraction_progress,
        "extraction_error": await _get_last_extraction_error(db, estimate_id)
        if estimate.status == EstimateStatus.DRAFT.value
        else None,
    }
