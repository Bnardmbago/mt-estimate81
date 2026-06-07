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
from app.models.estimate import Estimate, EstimateDocument, EstimateStatus, FeatureItem
from app.models.rate_card import RateCard, RateCardVersion


async def _get_rate_card_roles(db: AsyncSession) -> list[dict[str, Any]] | None:
    result = await db.execute(
        select(RateCardVersion)
        .join(RateCard)
        .where(RateCard.is_active.is_(True))
        .order_by(RateCardVersion.created_at.desc())
        .limit(1)
    )
    version = result.scalar_one_or_none()
    if not version:
        return None
    roles = version.settings.get("roles")
    return roles if isinstance(roles, list) else None


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
    form_data: dict[str, Any],
    document_texts: list[str],
    locale: Literal["ja", "en"],
    rate_card_roles: list[dict[str, Any]] | None,
) -> ExtractedRequirements:
    provider = get_ai_provider()
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
    }


async def run_extraction(
    db: AsyncSession,
    estimate_id: uuid.UUID,
    user_id: uuid.UUID,
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

    if estimate.status not in (EstimateStatus.DRAFT.value, EstimateStatus.REVIEW.value):
        return

    await db.execute(delete(FeatureItem).where(FeatureItem.estimate_id == estimate_id))
    estimate.extracted_data = None
    estimate.maintenance_assumptions = {}

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
        rate_card_roles = await _get_rate_card_roles(db)
        locale: Literal["ja", "en"] = "ja" if estimate.locale == "ja" else "en"

        ai_result = await _call_ai_provider(
            estimate.form_data,
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
                )
            )

        estimate.extracted_data = _build_extracted_data(ai_result, skipped_docs)
        estimate.maintenance_assumptions = ai_result.maintenance_assumptions.model_dump()
        estimate.status = EstimateStatus.REVIEW.value

        await log_change(
            db,
            estimate_id=estimate.id,
            user_id=user_id,
            action="extraction_completed",
            changes={
                "status": EstimateStatus.REVIEW.value,
                "feature_item_count": len(ai_result.feature_items),
            },
        )
        await db.commit()
    except Exception as exc:
        await db.rollback()
        result = await db.execute(select(Estimate).where(Estimate.id == estimate_id))
        estimate = result.scalar_one_or_none()
        if estimate:
            estimate.status = EstimateStatus.DRAFT.value
            await log_change(
                db,
                estimate_id=estimate.id,
                user_id=user_id,
                action="extraction_failed",
                changes={"status": EstimateStatus.DRAFT.value, "error": str(exc)},
            )
            await db.commit()
        raise


async def get_extraction_status(db: AsyncSession, estimate_id: uuid.UUID) -> dict[str, Any]:
    result = await db.execute(
        select(Estimate)
        .where(Estimate.id == estimate_id)
        .options(selectinload(Estimate.documents))
    )
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise AppError("Estimate not found", "ESTIMATE_NOT_FOUND", status_code=404)

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
    }
