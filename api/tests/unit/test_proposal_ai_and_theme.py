"""Unit tests for proposal AI prompts, schemas, and stub fallback."""

from __future__ import annotations

import pytest

from app.proposals.ai_generate import generate_assessment_content, stub_assessment
from app.proposals.export_context import build_proposal_export_context
from app.proposals.prompts import (
    build_assessment_system_prompt,
    build_assessment_user_prompt,
    build_poc_system_prompt,
    build_poc_user_prompt,
    build_proposal_system_prompt,
)
from app.proposals.schemas_ai import (
    ProposalAssessmentAI,
    ProposalBodyAI,
    ProposalPocAI,
)
from app.exports.theme import EXPORT_THEME, PRIMARY, ACCENT
from app.models.proposal import Proposal
import uuid
from datetime import datetime


def test_proposal_ai_schemas_and_prompts_exist():
    assert ProposalAssessmentAI.model_json_schema()
    assert ProposalBodyAI.model_json_schema()
    assert ProposalPocAI.model_json_schema()

    system_en = build_assessment_system_prompt("en")
    system_ja = build_assessment_system_prompt("ja")
    assert "English" in system_en
    assert "Japanese" in system_ja
    assert "one-time project cost" in system_en.lower()
    assert "Do not use abbreviations like NRC" in system_en or "NRC" in system_en

    proposal_system = build_proposal_system_prompt("en")
    assert "stakeholder" in proposal_system.lower() or "detailed" in proposal_system.lower()
    assert build_poc_system_prompt("en")
    user = build_assessment_user_prompt(
        {
            "project_name": "Demo",
            "client_name": "Acme",
            "costs": {"one_time_project_cost_jpy": 1000},
            "features": [{"id": "f1", "name": "Login", "hours": 8}],
        },
        "en",
    )
    assert "Demo" in user
    assert "1000" in user


@pytest.mark.asyncio
async def test_assessment_ai_failure_falls_back_to_stub(monkeypatch: pytest.MonkeyPatch):
    snapshot = {
        "project_name": "Demo",
        "client_name": "Acme",
        "modules": ["Portal"],
        "risks": ["Delay"],
        "features": [{"id": "a", "name": "AI chat", "hours": 40}],
        "costs": {"one_time_project_cost_jpy": 100},
    }

    async def boom(*_args, **_kwargs):
        raise RuntimeError("AI unavailable")

    monkeypatch.setattr(
        "app.proposals.ai_client.generate_assessment",
        boom,
    )
    result = await generate_assessment_content(snapshot, "en")
    stub = stub_assessment(snapshot, "en")
    assert result["sections"]
    assert len(result["sections"]) == len(stub["sections"])
    assert result["sections"][0]["id"] == stub["sections"][0]["id"]


@pytest.mark.asyncio
async def test_assessment_ai_none_falls_back_to_stub(monkeypatch: pytest.MonkeyPatch):
    snapshot = {
        "project_name": "Demo",
        "client_name": "Acme",
        "modules": [],
        "risks": [],
        "features": [],
        "costs": {},
    }

    async def empty(*_args, **_kwargs):
        return None

    monkeypatch.setattr("app.proposals.ai_client.generate_assessment", empty)
    result = await generate_assessment_content(snapshot, "en")
    assert result["sections"]
    assert result["sections"][0]["body"]


def test_export_context_includes_export_theme():
    proposal = Proposal(
        id=uuid.uuid4(),
        estimate_id=uuid.uuid4(),
        locale="en",
        include_poc=False,
        status="draft",
        source_snapshot={
            "project_name": "Demo",
            "client_name": "Acme",
            "costs": {},
            "gantt": {},
        },
        assessment={"sections": []},
        proposal_body={"sections": []},
        poc=None,
        diagrams=[],
        milestones=[],
        generation_meta={},
        source_fingerprint="x",
        user_id=uuid.uuid4(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    ctx = build_proposal_export_context(proposal, locale="en", variant="full")
    assert ctx["theme"]["primary"] == PRIMARY
    assert ctx["theme"]["accent"] == ACCENT
    assert ctx["theme"] == dict(EXPORT_THEME)


def test_stub_poc_enterprise_shape_and_assumptions():
    from app.proposals.ai_generate import stub_poc
    from app.proposals.schemas_ai import POC_SECTION_IDS

    snapshot = {
        "project_name": "Portal",
        "client_name": "Acme",
        "modules": ["Portal"],
        "risks": [],
        "gaps": [],
        "user_roles": [],
        "functional_requirements": ["Login"],
        "features": [
            {"id": "f1", "name": "AI chat", "hours": 40, "phase": "development", "role": "developer"}
        ],
        "costs": {"role_breakdown": [{"role": "developer", "rate_jpy": 10000}], "one_time_project_cost_jpy": 1},
        "gantt": {"total_working_days": 20, "project_start_date": "2026-08-01"},
        "assumptions": [],
    }
    poc = stub_poc(snapshot, {}, "en")
    assert set(s["id"] for s in poc["sections"]) == set(POC_SECTION_IDS)
    assert poc["project_brief"]["project_name"] == "Portal"
    assert "Assumption:" in poc["project_brief"]["target_users"]
    assert poc["tables"]
    assert poc["diagrams"]
    scope_in = next(s for s in poc["sections"] if s["id"] == "scope_in")
    assert scope_in["feature_ids"] == ["f1"]
    assert poc["official"]["total_effort_hours"] == 40

    poc_ja = stub_poc(snapshot, {}, "ja")
    assert "前提:" in poc_ja["project_brief"]["target_users"]
    assert any(s["id"] == "executive_summary" for s in poc_ja["sections"])


def test_poc_prompt_requires_enterprise_sections():
    prompt = build_poc_system_prompt("en")
    assert "feasibility" in prompt.lower()
    user = build_poc_user_prompt(
        {"project_name": "X", "features": [], "costs": {}, "gantt": {}},
        {},
        "en",
    )
    assert "executive_summary" in user
    assert "scope_in" in user
    assert "project_brief" in user
