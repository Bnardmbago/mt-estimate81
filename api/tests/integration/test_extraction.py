import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import ExtractedRequirements, FeatureItemSuggestion, MaintenanceAssumptions
from app.models.estimate import Estimate, EstimateStatus


@pytest.fixture
def mock_ai_provider():
    class MockProvider:
        async def extract_requirements(self, form_data, document_texts, locale, **kwargs):
            return ExtractedRequirements(
                functional_requirements=["User login", "Dashboard"],
                non_functional_requirements=["99.9% uptime"],
                user_roles=["Admin", "User"],
                modules=["Auth", "Dashboard"],
                external_systems=[],
                risks=["Tight deadline"],
                gaps=["Budget unclear"],
                confidence_notes="High confidence on auth scope",
                feature_items=[
                    FeatureItemSuggestion(
                        name="User login",
                        description="OAuth login flow",
                        suggested_hours=40,
                        phase="development",
                        role="developer",
                    ),
                    FeatureItemSuggestion(
                        name="Dashboard",
                        description="Main dashboard view",
                        suggested_hours=24,
                        phase="development",
                        role="developer",
                    ),
                ],
                maintenance_assumptions=MaintenanceAssumptions(
                    monthly_support_hours=20,
                    notes="Business hours support",
                ),
            )

    return MockProvider()


from app.models.rate_card import RateCardVersion


async def assign_rate_card(
    client: AsyncClient,
    estimate_id: str,
    active_rate_card: RateCardVersion,
    headers: dict[str, str],
) -> None:
    response = await client.patch(
        f"/estimates/{estimate_id}",
        json={"rate_card_id": str(active_rate_card.rate_card_id)},
        headers=headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_extract_auto_creates_rate_card(
    client: AsyncClient,
    auth_headers: dict[str, str],
    mock_ai_provider,
    monkeypatch: pytest.MonkeyPatch,
):
    from app.ai.schemas import (
        GeneratedLineItem,
        GeneratedPhasePercentage,
        GeneratedProductivity,
        GeneratedRateCardSuggestion,
        GeneratedRoleRate,
    )

    monkeypatch.setenv("EXTRACT_SYNC", "1")

    class CombinedProvider:
        async def extract_requirements(self, form_data, document_texts, locale, **kwargs):
            return await mock_ai_provider.extract_requirements(
                form_data, document_texts, locale, **kwargs
            )

        async def generate_rate_card(self, **kwargs):
            return GeneratedRateCardSuggestion(
                development_approach="traditional",
                roles=[
                    GeneratedRoleRate(name="PM", hourly_rate_jpy=9000),
                    GeneratedRoleRate(name="developer", hourly_rate_jpy=7000),
                ],
                phases=[
                    GeneratedPhasePercentage(name="requirement", percentage=0.10),
                    GeneratedPhasePercentage(name="design", percentage=0.15),
                    GeneratedPhasePercentage(name="development", percentage=0.40),
                    GeneratedPhasePercentage(name="testing", percentage=0.25),
                    GeneratedPhasePercentage(name="deployment", percentage=0.10),
                ],
                contingency_rate=0.15,
                overhead_rate=0.10,
                tax_rate=0.10,
                productivity=GeneratedProductivity(hours_per_feature_default=32),
                setup_cost_items=[
                    GeneratedLineItem(name="Infrastructure setup", amount_jpy=300000),
                    GeneratedLineItem(name="Tooling licenses", amount_jpy=150000),
                ],
                monthly_rc_items=[
                    GeneratedLineItem(name="Cloud hosting", amount_jpy=80000),
                ],
                generation_notes="Generated from project form.",
                used_default_assumptions=[],
            )

    create = await client.post(
        "/estimates",
        json={
            "project_name": "Auto Card Project",
            "client_name": "ACME",
            "locale": "en",
            "form_data": {"main_functional_needs": "Customer portal"},
        },
        headers=auth_headers,
    )
    estimate_id = create.json()["id"]

    combined = CombinedProvider()
    with patch(
        "app.rate_cards.generation.get_ai_provider",
        new=AsyncMock(return_value=combined),
    ), patch(
        "app.estimates.extraction.get_ai_provider",
        new=AsyncMock(return_value=combined),
    ):
        extract = await client.post(f"/estimates/{estimate_id}/extract", headers=auth_headers)
        assert extract.status_code == 202

    detail = await client.get(f"/estimates/{estimate_id}", headers=auth_headers)
    payload = detail.json()
    assert payload["rate_card_id"] is not None
    assert payload["status"] == "review"

    card = await client.get(
        f"/rate-cards/cards/{payload['rate_card_id']}",
        headers=auth_headers,
    )
    assert card.status_code == 200
    settings = card.json()["settings"]
    assert len(settings["setup_cost_items"]) >= 2
    assert len(settings["monthly_rc_items"]) >= 1


@pytest.mark.asyncio
async def test_re_extract_preserves_edited_rate_card(
    client: AsyncClient,
    auth_headers: dict[str, str],
    mock_ai_provider,
    monkeypatch: pytest.MonkeyPatch,
):
    from app.ai.schemas import (
        GeneratedLineItem,
        GeneratedPhasePercentage,
        GeneratedProductivity,
        GeneratedRateCardSuggestion,
        GeneratedRoleRate,
    )

    monkeypatch.setenv("EXTRACT_SYNC", "1")

    class CombinedProvider:
        async def extract_requirements(self, form_data, document_texts, locale, **kwargs):
            return await mock_ai_provider.extract_requirements(
                form_data, document_texts, locale, **kwargs
            )

        async def generate_rate_card(self, **kwargs):
            return GeneratedRateCardSuggestion(
                development_approach="traditional",
                roles=[GeneratedRoleRate(name="developer", hourly_rate_jpy=7000)],
                phases=[
                    GeneratedPhasePercentage(name="requirement", percentage=0.10),
                    GeneratedPhasePercentage(name="design", percentage=0.15),
                    GeneratedPhasePercentage(name="development", percentage=0.40),
                    GeneratedPhasePercentage(name="testing", percentage=0.25),
                    GeneratedPhasePercentage(name="deployment", percentage=0.10),
                ],
                contingency_rate=0.15,
                overhead_rate=0.10,
                tax_rate=0.10,
                productivity=GeneratedProductivity(hours_per_feature_default=32),
                setup_cost_items=[GeneratedLineItem(name="Original setup", amount_jpy=100000)],
                monthly_rc_items=[GeneratedLineItem(name="Original hosting", amount_jpy=50000)],
                generation_notes="Initial generation.",
                used_default_assumptions=[],
            )

    create = await client.post(
        "/estimates",
        json={
            "project_name": "Preserve Card",
            "client_name": "ACME",
            "locale": "en",
            "form_data": {"main_functional_needs": "Portal"},
        },
        headers=auth_headers,
    )
    estimate_id = create.json()["id"]
    combined = CombinedProvider()

    with patch(
        "app.rate_cards.generation.get_ai_provider",
        new=AsyncMock(return_value=combined),
    ), patch(
        "app.estimates.extraction.get_ai_provider",
        new=AsyncMock(return_value=combined),
    ):
        first = await client.post(f"/estimates/{estimate_id}/extract", headers=auth_headers)
        assert first.status_code == 202

    detail = await client.get(f"/estimates/{estimate_id}", headers=auth_headers)
    card_id = detail.json()["rate_card_id"]

    card = await client.get(f"/rate-cards/cards/{card_id}", headers=auth_headers)
    settings = card.json()["settings"]
    settings["setup_cost_items"] = [{"name": "Edited setup", "amount_jpy": 999999}]
    settings["monthly_rc_items"] = [{"name": "Edited hosting", "amount_jpy": 888888}]

    updated = await client.put(
        f"/rate-cards/cards/{card_id}",
        json={"settings": settings},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["is_locked"] is False

    with patch(
        "app.rate_cards.generation.get_ai_provider",
        new=AsyncMock(return_value=combined),
    ), patch(
        "app.estimates.extraction.get_ai_provider",
        new=AsyncMock(return_value=combined),
    ):
        second = await client.post(f"/estimates/{estimate_id}/extract", headers=auth_headers)
        assert second.status_code == 202

    card_after = await client.get(f"/rate-cards/cards/{card_id}", headers=auth_headers)
    after_settings = card_after.json()["settings"]
    assert after_settings["setup_cost_items"][0]["amount_jpy"] == 999999
    assert after_settings["monthly_rc_items"][0]["amount_jpy"] == 888888


@pytest.mark.asyncio
async def test_re_extract_after_export_with_edited_rate_card(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict[str, str],
    mock_ai_provider,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("EXTRACT_SYNC", "1")

    create = await client.post(
        "/estimates",
        json={
            "project_name": "Exported Re-extract",
            "client_name": "ACME",
            "locale": "en",
            "form_data": {"main_functional_needs": "Portal"},
        },
        headers=auth_headers,
    )
    estimate_id = create.json()["id"]

    with patch(
        "app.estimates.extraction.get_ai_provider",
        new=AsyncMock(return_value=mock_ai_provider),
    ):
        first = await client.post(f"/estimates/{estimate_id}/extract", headers=auth_headers)
        assert first.status_code == 202

    await client.post(f"/estimates/{estimate_id}/calculate", headers=auth_headers)
    estimate = await db_session.get(Estimate, uuid.UUID(estimate_id))
    assert estimate is not None
    estimate.status = EstimateStatus.EXPORTED.value
    await db_session.commit()

    detail = await client.get(f"/estimates/{estimate_id}", headers=auth_headers)
    card_id = detail.json()["rate_card_id"]
    assert detail.json()["status"] == "exported"

    card = await client.get(f"/rate-cards/cards/{card_id}", headers=auth_headers)
    settings = card.json()["settings"]
    settings["contingency_rate"] = 0.21
    updated = await client.put(
        f"/rate-cards/cards/{card_id}",
        json={"settings": settings},
        headers=auth_headers,
    )
    assert updated.status_code == 200

    with patch(
        "app.estimates.extraction.get_ai_provider",
        new=AsyncMock(return_value=mock_ai_provider),
    ):
        second = await client.post(f"/estimates/{estimate_id}/extract", headers=auth_headers)
        assert second.status_code == 202

    after = await client.get(f"/estimates/{estimate_id}", headers=auth_headers)
    assert after.json()["status"] == "review"
    card_after = await client.get(f"/rate-cards/cards/{card_id}", headers=auth_headers)
    assert card_after.json()["settings"]["contingency_rate"] == 0.21


@pytest.mark.asyncio
async def test_estimate_shows_rate_card_stale_after_card_edit(
    client: AsyncClient,
    auth_headers: dict[str, str],
    mock_ai_provider,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("EXTRACT_SYNC", "1")

    create = await client.post(
        "/estimates",
        json={
            "project_name": "Stale Notice",
            "client_name": "ACME",
            "locale": "en",
            "form_data": {"main_functional_needs": "Portal"},
        },
        headers=auth_headers,
    )
    estimate_id = create.json()["id"]

    with patch(
        "app.estimates.extraction.get_ai_provider",
        new=AsyncMock(return_value=mock_ai_provider),
    ):
        extract = await client.post(f"/estimates/{estimate_id}/extract", headers=auth_headers)
        assert extract.status_code == 202

    detail = await client.get(f"/estimates/{estimate_id}", headers=auth_headers)
    assert detail.json()["rate_card_stale"] is False
    card_id = detail.json()["rate_card_id"]

    card = await client.get(f"/rate-cards/cards/{card_id}", headers=auth_headers)
    settings = card.json()["settings"]
    settings["contingency_rate"] = 0.19
    updated = await client.put(
        f"/rate-cards/cards/{card_id}",
        json={"settings": settings},
        headers=auth_headers,
    )
    assert updated.status_code == 200

    stale = await client.get(f"/estimates/{estimate_id}", headers=auth_headers)
    assert stale.json()["rate_card_stale"] is True

    with patch(
        "app.estimates.extraction.get_ai_provider",
        new=AsyncMock(return_value=mock_ai_provider),
    ):
        re_extract = await client.post(f"/estimates/{estimate_id}/extract", headers=auth_headers)
        assert re_extract.status_code == 202

    fresh = await client.get(f"/estimates/{estimate_id}", headers=auth_headers)
    assert fresh.json()["rate_card_stale"] is False


@pytest.mark.asyncio
async def test_extraction_populates_feature_items(
    client: AsyncClient,
    auth_headers: dict[str, str],
    active_rate_card: RateCardVersion,
    mock_ai_provider,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("EXTRACT_SYNC", "1")

    create = await client.post(
        "/estimates",
        json={
            "project_name": "Extract Test",
            "client_name": "ACME",
            "locale": "en",
        },
        headers=auth_headers,
    )
    assert create.status_code == 201
    estimate_id = create.json()["id"]

    await client.patch(
        f"/estimates/{estimate_id}",
        json={"form_data": {"main_functional_needs": "User login and dashboard"}},
        headers=auth_headers,
    )
    await assign_rate_card(client, estimate_id, active_rate_card, auth_headers)

    with patch(
        "app.estimates.extraction.get_ai_provider",
        new=AsyncMock(return_value=mock_ai_provider),
    ):
        extract = await client.post(f"/estimates/{estimate_id}/extract", headers=auth_headers)
        assert extract.status_code == 202

    detail = await client.get(f"/estimates/{estimate_id}", headers=auth_headers)
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["status"] == "review"
    assert len(payload["feature_items"]) >= 1
    assert payload["extracted_data"]["functional_requirements"]
    assert payload["maintenance_assumptions"]["monthly_support_hours"] == 20

    audit = await client.get(f"/estimates/{estimate_id}/audit", headers=auth_headers)
    actions = [entry["action"] for entry in audit.json()]
    assert "extraction_started" in actions
    assert "extraction_completed" in actions


@pytest.mark.asyncio
async def test_stuck_extraction_status_recovers_to_draft(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    active_rate_card: RateCardVersion,
):
    create = await client.post(
        "/estimates",
        json={
            "project_name": "Stuck Test",
            "client_name": "ACME",
            "locale": "en",
        },
        headers=auth_headers,
    )
    estimate_id = create.json()["id"]
    await assign_rate_card(client, estimate_id, active_rate_card, auth_headers)

    estimate = await db_session.get(Estimate, uuid.UUID(estimate_id))
    assert estimate is not None
    estimate.status = EstimateStatus.EXTRACTING.value
    estimate.updated_at = datetime.utcnow() - timedelta(minutes=15)
    await db_session.commit()

    status = await client.get(f"/estimates/{estimate_id}/status", headers=auth_headers)
    assert status.status_code == 200
    body = status.json()
    assert body["status"] == "draft"
    assert body["extraction_error"]

    retry = await client.post(f"/estimates/{estimate_id}/extract", headers=auth_headers)
    assert retry.status_code == 202
    assert retry.json()["status"] == "accepted"


@pytest.mark.asyncio
async def test_extraction_status_during_extract(
    client: AsyncClient,
    auth_headers: dict[str, str],
    active_rate_card: RateCardVersion,
    mock_ai_provider,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("EXTRACT_SYNC", "0")

    create = await client.post(
        "/estimates",
        json={
            "project_name": "Status Test",
            "client_name": "ACME",
            "locale": "en",
        },
        headers=auth_headers,
    )
    estimate_id = create.json()["id"]
    await assign_rate_card(client, estimate_id, active_rate_card, auth_headers)

    hang = asyncio.Event()

    async def slow_run_extraction(*args, **kwargs):
        await hang.wait()

    with patch(
        "app.estimates.extraction.run_extraction",
        new=AsyncMock(side_effect=slow_run_extraction),
    ):
        extract = await client.post(f"/estimates/{estimate_id}/extract", headers=auth_headers)
        assert extract.status_code == 202

    status = await client.get(f"/estimates/{estimate_id}/status", headers=auth_headers)
    assert status.status_code == 200
    assert status.json()["status"] == "extracting"
    assert status.json()["extraction_progress"] is not None

    hang.set()


@pytest.mark.asyncio
async def test_update_feature_items_and_extracted_data(
    client: AsyncClient,
    auth_headers: dict[str, str],
    active_rate_card: RateCardVersion,
    mock_ai_provider,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("EXTRACT_SYNC", "1")

    create = await client.post(
        "/estimates",
        json={
            "project_name": "Edit Test",
            "client_name": "ACME",
            "locale": "en",
        },
        headers=auth_headers,
    )
    estimate_id = create.json()["id"]
    await assign_rate_card(client, estimate_id, active_rate_card, auth_headers)

    with patch(
        "app.estimates.extraction.get_ai_provider",
        new=AsyncMock(return_value=mock_ai_provider),
    ):
        await client.post(f"/estimates/{estimate_id}/extract", headers=auth_headers)

    detail = await client.get(f"/estimates/{estimate_id}", headers=auth_headers)
    feature_items = detail.json()["feature_items"]

    updated = await client.put(
        f"/estimates/{estimate_id}/feature-items",
        json={
            "items": [
                {
                    "id": feature_items[0]["id"],
                    "name": "Updated login",
                    "description": "Updated description",
                    "hours": 48,
                    "phase": "development",
                    "role": "developer",
                    "sort_order": 0,
                    "is_ai_generated": False,
                }
            ]
        },
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["feature_items"][0]["name"] == "Updated login"
    assert updated.json()["feature_items"][0]["hours"] == 48

    patched = await client.patch(
        f"/estimates/{estimate_id}/extracted-data",
        json={"functional_requirements": ["Updated requirement"]},
        headers=auth_headers,
    )
    assert patched.status_code == 200
    assert patched.json()["extracted_data"]["functional_requirements"] == ["Updated requirement"]


@pytest.mark.asyncio
async def test_extraction_retry_clears_partial_ai_output(
    client: AsyncClient,
    auth_headers: dict[str, str],
    active_rate_card: RateCardVersion,
    mock_ai_provider,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("EXTRACT_SYNC", "1")

    create = await client.post(
        "/estimates",
        json={
            "project_name": "Retry Clear Test",
            "client_name": "ACME",
            "locale": "en",
        },
        headers=auth_headers,
    )
    estimate_id = create.json()["id"]
    await assign_rate_card(client, estimate_id, active_rate_card, auth_headers)

    with patch(
        "app.estimates.extraction.get_ai_provider",
        new=AsyncMock(return_value=mock_ai_provider),
    ):
        await client.post(f"/estimates/{estimate_id}/extract", headers=auth_headers)

    detail = await client.get(f"/estimates/{estimate_id}", headers=auth_headers)
    assert detail.json()["status"] == "review"
    assert len(detail.json()["feature_items"]) >= 1

    class FailingProvider:
        async def extract_requirements(self, form_data, document_texts, locale, **kwargs):
            raise ValidationError.from_exception_data(
                "ExtractedRequirements",
                [{"type": "missing", "loc": ("feature_items",), "msg": "Field required", "input": {}}],
            )

    with patch(
        "app.estimates.extraction.get_ai_provider",
        new=AsyncMock(return_value=FailingProvider()),
    ):
        response = await client.post(f"/estimates/{estimate_id}/extract", headers=auth_headers)
        assert response.status_code == 202

    detail = await client.get(f"/estimates/{estimate_id}", headers=auth_headers)
    payload = detail.json()
    assert payload["status"] == "draft"
    assert payload["feature_items"] == []
    assert payload["extracted_data"] is None
    assert payload["maintenance_assumptions"] == {}

    status = await client.get(f"/estimates/{estimate_id}/status", headers=auth_headers)
    assert status.json()["extraction_error"]


@pytest.mark.asyncio
async def test_extraction_status_reports_background_failure(
    client: AsyncClient,
    auth_headers: dict[str, str],
    active_rate_card: RateCardVersion,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("EXTRACT_SYNC", "1")

    create = await client.post(
        "/estimates",
        json={
            "project_name": "Failure Test",
            "client_name": "ACME",
            "locale": "en",
        },
        headers=auth_headers,
    )
    estimate_id = create.json()["id"]
    await assign_rate_card(client, estimate_id, active_rate_card, auth_headers)

    class FailingProvider:
        async def extract_requirements(self, form_data, document_texts, locale, **kwargs):
            raise RuntimeError("Invalid API key")

    with patch(
        "app.estimates.extraction.get_ai_provider",
        new=AsyncMock(return_value=FailingProvider()),
    ):
        response = await client.post(f"/estimates/{estimate_id}/extract", headers=auth_headers)
        assert response.status_code == 202

    status = await client.get(f"/estimates/{estimate_id}/status", headers=auth_headers)
    assert status.status_code == 200
    payload = status.json()
    assert payload["status"] == "draft"
    assert payload["extraction_error"]
    assert "api key" in payload["extraction_error"].lower()
