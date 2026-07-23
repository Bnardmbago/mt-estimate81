"""Proposal CRUD, refresh, finalize, and serialization helpers."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.estimates.access import require_estimate_access
from app.estimates.service import get_gantt_timeline
from app.models.estimate import Estimate
from app.models.proposal import Proposal, ProposalExport, ProposalStatus
from app.models.user import User
from app.proposals.generation import (
    begin_generation_meta,
    ensure_estimate_loaded,
    proposal_generate_sync_enabled,
    run_generation_sequence,
)
from app.proposals.poc_pricing import price_poc_selection
from app.proposals.snapshot import (
    ELIGIBLE_STATUSES,
    build_source_snapshot,
    compute_source_fingerprint,
)
from app.schemas.proposal import (
    ProposalDetail,
    ProposalExportRecord,
    ProposalSectionPatch,
    ProposalStatusResponse,
    ProposalSummary,
)


async def _build_snapshot_with_live_gantt(
    db: AsyncSession,
    estimate: Estimate,
    user: User,
    locale: str,
) -> dict[str, Any]:
    """Snapshot commercials from the estimate and gantt from the same builder as the Estimate page."""
    snapshot = build_source_snapshot(estimate)
    try:
        live_gantt = await get_gantt_timeline(
            db,
            estimate.id,
            user,
            start_date=estimate.project_start_date,
            display_locale=locale,
        )
        if live_gantt:
            snapshot["gantt"] = live_gantt
    except Exception:
        # Keep calculation_result.gantt if live rebuild fails.
        pass
    return snapshot


async def _get_estimate(db: AsyncSession, estimate_id: uuid.UUID, user: User) -> Estimate:
    estimate = await ensure_estimate_loaded(db, estimate_id)
    if estimate is None:
        raise HTTPException(status_code=404, detail={"error": "Estimate not found", "code": "NOT_FOUND"})
    require_estimate_access(estimate, user)
    return estimate


def _require_eligible(estimate: Estimate) -> None:
    if estimate.status not in ELIGIBLE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Estimate must be calculated before generating a proposal",
                "code": "ESTIMATE_NOT_READY",
                "status": estimate.status,
            },
        )


async def get_proposal_or_404(db: AsyncSession, proposal_id: uuid.UUID, user: User) -> Proposal:
    result = await db.execute(
        select(Proposal)
        .where(Proposal.id == proposal_id)
        .options(selectinload(Proposal.exports))
    )
    proposal = result.scalar_one_or_none()
    if proposal is None:
        raise HTTPException(status_code=404, detail={"error": "Proposal not found", "code": "NOT_FOUND"})
    if not user.is_admin and proposal.user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail={"error": "You do not have access to this proposal", "code": "PROPOSAL_ACCESS_DENIED"},
        )
    # Also verify estimate access
    await _get_estimate(db, proposal.estimate_id, user)
    return proposal


def _is_stale(proposal: Proposal, estimate: Estimate | None) -> bool:
    if estimate is None:
        return False
    return compute_source_fingerprint(estimate) != (proposal.source_fingerprint or "")


async def to_detail(db: AsyncSession, proposal: Proposal, user: User) -> ProposalDetail:
    estimate = await ensure_estimate_loaded(db, proposal.estimate_id)
    exports = [
        ProposalExportRecord.model_validate(row)
        for row in sorted(proposal.exports or [], key=lambda e: e.generated_at, reverse=True)
    ]
    return ProposalDetail(
        id=proposal.id,
        estimate_id=proposal.estimate_id,
        locale=proposal.locale,
        include_poc=proposal.include_poc,
        status=proposal.status,
        source_snapshot=proposal.source_snapshot or {},
        assessment=proposal.assessment,
        proposal_body=proposal.proposal_body,
        poc=proposal.poc,
        diagrams=list(proposal.diagrams or []),
        milestones=list(proposal.milestones or []),
        generation_meta=proposal.generation_meta or {},
        source_fingerprint=proposal.source_fingerprint or "",
        source_stale=_is_stale(proposal, estimate),
        created_at=proposal.created_at,
        updated_at=proposal.updated_at,
        finalized_at=proposal.finalized_at,
        exports=exports,
    )


def to_status(proposal: Proposal) -> ProposalStatusResponse:
    meta = proposal.generation_meta or {}
    parts = meta.get("parts") or {}
    return ProposalStatusResponse(
        id=proposal.id,
        status=proposal.status,
        generation_meta=meta,
        assessment_ready=bool(proposal.assessment),
        proposal_ready=bool(proposal.proposal_body),
        poc_ready=bool(proposal.poc) if proposal.include_poc else True,
    )


async def list_proposals(db: AsyncSession, user: User) -> list[ProposalSummary]:
    stmt = select(Proposal).options(selectinload(Proposal.exports)).order_by(Proposal.updated_at.desc())
    if not user.is_admin:
        stmt = stmt.where(Proposal.user_id == user.id)
    result = await db.execute(stmt)
    proposals = list(result.scalars().all())
    summaries: list[ProposalSummary] = []
    for proposal in proposals:
        estimate = await ensure_estimate_loaded(db, proposal.estimate_id)
        summaries.append(
            ProposalSummary(
                id=proposal.id,
                estimate_id=proposal.estimate_id,
                project_name=estimate.project_name if estimate else "",
                client_name=estimate.client_name if estimate else "",
                locale=proposal.locale,
                include_poc=proposal.include_poc,
                status=proposal.status,
                updated_at=proposal.updated_at,
                source_stale=_is_stale(proposal, estimate),
            )
        )
    return summaries


async def get_by_estimate(
    db: AsyncSession,
    estimate_id: uuid.UUID,
    locale: str,
    user: User,
) -> ProposalDetail:
    await _get_estimate(db, estimate_id, user)
    result = await db.execute(
        select(Proposal)
        .where(Proposal.estimate_id == estimate_id, Proposal.locale == locale)
        .options(selectinload(Proposal.exports))
    )
    proposal = result.scalar_one_or_none()
    if proposal is None:
        raise HTTPException(status_code=404, detail={"error": "Proposal not found", "code": "NOT_FOUND"})
    if not user.is_admin and proposal.user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail={"error": "You do not have access to this proposal", "code": "PROPOSAL_ACCESS_DENIED"},
        )
    return await to_detail(db, proposal, user)


async def start_generate(
    db: AsyncSession,
    user: User,
    *,
    estimate_id: uuid.UUID,
    locale: Literal["ja", "en"],
    include_poc: bool,
    background_tasks: BackgroundTasks | None,
) -> ProposalDetail:
    estimate = await _get_estimate(db, estimate_id, user)
    _require_eligible(estimate)

    result = await db.execute(
        select(Proposal)
        .where(Proposal.estimate_id == estimate_id, Proposal.locale == locale)
        .options(selectinload(Proposal.exports))
    )
    proposal = result.scalar_one_or_none()
    run_id, meta = begin_generation_meta(include_poc)
    snapshot = await _build_snapshot_with_live_gantt(db, estimate, user, locale)
    fingerprint = compute_source_fingerprint(estimate)

    if proposal is None:
        proposal = Proposal(
            estimate_id=estimate_id,
            locale=locale,
            include_poc=include_poc,
            status=ProposalStatus.GENERATING.value,
            source_snapshot=snapshot,
            assessment=None,
            proposal_body=None,
            poc=None,
            diagrams=[],
            milestones=[],
            generation_meta=meta,
            source_fingerprint=fingerprint,
            user_id=user.id,
        )
        db.add(proposal)
    else:
        proposal.include_poc = include_poc
        proposal.status = ProposalStatus.GENERATING.value
        proposal.source_snapshot = snapshot
        proposal.source_fingerprint = fingerprint
        proposal.generation_meta = meta
        proposal.assessment = None
        proposal.proposal_body = None
        proposal.poc = None
        proposal.diagrams = []
        proposal.milestones = []
        proposal.finalized_at = None
        proposal.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(proposal)

    if proposal_generate_sync_enabled() or background_tasks is None:
        await run_generation_sequence(proposal.id, parts="all", db=db)
    else:
        background_tasks.add_task(run_generation_sequence, proposal.id)

    proposal = await get_proposal_or_404(db, proposal.id, user)
    return await to_detail(db, proposal, user)


async def regenerate(
    db: AsyncSession,
    user: User,
    proposal_id: uuid.UUID,
    part: Literal["assessment", "proposal", "poc", "all"],
    background_tasks: BackgroundTasks | None,
) -> ProposalDetail:
    proposal = await get_proposal_or_404(db, proposal_id, user)
    run_id, meta = begin_generation_meta(proposal.include_poc)
    # Preserve done status for parts not being regenerated
    old_parts = (proposal.generation_meta or {}).get("parts") or {}
    if part != "all":
        for key, value in old_parts.items():
            if key != part:
                meta["parts"][key] = value
    proposal.generation_meta = meta
    proposal.status = ProposalStatus.GENERATING.value
    proposal.finalized_at = None
    proposal.updated_at = datetime.utcnow()
    await db.commit()

    if proposal_generate_sync_enabled() or background_tasks is None:
        await run_generation_sequence(proposal.id, parts=part, db=db)
    else:
        background_tasks.add_task(run_generation_sequence, proposal.id, parts=part)

    proposal = await get_proposal_or_404(db, proposal.id, user)
    return await to_detail(db, proposal, user)


def _patch_sections_blob(blob: dict[str, Any] | None, patch: ProposalSectionPatch) -> dict[str, Any]:
    data = dict(blob or {})
    sections = list(data.get("sections") or [])
    found = False
    for idx, section in enumerate(sections):
        if section.get("id") == patch.section_id:
            updated = dict(section)
            if patch.body is not None:
                updated["body"] = patch.body
            if patch.bullets is not None:
                updated["bullets"] = patch.bullets
            if patch.rating is not None:
                updated["rating"] = patch.rating
            if patch.extra:
                updated.update(patch.extra)
            updated["user_edited"] = True
            sections[idx] = updated
            found = True
            break
    if not found:
        raise HTTPException(
            status_code=404,
            detail={"error": f"Section {patch.section_id} not found", "code": "SECTION_NOT_FOUND"},
        )
    data["sections"] = sections
    return data


_POC_BRIEF_FIELDS = {
    "project_name",
    "project_description",
    "business_problem",
    "target_users",
    "technology_stack",
    "constraints",
}


def _patch_poc_brief(blob: dict[str, Any] | None, patch: ProposalSectionPatch) -> dict[str, Any]:
    data = dict(blob or {})
    brief = dict(data.get("project_brief") or {})
    updates = dict(patch.extra or {})
    if patch.body is not None and "body_field" in updates:
        field = str(updates.pop("body_field"))
        if field in _POC_BRIEF_FIELDS:
            brief[field] = patch.body
    for key, value in updates.items():
        if key in _POC_BRIEF_FIELDS and isinstance(value, str):
            brief[key] = value
    data["project_brief"] = brief
    data["brief_user_edited"] = True
    return data


async def patch_sections(
    db: AsyncSession,
    user: User,
    proposal_id: uuid.UUID,
    patches: list[ProposalSectionPatch],
) -> ProposalDetail:
    proposal = await get_proposal_or_404(db, proposal_id, user)
    if proposal.status == ProposalStatus.FINALIZED.value:
        proposal.status = ProposalStatus.DRAFT.value
        proposal.finalized_at = None

    for patch in patches:
        if patch.part == "assessment":
            proposal.assessment = _patch_sections_blob(proposal.assessment, patch)
        elif patch.part == "proposal":
            proposal.proposal_body = _patch_sections_blob(proposal.proposal_body, patch)
        else:
            if not proposal.include_poc:
                raise HTTPException(
                    status_code=400,
                    detail={"error": "Proof of Concept is not included", "code": "POC_NOT_INCLUDED"},
                )
            if patch.section_id == "project_brief":
                proposal.poc = _patch_poc_brief(proposal.poc, patch)
            else:
                proposal.poc = _patch_sections_blob(proposal.poc, patch)

    proposal.updated_at = datetime.utcnow()
    await db.commit()
    proposal = await get_proposal_or_404(db, proposal.id, user)
    return await to_detail(db, proposal, user)


async def refresh_from_estimate(
    db: AsyncSession,
    user: User,
    proposal_id: uuid.UUID,
) -> ProposalDetail:
    proposal = await get_proposal_or_404(db, proposal_id, user)
    estimate = await _get_estimate(db, proposal.estimate_id, user)
    _require_eligible(estimate)

    snapshot = await _build_snapshot_with_live_gantt(db, estimate, user, proposal.locale)
    fingerprint = compute_source_fingerprint(estimate)
    proposal.source_snapshot = snapshot
    proposal.source_fingerprint = fingerprint

    # Refresh bound commercial bullets in cost_summary if not user_edited
    body = dict(proposal.proposal_body or {})
    sections = list(body.get("sections") or [])
    costs = snapshot.get("costs") or {}
    gantt = snapshot.get("gantt") or {}
    for idx, section in enumerate(sections):
        if section.get("user_edited"):
            continue
        if section.get("id") == "cost_summary":
            updated = dict(section)
            if proposal.locale == "ja":
                updated["bullets"] = [
                    f"一次性のプロジェクト費用: {costs.get('one_time_project_cost_jpy')} 円",
                    f"月次の継続費用: {costs.get('monthly_recurring_cost_jpy')} 円",
                    f"初年度合計: {costs.get('first_year_total_jpy')} 円",
                ]
            else:
                updated["bullets"] = [
                    f"One-time project cost: {costs.get('one_time_project_cost_jpy')} JPY",
                    f"Monthly recurring cost: {costs.get('monthly_recurring_cost_jpy')} JPY",
                    f"First-year total: {costs.get('first_year_total_jpy')} JPY",
                ]
            sections[idx] = updated
        if section.get("id") == "timeline_summary":
            updated = dict(section)
            if proposal.locale == "ja":
                updated["body"] = (
                    f"開始: {gantt.get('project_start_date') or '未設定'} / "
                    f"終了: {gantt.get('project_end_date') or '未設定'} / "
                    f"稼働日数目安: {gantt.get('total_working_days') or costs.get('total_effort_days')}"
                )
            else:
                updated["body"] = (
                    f"Start: {gantt.get('project_start_date') or 'TBD'} · "
                    f"End: {gantt.get('project_end_date') or 'TBD'} · "
                    f"Working days: {gantt.get('total_working_days') or costs.get('total_effort_days')}"
                )
            sections[idx] = updated
    if sections:
        body["sections"] = sections
        proposal.proposal_body = body

    # Keep milestones aligned with the live estimate gantt phases.
    locale: Literal["ja", "en"] = "ja" if proposal.locale == "ja" else "en"
    from app.proposals.ai_generate import stub_proposal_body

    _, _, refreshed_milestones = stub_proposal_body(
        snapshot,
        proposal.assessment or {},
        locale,
    )
    proposal.milestones = refreshed_milestones

    # Reprice POC official figures when feature ids still exist
    if proposal.include_poc and proposal.poc:
        poc = dict(proposal.poc)
        official = poc.get("official") or {}
        feature_ids = list(official.get("selected_feature_ids") or [])
        if not feature_ids:
            for section in poc.get("sections") or []:
                if section.get("id") in {"scope_in", "in_scope"}:
                    feature_ids = list(section.get("feature_ids") or [])
                    break
        poc["official"] = price_poc_selection(
            selected_feature_ids=feature_ids,
            features=snapshot.get("features") or [],
            role_breakdown=costs.get("role_breakdown") or [],
            gantt=gantt,
        )
        proposal.poc = poc

    meta = dict(proposal.generation_meta or {})
    meta["last_refreshed_at"] = datetime.utcnow().isoformat() + "Z"
    proposal.generation_meta = meta
    proposal.updated_at = datetime.utcnow()
    if proposal.status == ProposalStatus.FINALIZED.value:
        proposal.status = ProposalStatus.DRAFT.value
        proposal.finalized_at = None
    await db.commit()
    proposal = await get_proposal_or_404(db, proposal.id, user)
    return await to_detail(db, proposal, user)


async def finalize_proposal(
    db: AsyncSession,
    user: User,
    proposal_id: uuid.UUID,
) -> ProposalDetail:
    proposal = await get_proposal_or_404(db, proposal_id, user)
    if not proposal.assessment or not proposal.proposal_body:
        raise HTTPException(
            status_code=400,
            detail={"error": "Proposal content is incomplete", "code": "PROPOSAL_INCOMPLETE"},
        )
    if proposal.include_poc and not proposal.poc:
        raise HTTPException(
            status_code=400,
            detail={"error": "Proof of Concept content is missing", "code": "POC_INCOMPLETE"},
        )
    proposal.status = ProposalStatus.FINALIZED.value
    proposal.finalized_at = datetime.utcnow()
    proposal.updated_at = datetime.utcnow()
    await db.commit()
    proposal = await get_proposal_or_404(db, proposal.id, user)
    return await to_detail(db, proposal, user)


async def delete_proposal(
    db: AsyncSession,
    user: User,
    proposal_id: uuid.UUID,
) -> None:
    from app.storage.factory import get_storage_backend

    proposal = await get_proposal_or_404(db, proposal_id, user)
    storage = get_storage_backend()
    for export in list(proposal.exports or []):
        try:
            await storage.delete(export.storage_path)
        except Exception:
            pass
    await db.delete(proposal)
    await db.commit()
