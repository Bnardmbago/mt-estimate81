import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.exports import service
from app.models.user import User
from app.schemas.export import ExportRequest, ExportResponse

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
    )


@router.get("/estimates/{estimate_id}/exports", response_model=list[ExportResponse])
async def list_estimate_exports(
    estimate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await service.list_exports(db, estimate_id)


@router.get("/exports/{export_id}/download")
async def download_export(
    export_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    return await service.download_export(db, export_id)
