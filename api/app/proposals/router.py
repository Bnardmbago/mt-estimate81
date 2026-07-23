from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, require_full_account
from app.models.user import User
from app.proposals import export_service, service
from app.schemas.export import ExportEmailRequest, ExportEmailResponse
from app.schemas.proposal import (
    ProposalDetail,
    ProposalExportRecord,
    ProposalExportRequest,
    ProposalGenerateRequest,
    ProposalRegenerateRequest,
    ProposalSectionsPatchRequest,
    ProposalStatusResponse,
    ProposalSummary,
)

router = APIRouter(prefix="/proposals", tags=["proposals"])


@router.get("", response_model=list[ProposalSummary])
async def list_proposals(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
) -> list[ProposalSummary]:
    return await service.list_proposals(db, user)


@router.get("/by-estimate/{estimate_id}", response_model=ProposalDetail)
async def get_proposal_by_estimate(
    estimate_id: uuid.UUID,
    locale: Literal["ja", "en"] = Query("en"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
) -> ProposalDetail:
    return await service.get_by_estimate(db, estimate_id, locale, user)


@router.post("/generate", response_model=ProposalDetail)
async def generate_proposal(
    body: ProposalGenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
) -> ProposalDetail:
    return await service.start_generate(
        db,
        user,
        estimate_id=body.estimate_id,
        locale=body.locale,
        include_poc=body.include_poc,
        background_tasks=background_tasks,
    )


@router.get("/{proposal_id}", response_model=ProposalDetail)
async def get_proposal(
    proposal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
) -> ProposalDetail:
    proposal = await service.get_proposal_or_404(db, proposal_id, user)
    return await service.to_detail(db, proposal, user)


@router.delete("/{proposal_id}", status_code=204, response_class=Response)
async def delete_proposal(
    proposal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
) -> Response:
    await service.delete_proposal(db, user, proposal_id)
    return Response(status_code=204)


@router.get("/{proposal_id}/status", response_model=ProposalStatusResponse)
async def get_proposal_status(
    proposal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
) -> ProposalStatusResponse:
    proposal = await service.get_proposal_or_404(db, proposal_id, user)
    return service.to_status(proposal)


@router.patch("/{proposal_id}/sections", response_model=ProposalDetail)
async def patch_proposal_sections(
    proposal_id: uuid.UUID,
    body: ProposalSectionsPatchRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
) -> ProposalDetail:
    return await service.patch_sections(db, user, proposal_id, body.sections)


@router.post("/{proposal_id}/regenerate", response_model=ProposalDetail)
async def regenerate_proposal(
    proposal_id: uuid.UUID,
    body: ProposalRegenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
) -> ProposalDetail:
    return await service.regenerate(
        db, user, proposal_id, body.part, background_tasks
    )


@router.post("/{proposal_id}/refresh", response_model=ProposalDetail)
async def refresh_proposal(
    proposal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
) -> ProposalDetail:
    return await service.refresh_from_estimate(db, user, proposal_id)


@router.post("/{proposal_id}/finalize", response_model=ProposalDetail)
async def finalize_proposal(
    proposal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
) -> ProposalDetail:
    return await service.finalize_proposal(db, user, proposal_id)


@router.post("/{proposal_id}/export", response_model=ProposalExportRecord)
async def create_proposal_export(
    proposal_id: uuid.UUID,
    body: ProposalExportRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
) -> ProposalExportRecord:
    row = await export_service.export_proposal(
        db,
        user,
        proposal_id,
        format=body.format,
        variant=body.variant,
        locale=body.locale,
        project_name=body.project_name,
    )
    return ProposalExportRecord.model_validate(row)


@router.get("/{proposal_id}/exports", response_model=list[ProposalExportRecord])
async def list_proposal_exports(
    proposal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
) -> list[ProposalExportRecord]:
    rows = await export_service.list_exports(db, user, proposal_id)
    return [ProposalExportRecord.model_validate(row) for row in rows]


@router.get("/{proposal_id}/exports/{export_id}/download")
async def download_proposal_export(
    proposal_id: uuid.UUID,
    export_id: uuid.UUID,
    inline: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
):
    return await export_service.download_export(
        db, user, proposal_id, export_id, inline=inline
    )


@router.delete("/{proposal_id}/exports/{export_id}", status_code=204, response_class=Response)
async def delete_proposal_export(
    proposal_id: uuid.UUID,
    export_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
) -> Response:
    await export_service.delete_export(db, user, proposal_id, export_id)
    return Response(status_code=204)


@router.post(
    "/{proposal_id}/exports/email",
    response_model=ExportEmailResponse,
)
async def email_proposal_exports(
    proposal_id: uuid.UUID,
    body: ExportEmailRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
) -> ExportEmailResponse:
    result = await export_service.send_exports_email(
        db,
        user,
        proposal_id,
        export_ids=body.export_ids,
        to_email=body.to_email,
        message=body.message,
    )
    return ExportEmailResponse.model_validate(result)
