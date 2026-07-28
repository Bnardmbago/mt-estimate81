"""Tests for proposal generation purpose presets and admin settings."""

from __future__ import annotations

import pytest

from app.admin.ai_instruction_config import merge_parameters
from app.proposals.generation_presets import (
    DEFAULT_PROPOSAL_AI_SETTINGS,
    PURPOSE_PRESETS,
    budget_parameters,
    coerce_purpose,
    normalize_proposal_ai_settings,
    purpose_for_part,
)
from app.proposals.prompts import (
    build_poc_system_prompt,
    build_proposal_system_prompt,
    build_proposal_user_prompt,
)


def test_purpose_presets_have_expected_budgets():
    assert PURPOSE_PRESETS["concise"].max_tokens == 4096
    assert PURPOSE_PRESETS["standard"].max_tokens == 8192
    assert PURPOSE_PRESETS["detailed"].max_tokens == 16384
    assert PURPOSE_PRESETS["detailed"].timeout_seconds == 150
    assert PURPOSE_PRESETS["detailed"].min_tables_poc == 3


def test_normalize_proposal_ai_settings_defaults_and_coerce():
    assert normalize_proposal_ai_settings(None) == DEFAULT_PROPOSAL_AI_SETTINGS
    assert normalize_proposal_ai_settings({"proposal_purpose": "nope"})["proposal_purpose"] == "detailed"
    assert coerce_purpose("concise", fallback="standard") == "concise"


def test_prompts_vary_by_purpose():
    concise = build_proposal_system_prompt("en", purpose="concise")
    detailed = build_proposal_system_prompt("en", purpose="detailed")
    assert "1–2 sentences" in concise or "1-2 sentences" in concise or "concise" in concise.lower()
    assert "2–4 short paragraphs" in detailed or "2-4 short paragraphs" in detailed
    assert "at least 1 mermaid" in concise.lower() or "at least 1" in concise.lower()
    assert "at least 2 mermaid" in detailed.lower()

    poc_concise = build_poc_system_prompt("en", purpose="concise")
    poc_detailed = build_poc_system_prompt("en", purpose="detailed")
    assert "at least 1 table" in poc_concise.lower() or "at least 1" in poc_concise.lower()
    assert "at least 3 tables" in poc_detailed.lower()

    user = build_proposal_user_prompt(
        {"project_name": "X", "features": [], "costs": {}, "gantt": {}},
        {},
        "en",
        purpose="detailed",
    )
    assert "multi-sentence" in user.lower()


def test_merge_parameters_purpose_defaults_overridden_by_layer():
    purpose_defaults = budget_parameters("detailed")
    merged = merge_parameters(
        "proposal_body",
        {"max_tokens": 4096, "timeout_seconds": 90},
        purpose_defaults=purpose_defaults,
    )
    assert merged["max_tokens"] == 4096
    assert merged["timeout_seconds"] == 90
    assert merged["temperature"] == purpose_defaults["temperature"]


def test_stub_proposal_scales_visuals_for_concise():
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
    body, diagrams, _ = stub_proposal_body(snapshot, {}, "en", purpose="concise")
    assert len(diagrams) == 1
    assert len(body["tables"]) == 1

    body_d, diagrams_d, _ = stub_proposal_body(snapshot, {}, "en", purpose="detailed")
    assert len(diagrams_d) >= 2
    assert len(body_d["tables"]) >= 2


@pytest.mark.asyncio
async def test_proposal_ai_settings_admin_api(client, admin_headers):
    response = await client.get("/admin/proposal-ai-settings", headers=admin_headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["assessment_purpose"] == "standard"
    assert payload["proposal_purpose"] == "detailed"
    assert payload["poc_purpose"] == "detailed"
    assert "concise" in payload["purposes"]

    bad = await client.put(
        "/admin/proposal-ai-settings",
        headers=admin_headers,
        json={"proposal_purpose": "ultra"},
    )
    assert bad.status_code == 422

    ok = await client.put(
        "/admin/proposal-ai-settings",
        headers=admin_headers,
        json={"proposal_purpose": "concise", "poc_purpose": "standard"},
    )
    assert ok.status_code == 200, ok.text
    saved = ok.json()
    assert saved["proposal_purpose"] == "concise"
    assert saved["poc_purpose"] == "standard"
    assert purpose_for_part(
        {
            "assessment_purpose": "standard",
            "proposal_purpose": "concise",
            "poc_purpose": "standard",
        },
        "proposal",
    ) == "concise"
