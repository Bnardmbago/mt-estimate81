from unittest.mock import patch

import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from app.ai.schemas import ExtractedRequirements, FeatureItemSuggestion, MaintenanceAssumptions


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


@pytest.mark.asyncio
async def test_extraction_populates_feature_items(
    client: AsyncClient,
    auth_headers: dict[str, str],
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

    with patch("app.estimates.extraction.get_ai_provider", return_value=mock_ai_provider):
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
async def test_extraction_status_during_extract(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
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

    status = await client.get(f"/estimates/{estimate_id}/status", headers=auth_headers)
    assert status.status_code == 200
    assert status.json()["status"] == "draft"
    assert status.json()["extraction_progress"] is None


@pytest.mark.asyncio
async def test_update_feature_items_and_extracted_data(
    client: AsyncClient,
    auth_headers: dict[str, str],
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

    with patch("app.estimates.extraction.get_ai_provider", return_value=mock_ai_provider):
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

    with patch("app.estimates.extraction.get_ai_provider", return_value=mock_ai_provider):
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

    with patch("app.estimates.extraction.get_ai_provider", return_value=FailingProvider()):
        response = await client.post(f"/estimates/{estimate_id}/extract", headers=auth_headers)
        assert response.status_code == 502
        assert response.json()["code"] == "AI_INVALID_JSON"

    detail = await client.get(f"/estimates/{estimate_id}", headers=auth_headers)
    payload = detail.json()
    assert payload["status"] == "draft"
    assert payload["feature_items"] == []
    assert payload["extracted_data"] is None
    assert payload["maintenance_assumptions"] == {}
