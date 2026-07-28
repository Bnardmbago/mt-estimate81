"""Send stored exports to Google / Canva."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.destinations import canva as canva_client
from app.destinations import google as google_client
from app.destinations.content_pack import build_canva_content_pack
from app.destinations.mime import is_google_editable_format
from app.admin.oauth_app_config import get_oauth_app_config
from app.exceptions import AppError
from app.exports.internal_formats import require_admin_for_internal_format
from app.models.estimate import Estimate, Export
from app.models.proposal import Proposal, ProposalExport
from app.models.user import User
from app.storage.factory import get_storage_backend
from app.users.access import is_contact_user, require_full_user


def _deny_contact(user: User) -> None:
    if is_contact_user(user):
        raise AppError(
            "Contact accounts cannot use export destinations",
            "CONTACT_ACCESS_DENIED",
            status_code=403,
        )


async def _load_estimate_export(
    db: AsyncSession,
    export_id: uuid.UUID,
    user: User,
) -> tuple[Export, Estimate]:
    from app.estimates.access import require_estimate_access

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
    return export_record, estimate


async def _load_proposal_export(
    db: AsyncSession,
    proposal_id: uuid.UUID,
    export_id: uuid.UUID,
    user: User,
) -> tuple[ProposalExport, Proposal]:
    result = await db.execute(
        select(ProposalExport, Proposal)
        .join(Proposal, ProposalExport.proposal_id == Proposal.id)
        .where(
            ProposalExport.id == export_id,
            ProposalExport.proposal_id == proposal_id,
        )
    )
    row = result.one_or_none()
    if not row:
        raise AppError("Export not found", "EXPORT_NOT_FOUND", status_code=404)
    export_record, proposal = row
    # Proposal routes already require_full_account; still check ownership via estimate
    from app.estimates.access import require_estimate_access
    from app.models.estimate import Estimate

    est = await db.get(Estimate, proposal.estimate_id)
    if not est:
        raise AppError("Estimate not found", "ESTIMATE_NOT_FOUND", status_code=404)
    require_estimate_access(est, user)
    return export_record, proposal


async def send_estimate_export_to_google(
    db: AsyncSession,
    export_id: uuid.UUID,
    user: User,
) -> dict:
    _deny_contact(user)
    require_full_user(user)
    export_record, _estimate = await _load_estimate_export(db, export_id, user)

    if export_record.format == "md":
        raise AppError(
            "Markdown cannot be sent to Google",
            "DESTINATION_FORMAT_UNSUPPORTED",
            status_code=400,
        )
    if not is_google_editable_format(export_record.format):
        raise AppError(
            "Only DOCX and XLSX can be opened in Docs/Sheets",
            "DESTINATION_FORMAT_UNSUPPORTED",
            status_code=400,
        )

    storage = get_storage_backend()
    content = await storage.read(export_record.storage_path)
    access_token = await google_client.ensure_access_token(db, user)
    ext = "docx" if export_record.format.startswith("docx") else "xlsx"
    filename = f"estimate-{export_record.estimate_id}.{ext}"

    destination, file_id, url = await google_client.upload_and_convert(
        access_token=access_token,
        filename=filename,
        content=content,
        export_format=export_record.format,
    )
    export_record.destination = destination
    export_record.external_file_id = file_id
    export_record.external_url = url
    await db.commit()
    await db.refresh(export_record)
    return {
        "destination": destination,
        "external_file_id": file_id,
        "external_url": url,
        "export_id": export_record.id,
    }


async def send_proposal_export_to_google(
    db: AsyncSession,
    proposal_id: uuid.UUID,
    export_id: uuid.UUID,
    user: User,
) -> dict:
    require_full_user(user)
    export_record, _proposal = await _load_proposal_export(
        db, proposal_id, export_id, user
    )

    if export_record.format == "md":
        raise AppError(
            "Markdown cannot be sent to Google",
            "DESTINATION_FORMAT_UNSUPPORTED",
            status_code=400,
        )
    if not is_google_editable_format(export_record.format):
        raise AppError(
            "Only DOCX and XLSX can be opened in Docs/Sheets",
            "DESTINATION_FORMAT_UNSUPPORTED",
            status_code=400,
        )

    storage = get_storage_backend()
    content = await storage.read(export_record.storage_path)
    access_token = await google_client.ensure_access_token(db, user)
    filename = f"proposal-{proposal_id}-v{export_record.revision}.{export_record.format}"

    destination, file_id, url = await google_client.upload_and_convert(
        access_token=access_token,
        filename=filename,
        content=content,
        export_format=export_record.format,
    )
    export_record.destination = destination
    export_record.external_file_id = file_id
    export_record.external_url = url
    await db.commit()
    await db.refresh(export_record)
    return {
        "destination": destination,
        "external_file_id": file_id,
        "external_url": url,
        "export_id": export_record.id,
    }


async def send_proposal_export_to_canva(
    db: AsyncSession,
    proposal_id: uuid.UUID,
    export_id: uuid.UUID,
    user: User,
) -> dict:
    require_full_user(user)
    export_record, proposal = await _load_proposal_export(
        db, proposal_id, export_id, user
    )

    if not (
        export_record.format == "pdf" or str(export_record.format).startswith("pdf_")
    ):
        raise AppError(
            "Canva is only available for PDF exports",
            "CANVA_FORMAT_FORBIDDEN",
            status_code=400,
        )

    # Prefer rich context from proposal JSON for autofill
    from app.presentation.resolver import resolve_presentation
    from app.proposals.export_context import build_proposal_export_context

    bundle = await resolve_presentation(
        db,
        export_record.theme_id,
        export_record.style_id,
        export_record.template_id,
    )
    ctx = build_proposal_export_context(
        proposal,
        locale=export_record.locale,
        variant=export_record.variant,
        presentation=bundle,
    )
    canva_variant = "poc" if export_record.variant == "poc" else "proposal"
    pack = build_canva_content_pack(ctx, variant=canva_variant)
    oauth_config = await get_oauth_app_config(db)
    template_id = canva_client.template_id_for(
        variant=canva_variant,
        locale=export_record.locale,
        config=oauth_config,
    )
    access_token = await canva_client.ensure_access_token(db, user)
    title = pack["fields"].get("title") or f"Proposal {proposal_id}"
    design_id, edit_url = await canva_client.create_design_from_template(
        access_token=access_token,
        template_id=template_id,
        title=title,
        autofill_data=pack["fields"],
    )
    export_record.destination = "canva"
    export_record.external_file_id = design_id
    export_record.external_url = edit_url
    await db.commit()
    await db.refresh(export_record)
    return {
        "destination": "canva",
        "external_file_id": design_id,
        "external_url": edit_url,
        "export_id": export_record.id,
    }

async def send_estimate_export_to_canva(
    db: AsyncSession,
    export_id: uuid.UUID,
    user: User,
) -> dict:
    _deny_contact(user)
    require_full_user(user)
    export_record, estimate = await _load_estimate_export(db, export_id, user)

    if not (
        export_record.format == "pdf" or str(export_record.format).startswith("pdf_")
    ):
        raise AppError(
            "Canva is only available for PDF exports",
            "CANVA_FORMAT_FORBIDDEN",
            status_code=400,
        )

    oauth_config = await get_oauth_app_config(db)
    template_id = canva_client.template_id_for(
        variant="proposal",
        locale=export_record.locale,
        config=oauth_config,
    )
    access_token = await canva_client.ensure_access_token(db, user)
    project = ""
    if isinstance(getattr(estimate, "form_data", None), dict):
        project = str(estimate.form_data.get("project_name") or "").strip()
    title = project or f"Estimate {export_record.estimate_id}"
    design_id, edit_url = await canva_client.create_design_from_template(
        access_token=access_token,
        template_id=template_id,
        title=title,
        autofill_data={"title": title},
    )
    export_record.destination = "canva"
    export_record.external_file_id = design_id
    export_record.external_url = edit_url
    await db.commit()
    await db.refresh(export_record)
    return {
        "destination": "canva",
        "external_file_id": design_id,
        "external_url": edit_url,
        "export_id": export_record.id,
    }

