import logging
import uuid
from datetime import datetime

from fastapi import HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.audit.service import log_change
from app.exports.excel import generate_excel
from app.exports.markdown import generate_markdown
from app.models.estimate import Estimate, EstimateStatus, Export, ExportFormat
from app.models.rate_card import RateCard, RateCardVersion
from app.models.user import User
from app.storage.factory import get_storage_backend

logger = logging.getLogger(__name__)

FORMAT_EXTENSIONS = {
    ExportFormat.MD.value: "md",
    ExportFormat.XLSX.value: "xlsx",
    ExportFormat.PDF.value: "pdf",
}

CONTENT_TYPES = {
    ExportFormat.MD.value: "text/markdown; charset=utf-8",
    ExportFormat.XLSX.value: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ExportFormat.PDF.value: "application/pdf",
}


async def _get_rate_card_version(
    db: AsyncSession,
    rate_card_version_id: uuid.UUID | None,
) -> tuple[str | None, int | None]:
    if not rate_card_version_id:
        return None, None

    result = await db.execute(
        select(RateCardVersion, RateCard)
        .join(RateCard, RateCard.id == RateCardVersion.rate_card_id)
        .where(RateCardVersion.id == rate_card_version_id)
    )
    row = result.one_or_none()
    if not row:
        return None, None

    version, rate_card = row
    return rate_card.name, version.version_number


async def _get_estimate_for_export(db: AsyncSession, estimate_id: uuid.UUID) -> Estimate:
    result = await db.execute(
        select(Estimate)
        .where(Estimate.id == estimate_id)
        .options(
            selectinload(Estimate.feature_items),
            selectinload(Estimate.exports),
        )
    )
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(
            status_code=404,
            detail={"error": "Estimate not found", "code": "ESTIMATE_NOT_FOUND"},
        )
    return estimate


def _generate_content(
    estimate: Estimate,
    export_format: str,
    locale: str,
    *,
    rate_card_name: str | None,
    rate_card_version_number: int | None,
    generated_at: datetime,
) -> bytes:
    if export_format == ExportFormat.MD.value:
        content = generate_markdown(
            estimate,
            locale,
            rate_card_name=rate_card_name,
            rate_card_version_number=rate_card_version_number,
            generated_at=generated_at,
        )
        return content.encode("utf-8")

    if export_format == ExportFormat.XLSX.value:
        return generate_excel(
            estimate,
            locale,
            rate_card_name=rate_card_name,
            rate_card_version_number=rate_card_version_number,
            generated_at=generated_at,
        )

    raise HTTPException(
        status_code=501,
        detail={
            "error": f"Export format '{export_format}' is not yet implemented",
            "code": "EXPORT_FORMAT_NOT_IMPLEMENTED",
        },
    )


async def export_estimate(
    db: AsyncSession,
    estimate_id: uuid.UUID,
    export_format: str,
    locale: str | None,
    user: User,
) -> Export:
    estimate = await _get_estimate_for_export(db, estimate_id)

    if estimate.status not in (
        EstimateStatus.CALCULATED.value,
        EstimateStatus.EXPORTED.value,
        EstimateStatus.COMPLETED.value,
    ):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Export requires calculated status or later",
                "code": "INVALID_STATUS",
            },
        )

    if not estimate.calculation_result:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Calculation result is required before export",
                "code": "CALCULATION_REQUIRED",
            },
        )

    resolved_locale = locale or estimate.locale
    if resolved_locale not in ("ja", "en"):
        raise HTTPException(
            status_code=400,
            detail={"error": "Locale must be ja or en", "code": "INVALID_LOCALE"},
        )

    rate_card_name, rate_card_version_number = await _get_rate_card_version(
        db,
        estimate.rate_card_version_id,
    )
    generated_at = datetime.utcnow()
    export_id = uuid.uuid4()
    extension = FORMAT_EXTENSIONS[export_format]
    storage_path = f"exports/{estimate_id}/{export_id}.{extension}"

    try:
        content = _generate_content(
            estimate,
            export_format,
            resolved_locale,
            rate_card_name=rate_card_name,
            rate_card_version_number=rate_card_version_number,
            generated_at=generated_at,
        )
        storage = get_storage_backend()
        await storage.save(storage_path, content)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Export generation failed for estimate %s", estimate_id)
        raise HTTPException(
            status_code=500,
            detail={"error": "Export generation failed", "code": "EXPORT_FAILED"},
        )

    export_record = Export(
        id=export_id,
        estimate_id=estimate_id,
        format=export_format,
        storage_path=storage_path,
        locale=resolved_locale,
        generated_at=generated_at,
        generated_by=user.id,
    )
    db.add(export_record)

    if estimate.status == EstimateStatus.CALCULATED.value:
        estimate.status = EstimateStatus.EXPORTED.value

    await log_change(
        db,
        estimate_id=estimate.id,
        user_id=user.id,
        action="exported",
        changes={
            "format": export_format,
            "locale": resolved_locale,
            "export_id": str(export_id),
        },
    )
    await db.commit()
    await db.refresh(export_record)
    return export_record


async def list_exports(db: AsyncSession, estimate_id: uuid.UUID) -> list[Export]:
    await _get_estimate_for_export(db, estimate_id)
    result = await db.execute(
        select(Export)
        .where(Export.estimate_id == estimate_id)
        .order_by(Export.generated_at.desc())
    )
    return list(result.scalars().all())


async def download_export(db: AsyncSession, export_id: uuid.UUID) -> Response:
    result = await db.execute(select(Export).where(Export.id == export_id))
    export_record = result.scalar_one_or_none()
    if not export_record:
        raise HTTPException(
            status_code=404,
            detail={"error": "Export not found", "code": "EXPORT_NOT_FOUND"},
        )

    storage = get_storage_backend()
    if not await storage.exists(export_record.storage_path):
        raise HTTPException(
            status_code=404,
            detail={"error": "Export file not found", "code": "EXPORT_FILE_NOT_FOUND"},
        )

    content = await storage.read(export_record.storage_path)
    extension = FORMAT_EXTENSIONS.get(export_record.format, export_record.format)
    filename = f"estimate-{export_record.estimate_id}.{extension}"
    content_type = CONTENT_TYPES.get(export_record.format, "application/octet-stream")

    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
