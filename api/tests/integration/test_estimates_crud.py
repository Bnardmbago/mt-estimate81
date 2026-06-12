import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from app.ai.schemas import ExtractedRequirements, FeatureItemSuggestion, MaintenanceAssumptions
from app.models.rate_card import RateCardVersion


@pytest.fixture
def mock_ai_provider():
    class MockProvider:
        async def extract_requirements(self, form_data, document_texts, locale, **kwargs):
            return ExtractedRequirements(
                functional_requirements=["User login"],
                non_functional_requirements=["99.9% uptime"],
                user_roles=["Admin"],
                modules=["Auth"],
                external_systems=[],
                risks=[],
                gaps=[],
                confidence_notes="High confidence",
                feature_items=[
                    FeatureItemSuggestion(
                        name="User login",
                        description="OAuth login flow",
                        suggested_hours=40,
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
async def test_create_and_list_estimate(client: AsyncClient, auth_headers: dict[str, str]):
    create = await client.post(
        "/estimates",
        json={
            "project_name": "Test Project",
            "client_name": "ACME",
            "locale": "en",
        },
        headers=auth_headers,
    )
    assert create.status_code == 201
    estimate_id = create.json()["id"]

    get = await client.get(f"/estimates/{estimate_id}", headers=auth_headers)
    assert get.status_code == 200
    assert get.json()["project_name"] == "Test Project"
    assert get.json()["status"] == "draft"
    assert get.json()["feature_items"] == []
    assert get.json()["documents"] == []

    listing = await client.get("/estimates", headers=auth_headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["id"] == estimate_id


@pytest.mark.asyncio
async def test_update_estimate_and_audit(client: AsyncClient, auth_headers: dict[str, str]):
    create = await client.post(
        "/estimates",
        json={
            "project_name": "Original",
            "client_name": "ACME",
            "locale": "ja",
        },
        headers=auth_headers,
    )
    estimate_id = create.json()["id"]

    patch = await client.patch(
        f"/estimates/{estimate_id}",
        json={
            "project_name": "Updated Project",
            "form_data": {"main_functional_needs": "Login flow"},
        },
        headers=auth_headers,
    )
    assert patch.status_code == 200
    assert patch.json()["project_name"] == "Updated Project"
    assert patch.json()["form_data"]["main_functional_needs"] == "Login flow"

    audit = await client.get(f"/estimates/{estimate_id}/audit", headers=auth_headers)
    assert audit.status_code == 200
    entries = audit.json()
    assert len(entries) == 2
    assert entries[0]["action"] == "created"
    assert entries[1]["action"] == "updated"
    assert "project_name" in entries[1]["changes"]
    assert "form_data" in entries[1]["changes"]


@pytest.mark.asyncio
async def test_unauthenticated_create_rejected(client: AsyncClient):
    response = await client.post(
        "/estimates",
        json={
            "project_name": "Test Project",
            "client_name": "ACME",
            "locale": "en",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_nonexistent_estimate(client: AsyncClient, auth_headers: dict[str, str]):
    response = await client.get(
        "/estimates/00000000-0000-0000-0000-000000000099",
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_estimate(client: AsyncClient, auth_headers: dict[str, str]):
    create = await client.post(
        "/estimates",
        json={
            "project_name": "To Delete",
            "client_name": "ACME",
            "locale": "en",
        },
        headers=auth_headers,
    )
    estimate_id = create.json()["id"]

    delete = await client.delete(f"/estimates/{estimate_id}", headers=auth_headers)
    assert delete.status_code == 204

    get = await client.get(f"/estimates/{estimate_id}", headers=auth_headers)
    assert get.status_code == 404

    listing = await client.get("/estimates", headers=auth_headers)
    assert listing.status_code == 200
    assert all(item["id"] != estimate_id for item in listing.json())


@pytest.mark.asyncio
async def test_get_estimate_detail_with_feature_items_and_display_locale(
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
            "project_name": "Detail With Features",
            "client_name": "ACME",
            "locale": "en",
        },
        headers=auth_headers,
    )
    assert create.status_code == 201
    estimate_id = create.json()["id"]
    await assign_rate_card(client, estimate_id, active_rate_card, auth_headers)

    with patch(
        "app.estimates.extraction.get_ai_provider",
        new=AsyncMock(return_value=mock_ai_provider),
    ):
        extract = await client.post(
            f"/estimates/{estimate_id}/extract",
            headers={**auth_headers, "X-Content-Locale": "en"},
        )
        assert extract.status_code == 202

    headers = {
        **auth_headers,
        "X-Display-Locale": "en",
        "X-Content-Locale": "en",
    }
    get = await client.get(f"/estimates/{estimate_id}", headers=headers)
    assert get.status_code == 200
    payload = get.json()
    assert len(payload["feature_items"]) >= 1
    assert payload["feature_items"][0]["name"] == "User login"
    assert payload["status"] == "review"
