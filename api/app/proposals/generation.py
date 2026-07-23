"""Background proposal generation orchestration."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import SessionLocal
from app.models.estimate import Estimate
from app.models.proposal import Proposal, ProposalStatus
from app.proposals.ai_generate import (
    generate_assessment_content,
    generate_poc_content,
    generate_proposal_content,
)

logger = logging.getLogger(__name__)

PartName = Literal["assessment", "proposal", "poc", "all"]


def proposal_generate_sync_enabled() -> bool:
    return os.environ.get("PROPOSAL_GENERATE_SYNC", "").strip() in {"1", "true", "True", "yes"}


def _default_meta(run_id: str, include_poc: bool) -> dict[str, Any]:
    parts = {
        "assessment": {"status": "pending", "error": None},
        "proposal": {"status": "pending", "error": None},
    }
    if include_poc:
        parts["poc"] = {"status": "pending", "error": None}
    return {
        "run_id": run_id,
        "parts": parts,
        "prompt_version": "proposal-v1",
    }


async def _load_proposal(db: AsyncSession, proposal_id: uuid.UUID) -> Proposal | None:
    result = await db.execute(
        select(Proposal)
        .where(Proposal.id == proposal_id)
        .options(selectinload(Proposal.exports))
    )
    return result.scalar_one_or_none()


async def _set_part_status(
    db: AsyncSession,
    proposal: Proposal,
    part: str,
    status: str,
    error: str | None = None,
) -> None:
    meta = dict(proposal.generation_meta or {})
    parts = dict(meta.get("parts") or {})
    part_meta = dict(parts.get(part) or {})
    part_meta["status"] = status
    part_meta["error"] = error
    part_meta["updated_at"] = datetime.utcnow().isoformat() + "Z"
    parts[part] = part_meta
    meta["parts"] = parts
    proposal.generation_meta = meta
    proposal.updated_at = datetime.utcnow()
    await db.commit()


async def _run_generation_with_db(
    db: AsyncSession,
    proposal_id: uuid.UUID,
    parts: PartName,
) -> None:
    proposal = await _load_proposal(db, proposal_id)
    if proposal is None:
        logger.error("Proposal %s not found for generation", proposal_id)
        return

    locale: Literal["ja", "en"] = "ja" if proposal.locale == "ja" else "en"
    snapshot = proposal.source_snapshot or {}
    include_poc = bool(proposal.include_poc)

    if parts == "all":
        run_parts = ["assessment", "proposal"] + (["poc"] if include_poc else [])
    elif parts == "poc":
        run_parts = ["poc"] if include_poc else []
    else:
        run_parts = [parts]

    proposal.status = ProposalStatus.GENERATING.value
    await db.commit()

    try:
        if "assessment" in run_parts:
            await _set_part_status(db, proposal, "assessment", "running")
            assessment = await generate_assessment_content(snapshot, locale)
            proposal = await _load_proposal(db, proposal_id)
            if proposal is None:
                return
            proposal.assessment = assessment
            await db.commit()
            await _set_part_status(db, proposal, "assessment", "done")

        if "proposal" in run_parts:
            await _set_part_status(db, proposal, "proposal", "running")
            proposal = await _load_proposal(db, proposal_id)
            if proposal is None:
                return
            assessment = proposal.assessment or {}
            body, diagrams, milestones = await generate_proposal_content(
                snapshot, assessment, locale
            )
            proposal.proposal_body = body
            proposal.diagrams = diagrams
            proposal.milestones = milestones
            await db.commit()
            await _set_part_status(db, proposal, "proposal", "done")

        if "poc" in run_parts and include_poc:
            await _set_part_status(db, proposal, "poc", "running")
            proposal = await _load_proposal(db, proposal_id)
            if proposal is None:
                return
            assessment = proposal.assessment or {}
            poc = await generate_poc_content(snapshot, assessment, locale)
            proposal.poc = poc
            await db.commit()
            await _set_part_status(db, proposal, "poc", "done")
        elif not include_poc:
            proposal = await _load_proposal(db, proposal_id)
            if proposal is not None:
                proposal.poc = None
                await db.commit()

        proposal = await _load_proposal(db, proposal_id)
        if proposal is None:
            return
        proposal.status = ProposalStatus.DRAFT.value
        proposal.updated_at = datetime.utcnow()
        await db.commit()
    except Exception as exc:
        logger.exception("Proposal generation failed for %s", proposal_id)
        proposal = await _load_proposal(db, proposal_id)
        if proposal is None:
            return
        meta = dict(proposal.generation_meta or {})
        meta["error"] = str(exc)
        proposal.generation_meta = meta
        proposal.status = ProposalStatus.DRAFT.value
        await db.commit()


async def run_generation_sequence(
    proposal_id: uuid.UUID,
    *,
    parts: PartName = "all",
    db: AsyncSession | None = None,
) -> None:
    if db is not None:
        await _run_generation_with_db(db, proposal_id, parts)
        return
    async with SessionLocal() as session:
        await _run_generation_with_db(session, proposal_id, parts)


def begin_generation_meta(include_poc: bool) -> tuple[str, dict[str, Any]]:
    run_id = str(uuid.uuid4())
    return run_id, _default_meta(run_id, include_poc)


async def ensure_estimate_loaded(db: AsyncSession, estimate_id: uuid.UUID) -> Estimate | None:
    result = await db.execute(
        select(Estimate)
        .where(Estimate.id == estimate_id)
        .options(selectinload(Estimate.feature_items))
    )
    return result.scalar_one_or_none()
