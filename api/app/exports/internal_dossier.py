from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.estimates import service as estimate_service
from app.estimates.rate_card_stale import is_rate_card_stale_for_estimate
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

    has_calculation = bool(estimate.calculation_result)
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
