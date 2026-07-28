import os
import uuid
from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import create_access_token, hash_password
from app.models.estimate import Estimate, EstimateStatus, FeatureItem
from app.models.user import User


@pytest.fixture
async def calculated_estimate(db_session: AsyncSession, client: AsyncClient) -> Estimate:
    user = client.test_user  # type: ignore[attr-defined]
    estimate = Estimate(
        project_name="Proposal Source",
        client_name="Stakeholder Co",
        locale="en",
        status=EstimateStatus.CALCULATED.value,
        created_by=user.id,
        form_data={},
        extracted_data={
            "modules": ["Portal", "AI Assistant"],
            "risks": ["Model accuracy", "Integration delay"],
            "functional_requirements": ["Users can ask questions"],
            "non_functional_requirements": ["Available during business hours"],
            "user_roles": ["Admin", "User"],
            "estimate_exclusions": ["Hardware procurement"],
        },
        calculation_result={
            "total_effort_hours": 120,
            "total_effort_days": 15,
            "first_year_total_jpy": 5_000_000,
            "nrc": {"total_jpy": 4_000_000},
            "rc": {"monthly_total_jpy": 80_000, "annual_total_jpy": 960_000},
            "role_breakdown": [{"role": "developer", "rate_jpy": 12000, "hours": 120, "cost_jpy": 1_440_000}],
            "phase_breakdown": [],
            "gantt": {
                "project_start_date": "2026-08-01",
                "project_end_date": "2026-10-01",
                "total_working_days": 40,
                "phases": [
                    {
                        "phase": "development",
                        "start_date": "2026-08-01",
                        "end_date": "2026-09-15",
                        "duration_working_days": 30,
                    }
                ],
                "tasks": [],
            },
        },
        updated_at=datetime.utcnow(),
    )
    db_session.add(estimate)
    await db_session.flush()
    db_session.add(
        FeatureItem(
            estimate_id=estimate.id,
            sort_order=1,
            name="AI Assistant core",
            description="Validate AI responses",
            hours=40,
            phase="development",
            role="developer",
        )
    )
    db_session.add(
        FeatureItem(
            estimate_id=estimate.id,
            sort_order=2,
            name="User login",
            description="Auth",
            hours=8,
            phase="development",
            role="developer",
        )
    )
    await db_session.commit()
    await db_session.refresh(estimate)
    return estimate


@pytest.mark.asyncio
async def test_generate_proposal_and_export(
    client: AsyncClient,
    auth_headers: dict[str, str],
    calculated_estimate: Estimate,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("PROPOSAL_GENERATE_SYNC", "1")
    response = await client.post(
        "/proposals/generate",
        headers=auth_headers,
        json={
            "estimate_id": str(calculated_estimate.id),
            "locale": "en",
            "include_poc": True,
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] in {"draft", "generating", "ready"}
    assert payload["assessment"] is not None
    assert payload["proposal_body"] is not None
    assert payload["poc"] is not None
    assert payload["poc"]["official"]["total_effort_hours"] > 0
    assert payload["poc"]["project_brief"]["project_name"]
    assert any(s["id"] == "executive_summary" for s in payload["poc"]["sections"])
    assert any(s["id"] == "scope_in" for s in payload["poc"]["sections"])
    assert "NRC" not in str(payload["proposal_body"])

    proposal_id = payload["id"]

    patch = await client.patch(
        f"/proposals/{proposal_id}/sections",
        headers=auth_headers,
        json={
            "sections": [
                {
                    "part": "proposal",
                    "section_id": "executive_summary",
                    "body": "Edited executive summary for stakeholders.",
                }
            ]
        },
    )
    assert patch.status_code == 200, patch.text
    assert "Edited executive summary" in str(patch.json()["proposal_body"])

    export = await client.post(
        f"/proposals/{proposal_id}/export",
        headers=auth_headers,
        json={"format": "md", "variant": "full"},
    )
    assert export.status_code == 200, export.text
    assert export.json()["format"] == "md"

    downloads = await client.get(
        f"/proposals/{proposal_id}/exports/{export.json()['id']}/download",
        headers=auth_headers,
    )
    assert downloads.status_code == 200
    text = downloads.content.decode("utf-8")
    assert "One-time project cost" in text
    assert "NRC" not in text
    assert "Edited executive summary" in text

    preview = await client.get(
        f"/proposals/{proposal_id}/exports/{export.json()['id']}/download?inline=1",
        headers=auth_headers,
    )
    assert preview.status_code == 200
    assert "inline" in preview.headers.get("content-disposition", "")

    finalize = await client.post(f"/proposals/{proposal_id}/finalize", headers=auth_headers)
    assert finalize.status_code == 200
    assert finalize.json()["status"] == "finalized"


@pytest.mark.asyncio
async def test_contact_user_cannot_access_proposals(
    client: AsyncClient,
    db_session: AsyncSession,
    calculated_estimate: Estimate,
):
    contact = User(
        id=uuid.uuid4(),
        email="contact-proposal@example.com",
        password_hash=hash_password("pass"),
        display_name="Contact",
        is_admin=False,
        preferred_locale="en",
        account_type="contact",
    )
    db_session.add(contact)
    await db_session.commit()
    token = create_access_token({"sub": str(contact.id), "is_admin": False})
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/proposals", headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_proposal(
    client: AsyncClient,
    auth_headers: dict[str, str],
    calculated_estimate: Estimate,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("PROPOSAL_GENERATE_SYNC", "1")
    created = await client.post(
        "/proposals/generate",
        headers=auth_headers,
        json={
            "estimate_id": str(calculated_estimate.id),
            "locale": "en",
            "include_poc": False,
        },
    )
    assert created.status_code == 200, created.text
    proposal_id = created.json()["id"]

    deleted = await client.delete(f"/proposals/{proposal_id}", headers=auth_headers)
    assert deleted.status_code == 204

    missing = await client.get(f"/proposals/{proposal_id}", headers=auth_headers)
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_generate_proposal_persists_rich_ai_bodies(
    client: AsyncClient,
    auth_headers: dict[str, str],
    calculated_estimate: Estimate,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("PROPOSAL_GENERATE_SYNC", "1")

    rich_body = (
        "This detailed stakeholder assessment explains feasibility across scope, "
        "delivery readiness, and commercial constraints drawn only from the estimate snapshot. "
        "It expands into multiple sentences so decision makers can review risk posture and next steps."
    )

    async def rich_assessment(snapshot, locale):
        return {
            "sections": [
                {
                    "id": "feasibility",
                    "title": "Overall feasibility",
                    "body": rich_body,
                    "rating": "medium",
                    "user_edited": False,
                },
                {
                    "id": "readiness",
                    "title": "Project readiness",
                    "body": rich_body,
                    "rating": "medium",
                    "user_edited": False,
                },
                {
                    "id": "complexity",
                    "title": "Complexity",
                    "body": rich_body,
                    "rating": "medium",
                    "user_edited": False,
                },
                {
                    "id": "risks",
                    "title": "Risks",
                    "body": rich_body,
                    "bullets": ["Model accuracy"],
                    "user_edited": False,
                },
                {
                    "id": "recommendation",
                    "title": "Recommendation",
                    "body": rich_body,
                    "user_edited": False,
                },
                {
                    "id": "poc_recommendation",
                    "title": "Proof of Concept recommendation",
                    "body": rich_body,
                    "poc_recommended": True,
                    "user_edited": False,
                },
            ],
            "poc_recommended": True,
            "summary_cost_note": "",
        }

    async def rich_proposal(snapshot, assessment, locale):
        sections = [
            {
                "id": sid,
                "title": sid.replace("_", " ").title(),
                "body": rich_body,
                "user_edited": False,
            }
            for sid in [
                "executive_summary",
                "objectives",
                "proposed_solution",
                "included_scope",
                "excluded_scope",
                "deliverables",
                "timeline_summary",
                "cost_summary",
                "assumptions",
                "risks",
                "next_steps",
            ]
        ]
        return (
            {"sections": sections},
            [
                {
                    "id": "solution_overview",
                    "title": "Solution overview",
                    "engine": "mermaid",
                    "source": "flowchart LR\n  A-->B",
                }
            ],
            [{"id": "m1", "name": "Kickoff", "date": "2026-08-01"}],
        )

    async def rich_poc_with_ids(snapshot, assessment, locale):
        from app.proposals.schemas_ai import POC_SECTION_IDS

        features = snapshot.get("features") or []
        fid = features[0]["id"] if features else None
        sections = [
            {
                "id": sid,
                "title": sid.replace("_", " ").title(),
                "body": rich_body,
                "user_edited": False,
                **({"feature_ids": [fid] if fid else []} if sid == "scope_in" else {}),
            }
            for sid in POC_SECTION_IDS
        ]
        return {
            "project_brief": {
                "project_name": snapshot.get("project_name") or "Demo",
                "project_description": rich_body,
                "business_problem": rich_body,
                "target_users": "Admin, User",
                "technology_stack": "Portal, AI Assistant",
                "constraints": "Time-boxed validation",
            },
            "sections": sections,
            "tables": [
                {
                    "id": "risks",
                    "title": "Risks",
                    "headers": ["Risk", "Mitigation"],
                    "rows": [["Model accuracy", "Validate early"]],
                }
            ],
            "diagrams": [
                {
                    "id": "poc_architecture",
                    "title": "Architecture",
                    "engine": "mermaid",
                    "source": "flowchart LR\n  A-->B",
                }
            ],
            "milestones": [{"id": "m1", "name": "Kickoff", "date": "2026-08-01"}],
            "suggested_validation_window": "About three weeks for stakeholder validation.",
            "official": {"selected_feature_ids": [fid] if fid else []},
        }

    from app.proposals import ai_client

    monkeypatch.setattr(ai_client, "generate_assessment", rich_assessment)
    monkeypatch.setattr(ai_client, "generate_proposal", rich_proposal)
    monkeypatch.setattr(ai_client, "generate_poc", rich_poc_with_ids)

    response = await client.post(
        "/proposals/generate",
        headers=auth_headers,
        json={
            "estimate_id": str(calculated_estimate.id),
            "locale": "en",
            "include_poc": True,
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assessment_body = payload["assessment"]["sections"][0]["body"]
    proposal_body = payload["proposal_body"]["sections"][0]["body"]
    assert len(assessment_body) > 120
    assert len(proposal_body) > 120
    assert "detailed stakeholder assessment" in assessment_body
    assert payload["poc"]["suggested_validation_window"]
    assert payload["poc"]["project_brief"]["project_name"]
    assert len(payload["poc"]["sections"]) >= 17
    assert payload["poc"]["tables"]
    assert payload["poc"]["diagrams"]


async def _seed_presentation(db_session: AsyncSession) -> None:
    from app.models.presentation import PresentationStyle, PresentationTemplate, PresentationTheme
    from app.presentation.seeds import (
        CLASSIC_LINEAR_TEMPLATE,
        COMFORTABLE_STYLE,
        CORPORATE_NAVY_CONFIG,
        EXECUTIVE_COVER_TEMPLATE,
        MODERN_SLATE_CONFIG,
        SPACIOUS_STYLE,
    )

    existing = await db_session.get(PresentationTheme, "corporate-navy")
    if existing is not None:
        return
    db_session.add_all(
        [
            PresentationTheme(
                id="corporate-navy",
                name="Corporate Navy",
                is_default=True,
                is_active=True,
                config=CORPORATE_NAVY_CONFIG,
            ),
            PresentationTheme(
                id="modern-slate",
                name="Modern Slate",
                is_default=False,
                is_active=True,
                config=MODERN_SLATE_CONFIG,
            ),
            PresentationStyle(
                id="comfortable",
                name="Comfortable",
                is_default=True,
                is_active=True,
                config=COMFORTABLE_STYLE,
            ),
            PresentationStyle(
                id="spacious",
                name="Spacious",
                is_default=False,
                is_active=True,
                config=SPACIOUS_STYLE,
            ),
            PresentationTemplate(
                id="classic-linear",
                name="Classic Linear",
                is_default=True,
                is_active=True,
                config=CLASSIC_LINEAR_TEMPLATE,
            ),
            PresentationTemplate(
                id="executive-cover",
                name="Executive Cover",
                is_default=False,
                is_active=True,
                config=EXECUTIVE_COVER_TEMPLATE,
            ),
        ]
    )
    await db_session.commit()


@pytest.mark.asyncio
async def test_proposal_presentation_ids_and_export_override(
    client: AsyncClient,
    auth_headers: dict[str, str],
    calculated_estimate: Estimate,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("PROPOSAL_GENERATE_SYNC", "1")
    await _seed_presentation(db_session)

    async def fake_recommend(*_args, **_kwargs):
        return (
            "modern-slate",
            "spacious",
            "executive-cover",
            {"source": "ai", "recommended": {}, "warnings": []},
        )

    monkeypatch.setattr(
        "app.proposals.service.recommend_presentation",
        fake_recommend,
    )

    response = await client.post(
        "/proposals/generate",
        headers=auth_headers,
        json={
            "estimate_id": str(calculated_estimate.id),
            "locale": "en",
            "include_poc": False,
            "theme_id": "modern-slate",
            "style_id": "spacious",
            "template_id": "executive-cover",
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["theme_id"] == "modern-slate"
    assert payload["style_id"] == "spacious"
    assert payload["template_id"] == "executive-cover"
    assert payload["presentation_css_vars"]["--proposal-primary"]
    proposal_id = payload["id"]

    patch = await client.patch(
        f"/proposals/{proposal_id}/presentation",
        headers=auth_headers,
        json={"theme_id": "corporate-navy"},
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["theme_id"] == "corporate-navy"
    assert patch.json()["style_id"] == "spacious"

    export = await client.post(
        f"/proposals/{proposal_id}/export",
        headers=auth_headers,
        json={
            "format": "md",
            "variant": "full",
            "theme_id": "modern-slate",
            "style_id": "comfortable",
            "template_id": "classic-linear",
        },
    )
    assert export.status_code == 200, export.text
    export_row = export.json()
    assert export_row["theme_id"] == "modern-slate"
    assert export_row["style_id"] == "comfortable"
    assert export_row["template_id"] == "classic-linear"

    detail = await client.get(f"/proposals/{proposal_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["theme_id"] == "corporate-navy"
    assert detail.json()["style_id"] == "spacious"
    assert detail.json()["template_id"] == "executive-cover"

    catalogs = await client.get("/presentation/themes", headers=auth_headers)
    assert catalogs.status_code == 200
    assert any(row["id"] == "corporate-navy" for row in catalogs.json())

    defaults = await client.get("/presentation/defaults", headers=auth_headers)
    assert defaults.status_code == 200
    assert defaults.json()["theme_id"] == "corporate-navy"
