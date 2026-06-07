import uuid
from pathlib import Path

from fastapi import BackgroundTasks, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import SessionLocal
from app.documents.extractor import SUPPORTED_FILE_TYPES, ExtractionError, extract_document_text
from app.documents.hermes_client import HermesClient
from app.models.estimate import Estimate, EstimateDocument
from app.storage.factory import get_storage_backend


def get_file_extension(filename: str) -> str:
    return Path(filename).suffix.lstrip(".").lower()


def get_absolute_path(storage_path: str) -> str:
    return str((Path(settings.storage_path) / storage_path).resolve())


async def _get_estimate(db: AsyncSession, estimate_id: uuid.UUID) -> Estimate:
    result = await db.execute(select(Estimate).where(Estimate.id == estimate_id))
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(
            status_code=404,
            detail={"error": "Estimate not found", "code": "ESTIMATE_NOT_FOUND"},
        )
    return estimate


async def _get_document(
    db: AsyncSession,
    estimate_id: uuid.UUID,
    document_id: uuid.UUID,
) -> EstimateDocument:
    result = await db.execute(
        select(EstimateDocument).where(
            EstimateDocument.id == document_id,
            EstimateDocument.estimate_id == estimate_id,
        )
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(
            status_code=404,
            detail={"error": "Document not found", "code": "DOCUMENT_NOT_FOUND"},
        )
    return document


async def run_extraction(document_id: uuid.UUID) -> None:
    async with SessionLocal() as db:
        result = await db.execute(
            select(EstimateDocument).where(EstimateDocument.id == document_id)
        )
        document = result.scalar_one_or_none()
        if not document:
            return

        document.extraction_status = "processing"
        await db.commit()

        try:
            absolute_path = get_absolute_path(document.storage_path)
            extracted_text = await extract_document_text(
                absolute_path,
                document.file_type,
                hermes_client=HermesClient(),
            )
            document.extracted_text = extracted_text
            document.extraction_status = "done"
        except ExtractionError as exc:
            document.extracted_text = exc.message
            document.extraction_status = "failed"
        except Exception as exc:
            document.extracted_text = str(exc)
            document.extraction_status = "failed"

        await db.commit()


async def upload_document(
    db: AsyncSession,
    estimate_id: uuid.UUID,
    file: UploadFile,
    background_tasks: BackgroundTasks,
) -> EstimateDocument:
    await _get_estimate(db, estimate_id)

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail={"error": "Filename is required", "code": "INVALID_FILE"},
        )

    file_type = get_file_extension(file.filename)
    if file_type not in SUPPORTED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Unsupported file type: {file_type}",
                "code": "UNSUPPORTED_FILE_TYPE",
            },
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=400,
            detail={"error": "File is empty", "code": "INVALID_FILE"},
        )

    document_id = uuid.uuid4()
    storage_path = f"uploads/{estimate_id}/{document_id}.{file_type}"
    storage = get_storage_backend()
    await storage.save(storage_path, content)

    document = EstimateDocument(
        id=document_id,
        estimate_id=estimate_id,
        original_filename=file.filename,
        file_type=file_type,
        storage_path=storage_path,
        extraction_status="pending",
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    background_tasks.add_task(run_extraction, document.id)
    return document


async def delete_document(
    db: AsyncSession,
    estimate_id: uuid.UUID,
    document_id: uuid.UUID,
) -> None:
    document = await _get_document(db, estimate_id, document_id)
    storage = get_storage_backend()
    await storage.delete(document.storage_path)
    await db.delete(document)
    await db.commit()


async def retry_document_extraction(
    db: AsyncSession,
    estimate_id: uuid.UUID,
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
) -> EstimateDocument:
    document = await _get_document(db, estimate_id, document_id)
    document.extraction_status = "pending"
    document.extracted_text = None
    await db.commit()
    await db.refresh(document)

    background_tasks.add_task(run_extraction, document.id)
    return document
