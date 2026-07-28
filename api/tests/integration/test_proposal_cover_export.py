from __future__ import annotations

from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.estimate import Estimate, EstimateStatus
from app.models.presentation import PresentationTemplate
from app.models.proposal import Proposal


@pytest.fixture
async def cover_proposal(
    db_session: AsyncSession,
    client: AsyncClient,
) -> Proposal:
    user = client.test_user  # type: ignore[attr-defined]
    estimate = Estimate(
        project_name="Cover Export",
        client_name="Example Client",
        locale="en",
        status=EstimateStatus.CALCULATED.value,
        created_by=user.id,
        form_data={},
        extracted_data={},
        calculation_result={},
        updated_at=datetime.utcnow(),
    )
    db_session.add(estimate)
    await db_session.flush()
    db_session.add(
        PresentationTemplate(
            id="cover-export-test",
            name="Cover Export Test",
            is_default=True,
            is_active=True,
            config={
                "layout": "executive_cover",
                "cover": True,
                "page": {"size": "A4", "orientation": "landscape"},
                "cover_fields": [
                    {
                        "key": "title",
                        "required": True,
                        "emphasis": "title",
                        "content": {
                            "_i18n": {
                                "en": {"label": "Title"},
                                "ja": {"label": "件名"},
                            }
                        },
                    }
                ],
                "cover_design": {"assets": []},
            },
        )
    )
    proposal = Proposal(
        estimate_id=estimate.id,
        locale="en",
        include_poc=False,
        status="ready",
        source_snapshot={
            "project_name": "Cover Export",
            "client_name": "Example Client",
            "costs": {},
        },
        assessment={"sections": []},
        proposal_body={"sections": []},
        diagrams=[],
        milestones=[],
        generation_meta={},
        source_fingerprint="test",
        user_id=user.id,
        template_id="cover-export-test",
        presentation_meta={},
        cover_values={},
    )
    db_session.add(proposal)
    await db_session.commit()
    await db_session.refresh(proposal)
    return proposal


@pytest.mark.asyncio
async def test_cover_values_required_validation_and_export_override(
    client: AsyncClient,
    auth_headers: dict[str, str],
    cover_proposal: Proposal,
):
    proposal_id = cover_proposal.id

    missing = await client.post(
        f"/proposals/{proposal_id}/export",
        headers=auth_headers,
        json={"format": "md", "include_cover": True, "locale": "ja"},
    )
    assert missing.status_code == 400, missing.text
    assert missing.json()["code"] == "COVER_VALUES_REQUIRED"
    assert missing.json()["details"]["missing_keys"] == ["title"]

    patched = await client.patch(
        f"/proposals/{proposal_id}/cover-values",
        headers=auth_headers,
        json={"locale": "ja", "values": {"title": "役員向け提案書"}},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["cover_values"] == {
        "title": {"_i18n": {"ja": {"value": "役員向け提案書"}}}
    }

    without_cover = await client.post(
        f"/proposals/{proposal_id}/export",
        headers=auth_headers,
        json={"format": "md", "include_cover": False, "locale": "ja"},
    )
    assert without_cover.status_code == 200, without_cover.text
    without_download = await client.get(
        f"/proposals/{proposal_id}/exports/{without_cover.json()['id']}/download",
        headers=auth_headers,
    )
    assert "役員向け提案書" not in without_download.content.decode("utf-8")

    with_cover = await client.post(
        f"/proposals/{proposal_id}/export",
        headers=auth_headers,
        json={"format": "md", "include_cover": True, "locale": "ja"},
    )
    assert with_cover.status_code == 200, with_cover.text
    with_download = await client.get(
        f"/proposals/{proposal_id}/exports/{with_cover.json()['id']}/download",
        headers=auth_headers,
    )
    text = with_download.content.decode("utf-8")
    assert "**件名:** 役員向け提案書" in text


@pytest.mark.asyncio
async def test_export_cover_values_override_is_request_scoped(
    client: AsyncClient,
    auth_headers: dict[str, str],
    cover_proposal: Proposal,
):
    proposal_id = cover_proposal.id
    patched = await client.patch(
        f"/proposals/{proposal_id}/cover-values",
        headers=auth_headers,
        json={"locale": "en", "values": {"title": "Stored title"}},
    )
    assert patched.status_code == 200, patched.text

    exported = await client.post(
        f"/proposals/{proposal_id}/export",
        headers=auth_headers,
        json={
            "format": "md",
            "include_cover": True,
            "locale": "en",
            "cover_values": {"title": "One-off title"},
        },
    )
    assert exported.status_code == 200, exported.text
    downloaded = await client.get(
        f"/proposals/{proposal_id}/exports/{exported.json()['id']}/download",
        headers=auth_headers,
    )
    assert "**Title:** One-off title" in downloaded.content.decode("utf-8")

    detail = await client.get(f"/proposals/{proposal_id}", headers=auth_headers)
    assert detail.json()["cover_values"]["title"]["_i18n"]["en"]["value"] == "Stored title"
