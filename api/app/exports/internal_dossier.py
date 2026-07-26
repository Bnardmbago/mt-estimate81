from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.estimates import service as estimate_service
from app.estimates.rate_card_stale import is_rate_card_stale_for_estimate
from app.exports.markdown import generate_markdown
from app.exports.report_context import build_report_context
from app.models.estimate import Estimate
from app.models.proposal import Proposal
from app.models.rate_card import RateCard, RateCardVersion
from app.models.user import User


INTERNAL_BANNER = "INTERNAL — DO NOT DISTRIBUTE"
MISSING_CALCULATION_WARNING = "Calculation result is unavailable."
MISSING_RATE_CARD_WARNING = "Rate card version is unavailable."


def build_internal_export_context(
    report: dict[str, Any],
    rate_card: dict[str, Any] | None,
    proposals: list[dict[str, Any]],
    *,
    locale: str,
) -> dict[str, Any]:
    return {
        "locale": locale,
        "internal_banner": INTERNAL_BANNER,
        "report": report,
        "rate_card": rate_card,
        "proposals": proposals,
        "proposals_status": "none" if not proposals else "present",
    }


async def _load_rate_card(
    db: AsyncSession,
    rate_card_version_id: Any,
) -> tuple[dict[str, Any] | None, datetime | None]:
    if not rate_card_version_id:
        return None, None

    result = await db.execute(
        select(RateCardVersion, RateCard)
        .join(RateCard, RateCard.id == RateCardVersion.rate_card_id)
        .where(RateCardVersion.id == rate_card_version_id)
    )
    row = result.one_or_none()
    if row is None:
        return None, None

    version, rate_card = row
    effective_date = version.created_at
    return (
        {
            "rate_card_id": str(version.rate_card_id) if version.rate_card_id else None,
            "name": rate_card.name,
            "version_number": version.version_number,
            "effective_date": effective_date.isoformat() if effective_date else None,
            "settings": version.settings or {},
        },
        effective_date,
    )


async def _load_proposals(
    db: AsyncSession,
    estimate_id: Any,
) -> list[dict[str, Any]]:
    result = await db.execute(
        select(Proposal)
        .where(Proposal.estimate_id == estimate_id)
        .order_by(Proposal.created_at.asc())
    )
    proposals = result.scalars().all()
    return [
        {
            "id": str(proposal.id),
            "locale": proposal.locale,
            "status": proposal.status,
            "include_poc": proposal.include_poc,
            "assessment": proposal.assessment,
            "proposal_body": proposal.proposal_body,
            "poc": proposal.poc,
        }
        for proposal in proposals
    ]


async def build_internal_dossier_payload(
    db: AsyncSession,
    estimate: Estimate,
    *,
    locale: str,
) -> dict[str, Any]:
    warnings: list[str] = []
    rate_card, rate_card_effective_date = await _load_rate_card(
        db,
        estimate.rate_card_version_id,
    )
    if estimate.rate_card_version_id and rate_card is None:
        warnings.append(MISSING_RATE_CARD_WARNING)

    has_calculation = estimate.calculation_result is not None
    if has_calculation:
        report = build_report_context(
            estimate,
            locale,
            generated_at=datetime.now(UTC),
            rate_card_name=rate_card["name"] if rate_card else None,
            rate_card_version_number=rate_card["version_number"] if rate_card else None,
            rate_card_effective_date=rate_card_effective_date,
            export_revision=1,
        )
    else:
        report = {}
        warnings.append(MISSING_CALCULATION_WARNING)

    proposals = await _load_proposals(db, estimate.id)
    return {
        "estimate_id": str(estimate.id),
        "project_name": estimate.project_name,
        "client_name": estimate.client_name,
        "status": estimate.status,
        "locale": locale,
        "has_calculation": has_calculation,
        "rate_card_stale": await is_rate_card_stale_for_estimate(db, estimate),
        "warnings": warnings,
        "report": report,
        "rate_card": rate_card,
        "proposals": proposals,
    }


async def get_internal_dossier(
    db: AsyncSession,
    estimate_id: uuid.UUID,
    admin: User,
) -> dict[str, Any]:
    estimate = await estimate_service.get_estimate_for_user(db, estimate_id, admin)
    return await build_internal_dossier_payload(db, estimate, locale=estimate.locale)


async def load_internal_export_parts(
    db: AsyncSession,
    estimate: Estimate,
    locale: str,
) -> dict[str, Any]:
    """Return build_internal_export_context(...) ready for generators."""
    payload = await build_internal_dossier_payload(db, estimate, locale=locale)
    return build_internal_export_context(
        payload["report"],
        payload["rate_card"],
        payload["proposals"],
        locale=locale,
    )


def _fallback_report_markdown(report: dict[str, Any]) -> str:
    project_summary = report.get("project_summary") or {}
    lines = ["## Project Summary", ""]
    for label, key in (
        ("Project Name", "project_name"),
        ("Client", "client_name"),
        ("Estimate ID", "estimate_id"),
    ):
        value = project_summary.get(key)
        if value:
            lines.append(f"- {label}: {value}")
    if len(lines) == 2:
        lines.append(f"- {MISSING_CALCULATION_WARNING}")
    return "\n".join(lines)


def _rate_card_markdown(rate_card: dict[str, Any] | None) -> str:
    lines = ["## Rate Card Appendix", ""]
    if not rate_card:
        lines.append("- none")
        return "\n".join(lines)

    lines.append(f"- Rate Card Name: {rate_card.get('name', '')}")
    version_number = rate_card.get("version_number")
    if version_number is not None:
        lines.append(f"- Version: {version_number}")

    settings = rate_card.get("settings") or {}

    roles = settings.get("roles") or []
    if roles:
        lines.append("")
        lines.append("| Role | Hourly Rate |")
        lines.append("|---|---:|")
        for role in roles:
            lines.append(f"| {role.get('name', '')} | {role.get('hourly_rate', '')} |")

    setup_cost_items = settings.get("setup_cost_items") or settings.get("nrc_items") or []
    if setup_cost_items:
        lines.append("")
        lines.append("| NRC Item | Cost |")
        lines.append("|---|---:|")
        for item in setup_cost_items:
            name = item.get("name") or item.get("item", "")
            cost = item.get("amount", item.get("cost_jpy", item.get("cost", "")))
            lines.append(f"| {name} | {cost} |")

    monthly_rc_items = settings.get("monthly_rc_items") or settings.get("rc_items") or []
    if monthly_rc_items:
        lines.append("")
        lines.append("| RC Item | Monthly |")
        lines.append("|---|---:|")
        for item in monthly_rc_items:
            name = item.get("name") or item.get("item", "")
            monthly = item.get("amount", item.get("monthly_jpy", item.get("monthly", "")))
            lines.append(f"| {name} | {monthly} |")

    return "\n".join(lines)


def _proposals_markdown(proposals: list[dict[str, Any]]) -> str:
    lines = ["## Proposal Appendix", ""]
    if not proposals:
        lines.append("No proposal (none)")
        return "\n".join(lines)

    for proposal in proposals:
        lines.append(f"### Proposal ({proposal.get('locale', '')}) — {proposal.get('status', '')}")
        lines.append(f"- Assessment: {proposal.get('assessment')}")
        lines.append(f"- Proposal Body: {proposal.get('proposal_body')}")
        lines.append(f"- POC: {proposal.get('poc')}")
        lines.append("")

    return "\n".join(lines)


def generate_internal_markdown(ctx: dict[str, Any]) -> str:
    """Build the internal Markdown dossier: banner + report + rate card + proposals."""
    report = ctx.get("report") or {}

    sections = [f"# {INTERNAL_BANNER}", ""]

    if report.get("labels"):
        sections.append(generate_markdown(report))
    else:
        sections.append(_fallback_report_markdown(report))

    sections.append("")
    sections.append(_rate_card_markdown(ctx.get("rate_card")))
    sections.append("")
    sections.append(_proposals_markdown(ctx.get("proposals") or []))

    return "\n".join(sections)


def generate_internal_pdf(ctx: dict[str, Any]) -> bytes:
    """Render the internal PDF dossier (banner + report + rate card + proposals)."""
    from app.exports.pdf import generate_internal_dossier_pdf

    return generate_internal_dossier_pdf(ctx)


def _rate_card_role_rows(rate_card: dict[str, Any] | None) -> list[tuple[str, str]]:
    if not rate_card:
        return [("Rate Card", "none")]
    rows = [("Rate Card Name", str(rate_card.get("name", "")))]
    version_number = rate_card.get("version_number")
    if version_number is not None:
        rows.append(("Version", str(version_number)))
    return rows


def _rate_card_role_table(rate_card: dict[str, Any] | None) -> tuple[list[str], list[list[str]]] | None:
    roles = (rate_card or {}).get("settings", {}).get("roles") or []
    if not roles:
        return None
    return (
        ["Role", "Hourly Rate"],
        [[str(role.get("name", "")), str(role.get("hourly_rate", ""))] for role in roles],
    )


def _rate_card_item_table(
    settings: dict[str, Any],
    *,
    keys: tuple[str, ...],
    headers: list[str],
) -> tuple[list[str], list[list[str]]] | None:
    items: list[dict[str, Any]] = []
    for key in keys:
        items = settings.get(key) or []
        if items:
            break
    if not items:
        return None
    rows = []
    for item in items:
        name = item.get("name") or item.get("item", "")
        value = item.get("amount", item.get("cost_jpy", item.get("monthly_jpy", item.get("cost", item.get("monthly", "")))))
        rows.append([str(name), str(value)])
    return (headers, rows)


def _proposal_rows(proposal: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        ("Locale", str(proposal.get("locale", ""))),
        ("Status", str(proposal.get("status", ""))),
        ("Assessment", str(proposal.get("assessment"))),
        ("Proposal Body", str(proposal.get("proposal_body"))),
        ("POC", str(proposal.get("poc"))),
    ]


def _add_fallback_report_docx(document: Any, report: dict[str, Any]) -> None:
    project_summary = report.get("project_summary") or {}
    document.add_heading("Project Summary", level=2)
    from app.exports.docx import _add_key_value_table

    rows = [
        (label, str(project_summary[key]))
        for label, key in (
            ("Project Name", "project_name"),
            ("Client", "client_name"),
            ("Estimate ID", "estimate_id"),
        )
        if project_summary.get(key)
    ]
    if not rows:
        document.add_paragraph(MISSING_CALCULATION_WARNING)
        return
    _add_key_value_table(document, rows)


def generate_internal_docx(ctx: dict[str, Any]) -> bytes:
    """Render the internal DOCX dossier: banner + report + rate card + proposals."""
    from docx import Document

    from app.exports.docx import (
        _add_data_table,
        _add_key_value_table,
        _add_subheading,
        _document_bytes,
        build_report_document,
    )

    report = ctx.get("report") or {}

    if report.get("labels"):
        document = build_report_document(report)
    else:
        document = Document()
        _add_fallback_report_docx(document, report)

    banner_text = ctx.get("internal_banner") or INTERNAL_BANNER
    if document.paragraphs:
        banner_paragraph = document.paragraphs[0].insert_paragraph_before(banner_text)
        banner_paragraph.style = document.styles["Heading 1"]
    else:
        document.add_heading(banner_text, level=1)

    document.add_heading("Rate Card Appendix", level=2)
    rate_card = ctx.get("rate_card")
    _add_key_value_table(document, _rate_card_role_rows(rate_card))
    settings = (rate_card or {}).get("settings") or {}
    role_table = _rate_card_role_table(rate_card)
    if role_table:
        _add_data_table(document, role_table[0], role_table[1])
    setup_table = _rate_card_item_table(
        settings, keys=("setup_cost_items", "nrc_items"), headers=["NRC Item", "Cost"]
    )
    if setup_table:
        _add_data_table(document, setup_table[0], setup_table[1])
    monthly_table = _rate_card_item_table(
        settings, keys=("monthly_rc_items", "rc_items"), headers=["RC Item", "Monthly"]
    )
    if monthly_table:
        _add_data_table(document, monthly_table[0], monthly_table[1])

    document.add_heading("Proposal Appendix", level=2)
    proposals = ctx.get("proposals") or []
    if not proposals:
        document.add_paragraph("No proposal (none)")
    else:
        for proposal in proposals:
            _add_subheading(
                document,
                f"Proposal ({proposal.get('locale', '')}) — {proposal.get('status', '')}",
            )
            _add_key_value_table(document, _proposal_rows(proposal))

    return _document_bytes(document)


def _write_rate_card_sheet(ws: Any, rate_card: dict[str, Any] | None) -> None:
    row_idx = 1
    for label, value in _rate_card_role_rows(rate_card):
        ws.cell(row=row_idx, column=1, value=label)
        ws.cell(row=row_idx, column=2, value=value)
        row_idx += 1
    row_idx += 1

    settings = (rate_card or {}).get("settings") or {}
    role_table = _rate_card_role_table(rate_card)
    if role_table:
        headers, rows = role_table
        for col_idx, header in enumerate(headers, start=1):
            ws.cell(row=row_idx, column=col_idx, value=header)
        row_idx += 1
        for row in rows:
            for col_idx, value in enumerate(row, start=1):
                ws.cell(row=row_idx, column=col_idx, value=value)
            row_idx += 1
        row_idx += 1

    for keys, headers in (
        (("setup_cost_items", "nrc_items"), ["NRC Item", "Cost"]),
        (("monthly_rc_items", "rc_items"), ["RC Item", "Monthly"]),
    ):
        item_table = _rate_card_item_table(settings, keys=keys, headers=headers)
        if not item_table:
            continue
        table_headers, rows = item_table
        for col_idx, header in enumerate(table_headers, start=1):
            ws.cell(row=row_idx, column=col_idx, value=header)
        row_idx += 1
        for row in rows:
            for col_idx, value in enumerate(row, start=1):
                ws.cell(row=row_idx, column=col_idx, value=value)
            row_idx += 1
        row_idx += 1


def _write_proposals_sheet(ws: Any, proposals: list[dict[str, Any]]) -> None:
    row_idx = 1
    if not proposals:
        ws.cell(row=row_idx, column=1, value="No proposal (none)")
        return

    for proposal in proposals:
        ws.cell(
            row=row_idx,
            column=1,
            value=f"Proposal ({proposal.get('locale', '')}) — {proposal.get('status', '')}",
        )
        row_idx += 1
        for label, value in _proposal_rows(proposal):
            ws.cell(row=row_idx, column=1, value=label)
            ws.cell(row=row_idx, column=2, value=value)
            row_idx += 1
        row_idx += 1


def generate_internal_xlsx(ctx: dict[str, Any]) -> bytes:
    """Render the internal XLSX dossier: banner + report + rate card + proposals."""
    from io import BytesIO

    from openpyxl import Workbook

    from app.exports.excel import add_report_sheets

    report = ctx.get("report") or {}
    banner_text = ctx.get("internal_banner") or INTERNAL_BANNER

    wb = Workbook()
    wb.remove(wb.active)

    internal_ws = wb.create_sheet("Internal")
    internal_ws.cell(row=1, column=1, value=banner_text)

    if report.get("labels"):
        add_report_sheets(wb, report)
    else:
        report_ws = wb.create_sheet("Report")
        project_summary = report.get("project_summary") or {}
        row_idx = 1
        for label, key in (
            ("Project Name", "project_name"),
            ("Client", "client_name"),
            ("Estimate ID", "estimate_id"),
        ):
            value = project_summary.get(key)
            if value:
                report_ws.cell(row=row_idx, column=1, value=label)
                report_ws.cell(row=row_idx, column=2, value=str(value))
                row_idx += 1
        if row_idx == 1:
            report_ws.cell(row=1, column=1, value=MISSING_CALCULATION_WARNING)

    rate_card_ws = wb.create_sheet("Rate Card Appendix")
    _write_rate_card_sheet(rate_card_ws, ctx.get("rate_card"))

    proposals_ws = wb.create_sheet("Proposal Appendix")
    _write_proposals_sheet(proposals_ws, ctx.get("proposals") or [])

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
