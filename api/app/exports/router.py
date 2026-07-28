import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, require_full_account
from app.destinations import service as destination_service
from app.exports import service
from app.models.user import User
from app.schemas.export import (
    DestinationSendResponse,
    ExportEmailRequest,
    ExportEmailResponse,
    ExportRequest,
    ExportResponse,
)

router = APIRouter(tags=["exports"])


@router.post("/estimates/{estimate_id}/export", response_model=ExportResponse, status_code=201)
async def create_export(
    estimate_id: uuid.UUID,
    body: ExportRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await service.export_estimate(
        db,
        estimate_id,
        body.format,
        body.locale,
        user,
        theme_id=body.theme_id,
        style_id=body.style_id,
        template_id=body.template_id,
        include_cover=body.include_cover,
        cover_template_id=body.cover_template_id,
        cover_values=body.cover_values,
    )


@router.get("/estimates/{estimate_id}/exports", response_model=list[ExportResponse])
async def list_estimate_exports(
    estimate_id: uuid.UUID,
    audience: str | None = Query(default=None, pattern=r"^(client|internal)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await service.list_exports(db, estimate_id, user, audience=audience)


@router.get("/exports/{export_id}/download")
async def download_export(
    export_id: uuid.UUID,
    inline: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    return await service.download_export(db, export_id, user, inline=inline)


@router.delete("/exports/{export_id}", status_code=204)
async def delete_export(
    export_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    await service.delete_export(db, export_id, user)
    return Response(status_code=204)


@router.post(
    "/exports/{export_id}/send-to/google",
    response_model=DestinationSendResponse,
)
async def send_export_to_google(
    export_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
):
    return await destination_service.send_estimate_export_to_google(db, export_id, user)


@router.post(
    "/exports/{export_id}/send-to/canva",
    response_model=DestinationSendResponse,
)
async def send_export_to_canva(
    export_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
):
    return await destination_service.send_estimate_export_to_canva(db, export_id, user)


@router.post(
    "/estimates/{estimate_id}/exports/email",
    response_model=ExportEmailResponse,
)
async def email_exports(
    estimate_id: uuid.UUID,
    body: ExportEmailRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await service.send_exports_email(
        db,
        estimate_id,
        body.export_ids,
        body.to_email,
        body.message,
        user,
    )
