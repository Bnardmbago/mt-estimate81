"""Admin API for proposal generation purpose presets."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.proposal_ai_config import (
    get_proposal_ai_settings,
    settings_response_payload,
    update_proposal_ai_settings,
)
from app.dependencies import get_db, require_admin
from app.models.user import User

router = APIRouter(prefix="/admin/proposal-ai-settings", tags=["admin"])

Purpose = Literal["concise", "standard", "detailed"]


class PurposePresetSummary(BaseModel):
    purpose: Purpose
    max_tokens: int
    timeout_seconds: int
    min_diagrams: int
    min_tables_proposal: int
    min_tables_poc: int


class ProposalAiSettingsResponse(BaseModel):
    assessment_purpose: Purpose
    proposal_purpose: Purpose
    poc_purpose: Purpose
    presets: list[PurposePresetSummary]
    purposes: list[Purpose]


class ProposalAiSettingsUpdate(BaseModel):
    assessment_purpose: Purpose | None = None
    proposal_purpose: Purpose | None = None
    poc_purpose: Purpose | None = None


@router.get("", response_model=ProposalAiSettingsResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    settings = await get_proposal_ai_settings(db)
    return ProposalAiSettingsResponse(**settings_response_payload(settings))


@router.put("", response_model=ProposalAiSettingsResponse)
async def put_settings(
    body: ProposalAiSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    patch = body.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(
            status_code=400,
            detail={"error": "At least one purpose must be provided", "code": "INVALID_SETTINGS"},
        )
    try:
        settings = await update_proposal_ai_settings(db, patch)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": str(exc), "code": "INVALID_PURPOSE"},
        ) from exc
    return ProposalAiSettingsResponse(**settings_response_payload(settings))
