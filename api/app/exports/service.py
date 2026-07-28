import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.admin.quotation_company_config import (
    get_quotation_company_config,
    resolve_logo_for_export,
)
from app.admin.quotation_notes_config import QuotationNotesConfig, get_quotation_notes_config
from app.admin.smtp_config import get_smtp_config, smtp_runtime_config
from app.estimates.access import require_estimate_access
from app.estimates.service import get_estimate_for_user
from app.audit.service import log_change
from app.email.smtp import EmailAttachment, send_email_with_attachments
from app.exceptions import AppError
from app.exports.cover_render import embed_cover_asset_data
from app.exports.excel import generate_excel
from app.exports.internal_dossier import (
    generate_internal_docx,
    generate_internal_markdown,
    generate_internal_pdf,
    generate_internal_xlsx,
    load_internal_export_parts,
)
from app.exports.internal_formats import is_internal_format, require_admin_for_internal_format
from app.exports.markdown import generate_markdown
from app.exports.narrative_translate import ensure_export_narrative_locale
from app.exports.quotation_context import build_formal_quotation_context
from app.exports.quotation_number import allocate_quotation_export_fields
from app.exports.report_context import build_report_context
from app.rate_cards.defaults import DEFAULT_RATE_CARD_SETTINGS
from app.models.estimate import Estimate, EstimateStatus, Export, ExportFormat
from app.models.rate_card import RateCard, RateCardVersion
from app.models.user import User
from app.presentation.resolver import PresentationBundle, resolve_presentation
from app.presentation.service import assert_preset_ids_exist
from app.proposals.service import merge_cover_values
from app.config import settings
from app.storage.factory import get_storage_backend
from app.users.access import is_contact_user

logger = logging.getLogger(__name__)

FORMAT_EXTENSIONS = {
    ExportFormat.MD.value: "md",
    ExportFormat.XLSX.value: "xlsx",
    ExportFormat.PDF.value: "pdf",
    ExportFormat.PDF_QUOTATION.value: "pdf",
    ExportFormat.DOCX.value: "docx",
    ExportFormat.DOCX_QUOTATION.value: "docx",
    "pdf_preliminary": "pdf",
    ExportFormat.PDF_INTERNAL.value: "pdf",
    ExportFormat.DOCX_INTERNAL.value: "docx",
    ExportFormat.XLSX_INTERNAL.value: "xlsx",
    ExportFormat.MD_INTERNAL.value: "md",
}

CONTENT_TYPES = {
    ExportFormat.MD.value: "text/markdown; charset=utf-8",
    ExportFormat.XLSX.value: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ExportFormat.PDF.value: "application/pdf",
    ExportFormat.PDF_QUOTATION.value: "application/pdf",
    ExportFormat.DOCX.value: (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ),
    ExportFormat.DOCX_QUOTATION.value: (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ),
    "pdf_preliminary": "application/pdf",
    ExportFormat.PDF_INTERNAL.value: "application/pdf",
    ExportFormat.DOCX_INTERNAL.value: (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ),
    ExportFormat.XLSX_INTERNAL.value: (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ),
    ExportFormat.MD_INTERNAL.value: "text/markdown; charset=utf-8",
}

QUOTATION_FORMATS = frozenset(
    {
        ExportFormat.PDF_QUOTATION.value,
        ExportFormat.DOCX_QUOTATION.value,
    }
)

REPORT_FORMATS = frozenset(
    {
        ExportFormat.MD.value,
        ExportFormat.XLSX.value,
        ExportFormat.PDF.value,
        ExportFormat.DOCX.value,
    }
)


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


async def _generate_content(
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
    show_watermark: bool = False,
    export_user_display_name: str | None = None,
    quotation_notes_config: QuotationNotesConfig | None = None,
    company_config: Any | None = None,
    logo_src: str | None = None,
    logo_bytes: bytes | None = None,
    logo_ext: str | None = None,
    quotation_number: str | None = None,
    registration_number: str | None = None,
    contact_person: str | None = None,
    internal_ctx: dict[str, Any] | None = None,
    presentation: PresentationBundle | None = None,
    include_cover: bool | None = None,
    cover_values: dict[str, Any] | None = None,
) -> bytes:
    if export_format == ExportFormat.MD_INTERNAL.value:
        return generate_internal_markdown(internal_ctx or {}).encode("utf-8")

    if export_format == ExportFormat.XLSX_INTERNAL.value:
        return generate_internal_xlsx(internal_ctx or {})

    if export_format == ExportFormat.PDF_INTERNAL.value:
        if internal_ctx:
            await embed_cover_asset_data(internal_ctx, get_storage_backend())
        return generate_internal_pdf(internal_ctx or {})

    if export_format == ExportFormat.DOCX_INTERNAL.value:
        if internal_ctx:
            await embed_cover_asset_data(internal_ctx, get_storage_backend())
        return generate_internal_docx(internal_ctx or {})

    report_context = build_report_context(
        estimate,
        locale,
        generated_at=generated_at,
        rate_card_name=rate_card_name,
        rate_card_version_number=rate_card_version_number,
        rate_card_effective_date=rate_card_effective_date,
        export_revision=export_revision,
        export_user_display_name=export_user_display_name,
        presentation=presentation,
        include_cover=include_cover,
        cover_values=cover_values,
    )
    if report_context["include_cover"]:
        missing_keys = [
            field["key"]
            for field in report_context["cover"]["fields"]
            if field.get("required") and field.get("source") == "missing"
        ]
        if missing_keys:
            raise AppError(
                "Required cover values are missing",
                "COVER_VALUES_REQUIRED",
                status_code=400,
                details={"missing_keys": missing_keys},
            )

    storage = get_storage_backend()
    await embed_cover_asset_data(report_context, storage)

    if export_format == ExportFormat.MD.value:
        content = generate_markdown(report_context)
        return content.encode("utf-8")

    if export_format == ExportFormat.XLSX.value:
        return generate_excel(report_context, estimate)

    if export_format == ExportFormat.PDF.value:
        from app.exports.pdf import generate_report_pdf

        return generate_report_pdf(report_context, show_watermark=show_watermark)

    if export_format == ExportFormat.PDF_QUOTATION.value:
        from app.exports.pdf import generate_quotation_formal_pdf

        if not quotation_number:
            raise AppError(
                "Quotation export requires a quotation number",
                "QUOTATION_NUMBER_REQUIRED",
                status_code=500,
            )
        quotation_context = build_formal_quotation_context(
            estimate,
            locale,
            generated_at=generated_at,
            rate_card_name=rate_card_name,
            rate_card_version_number=rate_card_version_number,
            rate_card_effective_date=rate_card_effective_date,
            export_revision=export_revision,
            tax_rate=tax_rate,
            quotation_notes_config=quotation_notes_config,
            company_config=company_config,
            logo_src=logo_src,
            logo_bytes=logo_bytes,
            logo_ext=logo_ext,
            quotation_number=quotation_number,
            registration_number=registration_number or "",
            contact_person=contact_person,
            presentation=presentation,
            include_cover=include_cover,
            cover_values=cover_values,
        )
        await embed_cover_asset_data(quotation_context, storage)
        return generate_quotation_formal_pdf(quotation_context, show_watermark=show_watermark)

    if export_format == ExportFormat.DOCX.value:
        from app.exports.docx import generate_report_docx

        return generate_report_docx(report_context)

    if export_format == ExportFormat.DOCX_QUOTATION.value:
        from app.exports.docx import generate_quotation_formal_docx

        if not quotation_number:
            raise AppError(
                "Quotation export requires a quotation number",
                "QUOTATION_NUMBER_REQUIRED",
                status_code=500,
            )
        quotation_context = build_formal_quotation_context(
            estimate,
            locale,
            generated_at=generated_at,
            rate_card_name=rate_card_name,
            rate_card_version_number=rate_card_version_number,
            rate_card_effective_date=rate_card_effective_date,
            export_revision=export_revision,
            tax_rate=tax_rate,
            quotation_notes_config=quotation_notes_config,
            company_config=company_config,
            logo_src=logo_src,
            logo_bytes=logo_bytes,
            logo_ext=logo_ext,
            quotation_number=quotation_number,
            registration_number=registration_number or "",
            contact_person=contact_person,
            presentation=presentation,
            include_cover=include_cover,
            cover_values=cover_values,
        )
        await embed_cover_asset_data(quotation_context, storage)
        return generate_quotation_formal_docx(quotation_context)

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


async def _auto_email_single_export(
    db: AsyncSession,
    estimate: Estimate,
    export_record: Export,
    to_email: str,
    user: User,
) -> None:
    storage = get_storage_backend()
    if not await storage.exists(export_record.storage_path):
        return

    content = await storage.read(export_record.storage_path)
    content_type = CONTENT_TYPES.get(export_record.format, "application/octet-stream")
    attachment = EmailAttachment(
        filename=_export_filename(export_record),
        content=content,
        content_type=content_type,
    )
    subject = f"Estimate export: {estimate.project_name}"
    body_text = (
        f"Your estimate export for project: {estimate.project_name}\n\n"
        f"Attached file: {attachment.filename}"
    )
    smtp_config = await get_smtp_config(db)
    await send_email_with_attachments(
        to_email=to_email,
        subject=subject,
        body_text=body_text,
        attachments=[attachment],
        config=smtp_runtime_config(smtp_config),
    )
    await log_change(
        db,
        estimate_id=estimate.id,
        user_id=user.id,
        action="export_emailed",
        changes={
            "to_email": to_email,
            "export_ids": [str(export_record.id)],
            "auto": True,
        },
    )


async def export_estimate(
    db: AsyncSession,
    estimate_id: uuid.UUID,
    export_format: str,
    locale: str | None,
    user: User,
    *,
    theme_id: str | None = None,
    style_id: str | None = None,
    template_id: str | None = None,
    include_cover: bool | None = None,
    cover_template_id: str | None = None,
    cover_values: dict[str, Any] | None = None,
) -> Export:
    require_admin_for_internal_format(export_format, user)

    estimate = await _get_estimate_for_export(db, estimate_id, user)

    if is_contact_user(user) and len(estimate.exports) >= settings.contact_export_limit:
        raise AppError(
            f"Contact accounts are limited to {settings.contact_export_limit} exports per estimate",
            "CONTACT_EXPORT_LIMIT",
            status_code=403,
            details={"limit": settings.contact_export_limit},
        )

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

    if estimate.calculation_result is None:
        raise AppError(
            "Calculation result is required before export",
            "CALCULATION_REQUIRED",
            status_code=422 if is_internal_format(export_format) else 400,
        )

    resolved_locale = locale or estimate.locale
    if resolved_locale not in ("ja", "en"):
        raise AppError("Locale must be ja or en", "INVALID_LOCALE", details={"locale": resolved_locale})

    await assert_preset_ids_exist(
        db,
        theme_id=theme_id,
        style_id=style_id,
        template_id=template_id,
        cover_template_id=cover_template_id,
    )
    presentation = await resolve_presentation(
        db,
        theme_id or estimate.theme_id,
        style_id or estimate.style_id,
        template_id or estimate.template_id,
        cover_template_id=cover_template_id,
    )
    effective_cover_values = (
        merge_cover_values(estimate.cover_values, resolved_locale, cover_values)
        if cover_values is not None
        else estimate.cover_values
    )
    estimate.theme_id = presentation.theme_id
    estimate.style_id = presentation.style_id
    estimate.template_id = presentation.template_id
    estimate.cover_values = effective_cover_values or {}

    rate_card_name, rate_card_version_number, rate_card_effective_date, tax_rate = (
        await _get_rate_card_version(db, estimate.rate_card_version_id)
    )
    generated_at = datetime.utcnow()
    export_revision = len(estimate.exports) + 1
    export_id = uuid.uuid4()
    extension = FORMAT_EXTENSIONS[export_format]
    storage_path = f"exports/{estimate_id}/{export_id}.{extension}"
    show_watermark = is_contact_user(user) and export_format in (
        ExportFormat.PDF.value,
        ExportFormat.PDF_QUOTATION.value,
    )
    export_user_display_name = user.display_name.strip() or user.email

    quotation_notes_config = None
    company_config = None
    logo_src = None
    logo_bytes = None
    logo_ext = None
    if export_format in QUOTATION_FORMATS:
        quotation_notes_config = await get_quotation_notes_config(db)
        company_config = await get_quotation_company_config(db)
        logo_info = await resolve_logo_for_export(db)
        logo_src = logo_info.get("logo_src")
        logo_bytes = logo_info.get("logo_bytes")
        logo_ext = logo_info.get("logo_ext")

    quotation_number: str | None = None
    registration_number: str | None = None
    contact_person: str | None = None
    if export_format in QUOTATION_FORMATS:
        quotation_number, registration_number, contact_person = (
            await allocate_quotation_export_fields(
                db,
                generated_at=generated_at,
            )
        )

    internal_ctx: dict[str, Any] | None = None
    if is_internal_format(export_format):
        internal_ctx = await load_internal_export_parts(
            db,
            estimate,
            resolved_locale,
            presentation=presentation,
            include_cover=include_cover,
            cover_values=effective_cover_values,
        )

    if export_format in REPORT_FORMATS:
        try:
            translated = await ensure_export_narrative_locale(
                db, estimate, resolved_locale
            )
            if translated:
                await log_change(
                    db,
                    estimate_id=estimate.id,
                    user_id=user.id,
                    action="export_narrative_translated",
                    changes={
                        "locale": resolved_locale,
                        "source_locale": estimate.locale,
                    },
                )
        except Exception:
            logger.exception(
                "Narrative translation hook failed for estimate %s",
                estimate_id,
            )

    try:
        content = await _generate_content(
            estimate,
            export_format,
            resolved_locale,
            rate_card_name=rate_card_name,
            rate_card_version_number=rate_card_version_number,
            rate_card_effective_date=rate_card_effective_date,
            export_revision=export_revision,
            generated_at=generated_at,
            tax_rate=tax_rate,
            show_watermark=show_watermark,
            export_user_display_name=export_user_display_name,
            quotation_notes_config=quotation_notes_config,
            company_config=company_config,
            logo_src=logo_src,
            logo_bytes=logo_bytes,
            logo_ext=logo_ext,
            quotation_number=quotation_number,
            registration_number=registration_number,
            contact_person=contact_person,
            internal_ctx=internal_ctx,
            presentation=presentation,
            include_cover=include_cover,
            cover_values=effective_cover_values,
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
        quotation_number=quotation_number,
        registration_number=registration_number,
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

    if is_contact_user(user):
        try:
            await _auto_email_single_export(db, estimate, export_record, user.email, user)
        except Exception:
            logger.exception(
                "Auto-email failed for contact export on estimate %s",
                estimate_id,
            )

    await db.commit()
    await db.refresh(export_record)
    return export_record


async def list_exports(
    db: AsyncSession,
    estimate_id: uuid.UUID,
    user: User,
    *,
    audience: str | None = None,
) -> list[Export]:
    if audience == "internal" and not user.is_admin:
        raise AppError(
            "Internal exports are restricted to administrators",
            "INTERNAL_EXPORT_ADMIN_REQUIRED",
            status_code=403,
        )

    await _get_estimate_for_export(db, estimate_id, user)
    result = await db.execute(
        select(Export)
        .where(Export.estimate_id == estimate_id)
        .order_by(Export.generated_at.desc())
    )
    exports = list(result.scalars().all())

    if audience == "internal":
        return [record for record in exports if is_internal_format(record.format)]
    return [record for record in exports if not is_internal_format(record.format)]


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
    require_admin_for_internal_format(export_record.format, user)

    storage = get_storage_backend()
    if not await storage.exists(export_record.storage_path):
        raise AppError("Export file not found", "EXPORT_FILE_NOT_FOUND", status_code=404)

    content = await storage.read(export_record.storage_path)
    extension = FORMAT_EXTENSIONS.get(export_record.format, export_record.format)
    suffix = ""
    if export_record.format == ExportFormat.PDF_QUOTATION.value:
        suffix = "-quotation"
    elif export_record.format == "pdf_preliminary":
        suffix = "-preliminary"
    elif is_internal_format(export_record.format):
        suffix = "-internal"
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
    require_admin_for_internal_format(export_record.format, user)

    if is_contact_user(user):
        raise AppError(
            "Contact accounts cannot delete exports",
            "CONTACT_ACCESS_DENIED",
            status_code=403,
        )

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
    if is_contact_user(user):
        raise AppError(
            "Contact accounts receive exports automatically by email",
            "CONTACT_ACCESS_DENIED",
            status_code=403,
        )

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

    for export_record in export_records:
        require_admin_for_internal_format(export_record.format, user)

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
