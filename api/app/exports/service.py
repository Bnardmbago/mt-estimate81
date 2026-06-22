import logging
import uuid
from datetime import datetime

from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.admin.smtp_config import get_smtp_config, smtp_runtime_config
from app.estimates.access import require_estimate_access
from app.estimates.service import get_estimate_for_user
from app.audit.service import log_change
from app.email.smtp import EmailAttachment, send_email_with_attachments
from app.exceptions import AppError
from app.exports.excel import generate_excel
from app.exports.markdown import generate_markdown
from app.exports.quotation_context import build_quotation_context
from app.exports.report_context import build_report_context
from app.rate_cards.defaults import DEFAULT_RATE_CARD_SETTINGS
from app.models.estimate import Estimate, EstimateStatus, Export, ExportFormat
from app.models.rate_card import RateCard, RateCardVersion
from app.models.user import User
from app.storage.factory import get_storage_backend

logger = logging.getLogger(__name__)

FORMAT_EXTENSIONS = {
    ExportFormat.MD.value: "md",
    ExportFormat.XLSX.value: "xlsx",
    ExportFormat.PDF.value: "pdf",
    ExportFormat.PDF_QUOTATION.value: "pdf",
    ExportFormat.PDF_PRELIMINARY.value: "pdf",
}

CONTENT_TYPES = {
    ExportFormat.MD.value: "text/markdown; charset=utf-8",
    ExportFormat.XLSX.value: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ExportFormat.PDF.value: "application/pdf",
    ExportFormat.PDF_QUOTATION.value: "application/pdf",
    ExportFormat.PDF_PRELIMINARY.value: "application/pdf",
}


async def _get_rate_card_version(
    db: AsyncSession,
    rate_card_version_id: uuid.UUID | None,
) -> tuple[str | None, int | None, datetime | None, float]:
    default_tax = float(DEFAULT_RATE_CARD_SETTINGS.get("tax_rate", 0.10))
    if not rate_card_version_id:
        return None, None, None, default_tax

    result = await db.execute(
        select(RateCardVersion, RateCard)
        .join(RateCard, RateCard.id == RateCardVersion.rate_card_id)
        .where(RateCardVersion.id == rate_card_version_id)
    )
    row = result.one_or_none()
    if not row:
        return None, None, None, default_tax

    version, rate_card = row
    settings = version.settings or {}
    tax_rate = float(settings.get("tax_rate", default_tax))
    return rate_card.name, version.version_number, version.created_at, tax_rate


async def _get_estimate_for_export(
    db: AsyncSession,
    estimate_id: uuid.UUID,
    user: User,
) -> Estimate:
    estimate = await get_estimate_for_user(db, estimate_id, user)
    result = await db.execute(
        select(Estimate)
        .where(Estimate.id == estimate_id)
        .options(
            selectinload(Estimate.feature_items),
            selectinload(Estimate.exports),
        )
    )
    return result.scalar_one()


def _generate_content(
    estimate: Estimate,
    export_format: str,
    locale: str,
    *,
    rate_card_name: str | None,
    rate_card_version_number: int | None,
    rate_card_effective_date: datetime | None,
    export_revision: int,
    generated_at: datetime,
    tax_rate: float,
) -> bytes:
    report_context = build_report_context(
        estimate,
        locale,
        generated_at=generated_at,
        rate_card_name=rate_card_name,
        rate_card_version_number=rate_card_version_number,
        rate_card_effective_date=rate_card_effective_date,
        export_revision=export_revision,
    )

    if export_format == ExportFormat.MD.value:
        content = generate_markdown(report_context)
        return content.encode("utf-8")

    if export_format == ExportFormat.XLSX.value:
        return generate_excel(report_context, estimate)

    if export_format == ExportFormat.PDF.value:
        from app.exports.pdf import generate_report_pdf

        return generate_report_pdf(report_context)

    if export_format == ExportFormat.PDF_QUOTATION.value:
        from app.exports.pdf import generate_quotation_pdf

        quotation_context = build_quotation_context(
            estimate,
            locale,
            generated_at=generated_at,
            rate_card_name=rate_card_name,
            rate_card_version_number=rate_card_version_number,
            rate_card_effective_date=rate_card_effective_date,
            export_revision=export_revision,
            tax_rate=tax_rate,
        )
        return generate_quotation_pdf(quotation_context)

    if export_format == ExportFormat.PDF_PRELIMINARY.value:
        from app.exports.pdf import generate_preliminary_pdf
        from app.exports.preliminary_context import build_preliminary_context

        preliminary_context = build_preliminary_context(
            estimate,
            locale,
            generated_at=generated_at,
            rate_card_name=rate_card_name,
            rate_card_version_number=rate_card_version_number,
            rate_card_effective_date=rate_card_effective_date,
            export_revision=export_revision,
            tax_rate=tax_rate,
        )
        return generate_preliminary_pdf(preliminary_context)

    raise AppError(
        f"Export format '{export_format}' is not yet implemented",
        "EXPORT_FORMAT_NOT_IMPLEMENTED",
        status_code=501,
        details={"format": export_format},
    )


def _export_filename(export_record: Export) -> str:
    extension = FORMAT_EXTENSIONS.get(export_record.format, export_record.format)
    format_label = export_record.format.replace("_", "-")
    return f"estimate-{format_label}-{export_record.locale}.{extension}"


async def export_estimate(
    db: AsyncSession,
    estimate_id: uuid.UUID,
    export_format: str,
    locale: str | None,
    user: User,
) -> Export:
    estimate = await _get_estimate_for_export(db, estimate_id, user)

    if estimate.status not in (
        EstimateStatus.CALCULATED.value,
        EstimateStatus.EXPORTED.value,
        EstimateStatus.COMPLETED.value,
    ):
        raise AppError(
            "Export requires calculated status or later",
            "INVALID_STATUS",
            details={"required_statuses": ["calculated", "exported", "completed"]},
        )

    if not estimate.calculation_result:
        raise AppError(
            "Calculation result is required before export",
            "CALCULATION_REQUIRED",
        )

    resolved_locale = locale or estimate.locale
    if resolved_locale not in ("ja", "en"):
        raise AppError("Locale must be ja or en", "INVALID_LOCALE", details={"locale": resolved_locale})

    rate_card_name, rate_card_version_number, rate_card_effective_date, tax_rate = (
        await _get_rate_card_version(db, estimate.rate_card_version_id)
    )
    generated_at = datetime.utcnow()
    export_revision = len(estimate.exports) + 1
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
            rate_card_effective_date=rate_card_effective_date,
            export_revision=export_revision,
            generated_at=generated_at,
            tax_rate=tax_rate,
        )
        storage = get_storage_backend()
        await storage.save(storage_path, content)
    except AppError:
        raise
    except Exception:
        logger.exception("Export generation failed for estimate %s", estimate_id)
        raise AppError("Export generation failed", "EXPORT_FAILED", status_code=500)

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


async def list_exports(
    db: AsyncSession,
    estimate_id: uuid.UUID,
    user: User,
) -> list[Export]:
    await _get_estimate_for_export(db, estimate_id, user)
    result = await db.execute(
        select(Export)
        .where(Export.estimate_id == estimate_id)
        .order_by(Export.generated_at.desc())
    )
    return list(result.scalars().all())


async def download_export(
    db: AsyncSession,
    export_id: uuid.UUID,
    user: User,
    *,
    inline: bool = False,
) -> Response:
    result = await db.execute(
        select(Export, Estimate)
        .join(Estimate, Export.estimate_id == Estimate.id)
        .where(Export.id == export_id)
    )
    row = result.one_or_none()
    if not row:
        raise AppError("Export not found", "EXPORT_NOT_FOUND", status_code=404)

    export_record, estimate = row
    require_estimate_access(estimate, user)

    storage = get_storage_backend()
    if not await storage.exists(export_record.storage_path):
        raise AppError("Export file not found", "EXPORT_FILE_NOT_FOUND", status_code=404)

    content = await storage.read(export_record.storage_path)
    extension = FORMAT_EXTENSIONS.get(export_record.format, export_record.format)
    suffix = ""
    if export_record.format == ExportFormat.PDF_QUOTATION.value:
        suffix = "-quotation"
    elif export_record.format == ExportFormat.PDF_PRELIMINARY.value:
        suffix = "-preliminary"
    filename = f"estimate-{export_record.estimate_id}{suffix}.{extension}"
    content_type = CONTENT_TYPES.get(export_record.format, "application/octet-stream")
    disposition = "inline" if inline else "attachment"

    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'{disposition}; filename="{filename}"'},
    )


async def delete_export(
    db: AsyncSession,
    export_id: uuid.UUID,
    user: User,
) -> None:
    result = await db.execute(
        select(Export, Estimate)
        .join(Estimate, Export.estimate_id == Estimate.id)
        .where(Export.id == export_id)
    )
    row = result.one_or_none()
    if not row:
        raise AppError("Export not found", "EXPORT_NOT_FOUND", status_code=404)

    export_record, estimate = row
    require_estimate_access(estimate, user)

    storage = get_storage_backend()
    if await storage.exists(export_record.storage_path):
        await storage.delete(export_record.storage_path)

    await db.delete(export_record)
    await db.commit()


async def send_exports_email(
    db: AsyncSession,
    estimate_id: uuid.UUID,
    export_ids: list[uuid.UUID],
    to_email: str,
    message: str | None,
    user: User,
) -> dict:
    estimate = await _get_estimate_for_export(db, estimate_id, user)

    unique_ids = list(dict.fromkeys(export_ids))
    result = await db.execute(
        select(Export).where(
            Export.estimate_id == estimate_id,
            Export.id.in_(unique_ids),
        )
    )
    export_records = list(result.scalars().all())

    if len(export_records) != len(unique_ids):
        raise AppError("One or more exports not found", "EXPORT_NOT_FOUND", status_code=404)

    export_by_id = {record.id: record for record in export_records}
    ordered_exports = [export_by_id[export_id] for export_id in unique_ids]

    storage = get_storage_backend()
    attachments: list[EmailAttachment] = []
    for export_record in ordered_exports:
        if not await storage.exists(export_record.storage_path):
            raise AppError("Export file not found", "EXPORT_FILE_NOT_FOUND", status_code=404)

        content = await storage.read(export_record.storage_path)
        content_type = CONTENT_TYPES.get(export_record.format, "application/octet-stream")
        attachments.append(
            EmailAttachment(
                filename=_export_filename(export_record),
                content=content,
                content_type=content_type,
            )
        )

    subject = f"Estimate export: {estimate.project_name}"
    body_lines = [
        f"Estimate exports for project: {estimate.project_name}",
        "",
    ]
    if message and message.strip():
        body_lines.extend([message.strip(), ""])
    body_lines.append("Attached files:")
    for attachment in attachments:
        body_lines.append(f"- {attachment.filename}")

    sent_at = datetime.utcnow()
    smtp_config = await get_smtp_config(db)
    await send_email_with_attachments(
        to_email=to_email,
        subject=subject,
        body_text="\n".join(body_lines),
        attachments=attachments,
        config=smtp_runtime_config(smtp_config),
    )

    await log_change(
        db,
        estimate_id=estimate.id,
        user_id=user.id,
        action="export_emailed",
        changes={
            "to_email": to_email,
            "export_ids": [str(export_id) for export_id in unique_ids],
        },
    )
    await db.commit()

    return {
        "to_email": to_email,
        "export_ids": unique_ids,
        "sent_at": sent_at,
    }
