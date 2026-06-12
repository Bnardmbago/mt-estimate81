import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.documents import service
from app.models.user import User
from app.schemas.estimate import EstimateDocumentResponse

router = APIRouter(prefix="/estimates", tags=["documents"])


@router.post(
    "/{estimate_id}/documents",
    response_model=EstimateDocumentResponse,
    status_code=201,
)
async def upload_document(
    estimate_id: uuid.UUID,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await service.upload_document(db, estimate_id, file, background_tasks, user)


@router.delete("/{estimate_id}/documents/{document_id}", status_code=204)
async def delete_document(
    estimate_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await service.delete_document(db, estimate_id, document_id, user)


@router.post(
    "/{estimate_id}/documents/{document_id}/retry",
    response_model=EstimateDocumentResponse,
)
async def retry_document_extraction(
    estimate_id: uuid.UUID,
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await service.retry_document_extraction(
        db,
        estimate_id,
        document_id,
        background_tasks,
        user,
    )
