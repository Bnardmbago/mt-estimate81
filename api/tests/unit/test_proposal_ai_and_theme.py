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
    build_proposal_user_prompt,
)
from app.proposals.schemas_ai import (
    ProposalAssessmentAI,
    ProposalBodyAI,
    ProposalPocAI,
)
from app.exports.theme import EXPORT_THEME, PRIMARY, ACCENT
from app.models.proposal import Proposal
from app.presentation.resolver import PresentationBundle
from app.presentation.seeds import (
    CORPORATE_NAVY_CONFIG,
    MODERN_SLATE_CONFIG,
    WARM_EDITORIAL_CONFIG,
)
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

    proposal_system = build_proposal_system_prompt("en", purpose="detailed")
    assert "stakeholder" in proposal_system.lower() or "detailed" in proposal_system.lower()
    assert "several sentences" in proposal_system.lower() or "2–4" in proposal_system or "2-4" in proposal_system
    assert "mermaid" in proposal_system.lower()
    assert "table" in proposal_system.lower()
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
    assert ctx["layout"]["layout"] == "linear"
    assert "style" in ctx


def test_theme_specialized_colors_fall_back_to_accent_and_preserve_overrides():
    fallback = PresentationBundle(
        theme_id="fallback",
        style_id="comfortable",
        template_id="classic-linear",
        theme_tokens={"colors": {"accent": "C026D3"}},
    ).theme_color_map()
    explicit = PresentationBundle(
        theme_id="explicit",
        style_id="comfortable",
        template_id="classic-linear",
        theme_tokens={
            "colors": {
                "accent": "C026D3",
                "chart": "0EA5E9",
                "callout": "F59E0B",
                "table_highlight": "10B981",
            }
        },
    ).theme_color_map()

    assert fallback["chart"] == "C026D3"
    assert fallback["callout"] == "C026D3"
    assert fallback["table_highlight"] == "C026D3"
    assert explicit["chart"] == "0EA5E9"
    assert explicit["callout"] == "F59E0B"
    assert explicit["table_highlight"] == "10B981"


def test_theme_color_map_normalizes_every_output_to_safe_unprefixed_hex():
    colors = PresentationBundle(
        theme_id="unsafe",
        style_id="comfortable",
        template_id="classic-linear",
        theme_tokens={
            "colors": {
                "primary": "red; background:url(javascript:alert(1))",
                "primary_light": "url(https://invalid)",
                "surface": "#abcdef",
                "border": "E2E8F0}",
                "border_light": "not-a-color",
                "text_body": "1E293B; color:red",
                "text_muted": "",
                "accent": "2563EB);--owned:1",
                "text_on_primary": "rgb(0,0,0)",
                "table_header": "var(--evil)",
                "table_row_alt": "#F1F5F9",
                "chart": "url(data:text/css,evil)",
                "callout": "F59E0B;",
                "table_highlight": "#10B981",
            }
        },
    ).theme_color_map()

    assert all(
        len(value) == 6 and all(character in "0123456789abcdefABCDEF" for character in value)
        for value in colors.values()
    )
    assert colors["primary"] == EXPORT_THEME["primary"]
    assert colors["surface"] == "abcdef"
    assert colors["accent"] == EXPORT_THEME["accent"]
    assert colors["chart"] == EXPORT_THEME["accent"]
    assert colors["callout"] == EXPORT_THEME["accent"]
    assert colors["table_highlight"] == "10B981"


def test_seeded_theme_callouts_remain_linked_to_each_theme_accent():
    for seed in (
        CORPORATE_NAVY_CONFIG,
        MODERN_SLATE_CONFIG,
        WARM_EDITORIAL_CONFIG,
    ):
        assert "callout" not in seed["colors"]
        colors = PresentationBundle(
            theme_id="seed",
            style_id="comfortable",
            template_id="classic-linear",
            theme_tokens=seed,
        ).theme_color_map()
        assert colors["callout"] == colors["accent"]


def test_presentation_recommend_prompt_exists():
    from app.proposals.prompts import (
        build_presentation_recommend_system_prompt,
        build_presentation_recommend_user_prompt,
    )
    from app.proposals.schemas_ai import PresentationRecommendAI

    assert PresentationRecommendAI.model_json_schema()
    system = build_presentation_recommend_system_prompt("en")
    assert "Theme" in system
    user = build_presentation_recommend_user_prompt(
        {"project_name": "Demo", "costs": {}, "features": []},
        {
            "themes": [{"id": "corporate-navy", "name": "Navy", "description": ""}],
            "styles": [{"id": "comfortable", "name": "Comfortable", "description": ""}],
            "templates": [{"id": "classic-linear", "name": "Linear", "description": ""}],
        },
        "en",
        include_poc=False,
    )
    assert "corporate-navy" in user



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
    assert len(poc["tables"]) >= 3
    assert len(poc["diagrams"]) >= 2
    assert any(d["id"] == "poc_validation_flow" for d in poc["diagrams"])
    scope_in = next(s for s in poc["sections"] if s["id"] == "scope_in")
    assert scope_in["feature_ids"] == ["f1"]
    assert poc["official"]["total_effort_hours"] == 40

    poc_ja = stub_poc(snapshot, {}, "ja")
    assert "前提:" in poc_ja["project_brief"]["target_users"]
    assert any(s["id"] == "executive_summary" for s in poc_ja["sections"])
    assert len(poc_ja["tables"]) >= 3
    assert len(poc_ja["diagrams"]) >= 2


def test_stub_proposal_includes_tables_and_diagrams():
    from app.proposals.ai_generate import stub_proposal_body

    snapshot = {
        "project_name": "Portal",
        "client_name": "Acme",
        "modules": ["Portal"],
        "risks": ["Integration risk"],
        "features": [{"id": "f1", "name": "Login", "hours": 8}],
        "costs": {
            "one_time_project_cost_jpy": 1000,
            "monthly_recurring_cost_jpy": 100,
            "first_year_total_jpy": 2200,
            "total_effort_days": 10,
        },
        "gantt": {"total_working_days": 10, "project_start_date": "2026-08-01"},
        "assumptions": [],
    }
    body, diagrams, milestones = stub_proposal_body(snapshot, {}, "en")
    assert len(body["sections"]) >= 8
    assert len(body["tables"]) >= 2
    assert len(diagrams) >= 2
    assert any(d["id"] == "delivery_flow" for d in diagrams)
    assert milestones

    proposal_user = build_proposal_user_prompt(snapshot, {}, "en", purpose="detailed")
    assert "multi-sentence" in proposal_user.lower()
    assert "mermaid" in proposal_user.lower()
    assert "tables[]" in proposal_user


def test_poc_prompt_requires_enterprise_sections():
    prompt = build_poc_system_prompt("en", purpose="detailed")
    assert "feasibility" in prompt.lower()
    assert "several sentences" in prompt.lower() or "2–4" in prompt or "2-4" in prompt
    assert "mermaid" in prompt.lower()
    assert "table" in prompt.lower()
    user = build_poc_user_prompt(
        {"project_name": "X", "features": [], "costs": {}, "gantt": {}},
        {},
        "en",
        purpose="detailed",
    )
    assert "executive_summary" in user
    assert "scope_in" in user
    assert "project_brief" in user
    assert "mermaid" in user.lower()
    assert "tables[]" in user
