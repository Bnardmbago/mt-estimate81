from __future__ import annotations

import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.exports.internal_dossier import (
    build_internal_dossier_payload,
    build_internal_export_context,
    generate_internal_markdown,
    generate_internal_pdf,
    load_internal_export_parts,
)
from app.schemas.internal_dossier import InternalDossierResponse


def test_export_context_includes_rate_card_and_proposal_markers():
    report = {
        "project_summary": {"project_name": "P"},
        "extracted": {"cost_drivers": [{"name": "x"}]},
    }
    rate_card = {
        "name": "RC",
        "version_number": 2,
        "settings": {"roles": [{"name": "Engineer", "hourly_rate": 10000}]},
    }
    proposals = [
        {
            "locale": "en",
            "status": "draft",
            "assessment": {"sections": []},
            "proposal_body": None,
            "poc": None,
        }
    ]

    ctx = build_internal_export_context(report, rate_card, proposals, locale="en")

    assert ctx["internal_banner"] == "INTERNAL — DO NOT DISTRIBUTE"
    assert ctx["rate_card"]["settings"]["roles"][0]["name"] == "Engineer"
    assert ctx["proposals"][0]["locale"] == "en"
    assert "cost_drivers" in ctx["report"]["extracted"]
    assert ctx["proposals_status"] == "present"


def test_export_context_marks_missing_proposal():
    ctx = build_internal_export_context({"project_summary": {}}, None, [], locale="en")

    assert ctx["proposals_status"] == "none"


@pytest.mark.asyncio
async def test_dossier_payload_loads_frozen_rate_card_and_proposals():
    estimate_id = uuid.uuid4()
    version_id = uuid.uuid4()
    rate_card_id = uuid.uuid4()
    proposal_id = uuid.uuid4()
    effective_date = datetime(2026, 7, 1, 12, 30)
    estimate = SimpleNamespace(
        id=estimate_id,
        project_name="Portal",
        client_name="ACME",
        status="calculated",
        calculation_result={"total_effort_hours": 10},
        rate_card_version_id=version_id,
        exports=[],
    )
    version = SimpleNamespace(
        id=version_id,
        rate_card_id=rate_card_id,
        version_number=3,
        created_at=effective_date,
        settings={"roles": [{"name": "Engineer", "hourly_rate": 10000}]},
    )
    rate_card = SimpleNamespace(id=rate_card_id, name="Standard")
    proposal = SimpleNamespace(
        id=proposal_id,
        locale="en",
        status="ready",
        include_poc=True,
        assessment={"sections": []},
        proposal_body={"sections": [{"title": "Approach"}]},
        poc={"sections": []},
    )
    rate_card_result = MagicMock()
    rate_card_result.one_or_none.return_value = (version, rate_card)
    proposals_result = MagicMock()
    proposals_result.scalars.return_value.all.return_value = [proposal]
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[rate_card_result, proposals_result])
    report = {"project_summary": {"project_name": "Portal"}}

    with (
        patch("app.exports.internal_dossier.build_report_context", return_value=report) as build,
        patch(
            "app.exports.internal_dossier.is_rate_card_stale_for_estimate",
            new=AsyncMock(return_value=True),
        ),
    ):
        payload = await build_internal_dossier_payload(db, estimate, locale="en")

    assert payload["estimate_id"] == str(estimate_id)
    assert payload["has_calculation"] is True
    assert payload["rate_card_stale"] is True
    assert payload["warnings"] == []
    assert payload["report"] == report
    assert payload["rate_card"] == {
        "rate_card_id": str(rate_card_id),
        "name": "Standard",
        "version_number": 3,
        "effective_date": effective_date.isoformat(),
        "settings": version.settings,
    }
    assert payload["proposals"] == [
        {
            "id": str(proposal_id),
            "locale": "en",
            "status": "ready",
            "include_poc": True,
            "assessment": proposal.assessment,
            "proposal_body": proposal.proposal_body,
            "poc": proposal.poc,
        }
    ]
    assert build.call_args.kwargs["rate_card_name"] == "Standard"
    assert build.call_args.kwargs["rate_card_version_number"] == 3
    assert build.call_args.kwargs["rate_card_effective_date"] == effective_date


@pytest.mark.asyncio
async def test_dossier_payload_warns_when_calculation_is_missing():
    estimate = SimpleNamespace(
        id=uuid.uuid4(),
        project_name="Draft",
        client_name="ACME",
        status="draft",
        calculation_result=None,
        rate_card_version_id=None,
        exports=[],
    )
    proposals_result = MagicMock()
    proposals_result.scalars.return_value.all.return_value = []
    db = AsyncMock()
    db.execute = AsyncMock(return_value=proposals_result)

    with (
        patch("app.exports.internal_dossier.build_report_context") as build,
        patch(
            "app.exports.internal_dossier.is_rate_card_stale_for_estimate",
            new=AsyncMock(return_value=False),
        ),
    ):
        payload = await build_internal_dossier_payload(db, estimate, locale="ja")

    build.assert_not_called()
    assert payload["report"] == {}
    assert payload["has_calculation"] is False
    assert payload["rate_card"] is None
    assert payload["warnings"]


@pytest.mark.asyncio
async def test_load_internal_export_parts_wraps_payload_for_generators():
    payload = {
        "locale": "en",
        "report": {"project_summary": {}},
        "rate_card": None,
        "proposals": [],
    }

    with patch(
        "app.exports.internal_dossier.build_internal_dossier_payload",
        new=AsyncMock(return_value=payload),
    ):
        context = await load_internal_export_parts(AsyncMock(), SimpleNamespace(), "en")

    assert context["internal_banner"] == "INTERNAL — DO NOT DISTRIBUTE"
    assert context["report"] == payload["report"]
    assert context["proposals_status"] == "none"


def test_internal_dossier_response_accepts_documented_shape():
    response = InternalDossierResponse(
        estimate_id=str(uuid.uuid4()),
        project_name="Portal",
        client_name="ACME",
        status="calculated",
        locale="en",
        has_calculation=True,
        rate_card_stale=False,
        warnings=[],
        report={"project_summary": {}},
        rate_card=None,
        proposals=[],
    )

    assert response.rate_card is None
    assert response.proposals == []


def test_internal_markdown_contains_banner_and_rate_card():
    ctx = build_internal_export_context(
        {"project_summary": {"project_name": "Alpha"}},
        {"name": "RC1", "settings": {"roles": [{"name": "PM", "hourly_rate": 1}]}},
        [],
        locale="en",
    )
    md = generate_internal_markdown(ctx)
    assert "INTERNAL — DO NOT DISTRIBUTE" in md
    assert "Alpha" in md
    assert "PM" in md
    assert "none" in md.lower() or "No proposal" in md


def test_internal_pdf_is_pdf_and_html_has_banner():
    from app.exports.pdf import build_internal_dossier_html

    ctx = build_internal_export_context(
        {"project_summary": {"project_name": "Alpha"}, "labels": {}, "extracted": {}},
        {"name": "RC1", "settings": {"roles": []}},
        [],
        locale="en",
    )
    html = build_internal_dossier_html(ctx)
    assert "INTERNAL — DO NOT DISTRIBUTE" in html
    pdf = generate_internal_pdf(ctx)
    assert pdf.startswith(b"%PDF")
