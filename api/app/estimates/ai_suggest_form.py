import uuid
from typing import Literal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.factory import get_ai_provider
from app.estimates.form_fields import (
    normalize_suggested_form_data,
    snapshot_fields,
    specification_schema,
)
from app.estimates.project_name import is_usable_project_name
from app.estimates.service import get_estimate_for_user
from app.exceptions import AppError
from app.i18n.localized_content import resolve_localized_dict
from app.models.estimate import Estimate, EstimateStatus
from app.models.user import User
from app.rate_cards.generation import _collect_document_texts, _extract_pending_documents
from app.schemas.estimate import EstimateAiSuggestFormRequest, EstimateAiSuggestFormResponse

DOCUMENT_ONLY_PROMPT = (
    "Analyze the uploaded documents and project context to suggest values for each "
    "questionnaire field."
)


async def suggest_form_for_estimate(
    db: AsyncSession,
    estimate_id: uuid.UUID,
    body: EstimateAiSuggestFormRequest,
    user: User,
) -> EstimateAiSuggestFormResponse:
    estimate = await get_estimate_for_user(db, estimate_id, user)

    if estimate.status != EstimateStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "AI form suggestion is only available for draft estimates",
                "code": "INVALID_STATUS",
            },
        )

    if not is_usable_project_name(estimate.project_name):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Enter a project name before generating AI suggestions",
                "code": "PROJECT_NAME_REQUIRED",
            },
        )

    locale: Literal["ja", "en"] = body.locale or (
        "ja" if estimate.locale == "ja" else "en"
    )
    content_locale = estimate.locale if estimate.locale in ("ja", "en") else locale

    await _extract_pending_documents(db, estimate.id)
    result = await db.execute(
        select(Estimate)
        .where(Estimate.id == estimate.id)
        .options(selectinload(Estimate.documents))
    )
    estimate = result.scalar_one()
    document_texts = _collect_document_texts(list(estimate.documents))
    prompt = body.prompt.strip()
    if not prompt and not document_texts:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Enter a prompt or upload at least one extracted document",
                "code": "PROMPT_OR_DOCUMENTS_REQUIRED",
            },
        )
    effective_prompt = prompt or DOCUMENT_ONLY_PROMPT
    current_form_data = resolve_localized_dict(
        estimate.form_data,
        locale,
        content_locale,
    )

    schema = snapshot_fields(estimate.form_schema_snapshot)
    spec_schema = specification_schema(schema)

    try:
        provider = await get_ai_provider(db)
        suggestion = await provider.suggest_estimate_form_fields(
            prompt=effective_prompt,
            project_name=estimate.project_name,
            client_name=estimate.client_name,
            current_form_data=current_form_data,
            document_texts=document_texts,
            locale=locale,
            form_schema=spec_schema,
        )
    except Exception as exc:
        raise AppError(
            "AI suggestion is unavailable",
            "AI_UNAVAILABLE",
            status_code=503,
            details={"message": str(exc)[:200]},
        ) from exc

    form_data = normalize_suggested_form_data(suggestion.form_data, schema)
    return EstimateAiSuggestFormResponse(
        form_data=form_data,
        generation_notes=suggestion.generation_notes.strip(),
    )
