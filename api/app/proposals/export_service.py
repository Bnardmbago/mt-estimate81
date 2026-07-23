"""Persist and download proposal exports."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import AppError
from app.models.proposal import Proposal, ProposalExport, ProposalExportFormat
from app.models.user import User
from app.proposals.export_context import build_proposal_export_context
from app.proposals.export_formats import (
    generate_proposal_docx,
    generate_proposal_markdown,
    generate_proposal_pdf,
    generate_proposal_xlsx,
)
from app.proposals.service import get_proposal_or_404
from app.storage.factory import get_storage_backend

FORMAT_EXTENSIONS = {
    ProposalExportFormat.PDF.value: "pdf",
    ProposalExportFormat.DOCX.value: "docx",
    ProposalExportFormat.MD.value: "md",
    ProposalExportFormat.XLSX.value: "xlsx",
}

CONTENT_TYPES = {
    ProposalExportFormat.PDF.value: "application/pdf",
    ProposalExportFormat.DOCX.value: (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ),
    ProposalExportFormat.MD.value: "text/markdown; charset=utf-8",
    ProposalExportFormat.XLSX.value: (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ),
}


def _enrich_diagrams_for_visual_export(ctx: dict) -> dict:
    """Render Mermaid sources to SVG for PDF/DOCX (graceful no-op if renderer unavailable)."""
    from app.proposals.mermaid_render import enrich_diagrams_with_svg

    enriched = dict(ctx)
    enriched["diagrams"] = enrich_diagrams_with_svg(ctx.get("diagrams"))
    poc = ctx.get("poc")
    if poc:
        poc_copy = dict(poc)
        poc_copy["diagrams"] = enrich_diagrams_with_svg(poc.get("diagrams"))
        enriched["poc"] = poc_copy
    return enriched


def _generate_bytes(fmt: str, ctx: dict) -> bytes:
    if fmt in (ProposalExportFormat.PDF.value, ProposalExportFormat.DOCX.value):
        ctx = _enrich_diagrams_for_visual_export(ctx)
    if fmt == ProposalExportFormat.PDF.value:
        return generate_proposal_pdf(ctx)
    if fmt == ProposalExportFormat.DOCX.value:
        return generate_proposal_docx(ctx)
    if fmt == ProposalExportFormat.MD.value:
        return generate_proposal_markdown(ctx)
    if fmt == ProposalExportFormat.XLSX.value:
        return generate_proposal_xlsx(ctx)
    raise AppError(f"Unsupported proposal export format: {fmt}", code="UNSUPPORTED_FORMAT")


async def export_proposal(
    db: AsyncSession,
    user: User,
    proposal_id: uuid.UUID,
    *,
    format: str,
    variant: str = "full",
    locale: str | None = None,
    project_name: str | None = None,
) -> ProposalExport:
    proposal = await get_proposal_or_404(db, proposal_id, user)
    if not proposal.assessment or not proposal.proposal_body:
        raise AppError("Proposal content is incomplete", code="PROPOSAL_INCOMPLETE", status_code=400)
    if variant == "poc" and (not proposal.include_poc or not proposal.poc):
        raise AppError("Proof of Concept is not available", code="POC_NOT_AVAILABLE", status_code=400)

    loc = locale or proposal.locale
    ctx = build_proposal_export_context(
        proposal,
        locale=loc,
        variant=variant,
        project_name=project_name,
    )
    content = _generate_bytes(format, ctx)

    result = await db.execute(
        select(func.count()).select_from(ProposalExport).where(ProposalExport.proposal_id == proposal.id)
    )
    revision = int(result.scalar_one() or 0) + 1

    ext = FORMAT_EXTENSIONS[format]
    storage = get_storage_backend()
    path = f"proposals/{proposal.id}/{revision}_{variant}.{ext}"
    await storage.save(path, content)

    row = ProposalExport(
        proposal_id=proposal.id,
        format=format,
        variant=variant,
        storage_path=path,
        locale=loc,
        revision=revision,
        generated_by=user.id,
        generated_at=datetime.utcnow(),
    )
    db.add(row)
    proposal.updated_at = datetime.utcnow()
    if proposal.status == "draft":
        proposal.status = "ready"
    await db.commit()
    await db.refresh(row)
    return row


async def list_exports(
    db: AsyncSession,
    user: User,
    proposal_id: uuid.UUID,
) -> list[ProposalExport]:
    proposal = await get_proposal_or_404(db, proposal_id, user)
    return sorted(proposal.exports or [], key=lambda e: e.generated_at, reverse=True)


async def download_export(
    db: AsyncSession,
    user: User,
    proposal_id: uuid.UUID,
    export_id: uuid.UUID,
    *,
    inline: bool = False,
) -> Response:
    await get_proposal_or_404(db, proposal_id, user)
    result = await db.execute(
        select(ProposalExport).where(
            ProposalExport.id == export_id,
            ProposalExport.proposal_id == proposal_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise AppError("Export not found", code="NOT_FOUND", status_code=404)

    storage = get_storage_backend()
    content = await storage.read(row.storage_path)
    ext = FORMAT_EXTENSIONS.get(row.format, row.format)
    filename = f"proposal_{row.revision}_{row.variant}.{ext}"
    disposition = "inline" if inline else "attachment"
    return Response(
        content=content,
        media_type=CONTENT_TYPES.get(row.format, "application/octet-stream"),
        headers={"Content-Disposition": f'{disposition}; filename="{filename}"'},
    )


async def delete_export(
    db: AsyncSession,
    user: User,
    proposal_id: uuid.UUID,
    export_id: uuid.UUID,
) -> None:
    await get_proposal_or_404(db, proposal_id, user)
    result = await db.execute(
        select(ProposalExport).where(
            ProposalExport.id == export_id,
            ProposalExport.proposal_id == proposal_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise AppError("Export not found", code="NOT_FOUND", status_code=404)
    storage = get_storage_backend()
    try:
        await storage.delete(row.storage_path)
    except Exception:
        pass
    await db.delete(row)
    await db.commit()


async def send_exports_email(
    db: AsyncSession,
    user: User,
    proposal_id: uuid.UUID,
    *,
    export_ids: list[uuid.UUID],
    to_email: str,
    message: str | None,
) -> dict:
    from datetime import datetime

    from app.admin.smtp_config import get_smtp_config, smtp_runtime_config
    from app.email.smtp import EmailAttachment, send_email_with_attachments

    proposal = await get_proposal_or_404(db, proposal_id, user)
    snapshot = proposal.source_snapshot or {}
    project_name = snapshot.get("project_name") or "Proposal"

    unique_ids = list(dict.fromkeys(export_ids))
    result = await db.execute(
        select(ProposalExport).where(
            ProposalExport.proposal_id == proposal_id,
            ProposalExport.id.in_(unique_ids),
        )
    )
    export_records = list(result.scalars().all())
    if len(export_records) != len(unique_ids):
        raise AppError("One or more exports not found", code="EXPORT_NOT_FOUND", status_code=404)

    export_by_id = {record.id: record for record in export_records}
    ordered_exports = [export_by_id[export_id] for export_id in unique_ids]

    storage = get_storage_backend()
    attachments: list[EmailAttachment] = []
    for export_record in ordered_exports:
        content = await storage.read(export_record.storage_path)
        ext = FORMAT_EXTENSIONS.get(export_record.format, export_record.format)
        filename = f"proposal_{export_record.revision}_{export_record.variant}.{ext}"
        attachments.append(
            EmailAttachment(
                filename=filename,
                content=content,
                content_type=CONTENT_TYPES.get(export_record.format, "application/octet-stream"),
            )
        )

    subject = f"Proposal export: {project_name}"
    body_lines = [
        f"Proposal exports for project: {project_name}",
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

    return {
        "to_email": to_email,
        "export_ids": unique_ids,
        "sent_at": sent_at,
    }
