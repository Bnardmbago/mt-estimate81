import uuid
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.ai.schemas import GeneratedRoleRate, RateCardRolesSectionSuggestion
from app.rate_cards.ai_suggest import _build_estimate_context


def test_build_estimate_context_uses_feature_item_hours_field():
    estimate = SimpleNamespace(
        locale="en",
        project_name="Portal",
        client_name="ACME",
        status="review",
        form_data={},
        extracted_data={},
        maintenance_assumptions={},
        calculation_result=None,
        feature_items=[
            SimpleNamespace(
                name="User login",
                hours=40,
                phase="development",
                role="developer",
                description="OAuth login flow",
                sort_order=0,
            )
        ],
    )

    context = _build_estimate_context(estimate, "en")

    assert context["feature_items"][0]["hours"] == 40
    assert context["feature_items"][0]["name"] == "User login"


@pytest.fixture
def mock_section_ai_provider():
    class MockProvider:
        async def extract_requirements(self, *args, **kwargs):
            raise NotImplementedError

        async def generate_rate_card(self, **kwargs):
            raise NotImplementedError

        async def suggest_rate_card_section(self, **kwargs):
            return RateCardRolesSectionSuggestion(
                items=[GeneratedRoleRate(name="DevOps", hourly_rate_jpy=8500)],
                generation_notes="Added DevOps based on cloud integration scope.",
            )

    return MockProvider()


@pytest.mark.asyncio
async def test_suggest_rate_card_section_roles(
    client: AsyncClient,
    auth_headers: dict[str, str],
    mock_section_ai_provider,
):
    estimate = await client.post(
        "/estimates",
        json={
            "project_name": "Cloud Portal",
            "client_name": "ACME",
            "locale": "en",
        },
        headers=auth_headers,
    )
    estimate_id = estimate.json()["id"]

    card = await client.post(
        "/rate-cards/cards",
        json={
            "name": "AI Test Card",
            "activate": False,
            "development_approach": "traditional",
        },
        headers=auth_headers,
    )
    assert card.status_code == 201
    card_id = card.json()["id"]

    await client.patch(
        f"/estimates/{estimate_id}",
        json={"rate_card_id": card_id},
        headers=auth_headers,
    )

    with patch(
        "app.rate_cards.ai_suggest.get_ai_provider",
        return_value=mock_section_ai_provider,
    ):
        response = await client.post(
            f"/rate-cards/cards/{card_id}/ai/suggest",
            json={
                "estimate_id": estimate_id,
                "section": "roles",
                "prompt": "Add DevOps for AWS hosting",
                "locale": "en",
            },
            headers=auth_headers,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["section"] == "roles"
    assert len(payload["items"]) == 1
    assert payload["items"][0]["name"] == "DevOps"
    assert payload["estimate"]["project_name"] == "Cloud Portal"


@pytest.mark.asyncio
async def test_suggest_rate_card_section_free_form_without_estimate(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    captured: dict[str, object] = {}

    class MockProvider:
        async def extract_requirements(self, *args, **kwargs):
            raise NotImplementedError

        async def generate_rate_card(self, **kwargs):
            raise NotImplementedError

        async def suggest_rate_card_section(self, **kwargs):
            captured.update(kwargs)
            return RateCardRolesSectionSuggestion(
                items=[GeneratedRoleRate(name="DevOps", hourly_rate_jpy=8500)],
                generation_notes="Added DevOps based on prompt only.",
            )

    card = await client.post(
        "/rate-cards/cards",
        json={
            "name": "Free Form Card",
            "activate": False,
            "development_approach": "traditional",
        },
        headers=auth_headers,
    )
    assert card.status_code == 201
    card_id = card.json()["id"]

    with patch(
        "app.rate_cards.ai_suggest.get_ai_provider",
        return_value=MockProvider(),
    ):
        response = await client.post(
            f"/rate-cards/cards/{card_id}/ai/suggest",
            json={
                "estimate_id": None,
                "section": "roles",
                "prompt": "Add a DevOps role for cloud infrastructure",
                "locale": "en",
            },
            headers=auth_headers,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["section"] == "roles"
    assert len(payload["items"]) == 1
    assert payload["estimate"] is None
    assert captured["free_form"] is True
    assert captured["estimate_context"] == {}
    assert captured["document_texts"] == []


@pytest.mark.asyncio
async def test_suggest_rate_card_section_rejects_unlinked_estimate(
    client: AsyncClient,
    auth_headers: dict[str, str],
    mock_section_ai_provider,
):
    estimate = await client.post(
        "/estimates",
        json={
            "project_name": "Unlinked",
            "client_name": "ACME",
            "locale": "en",
        },
        headers=auth_headers,
    )
    estimate_id = estimate.json()["id"]

    card = await client.post(
        "/rate-cards/cards",
        json={
            "name": "Other Card",
            "activate": False,
            "development_approach": "traditional",
        },
        headers=auth_headers,
    )
    assert card.status_code == 201
    card_id = card.json()["id"]

    with patch(
        "app.rate_cards.ai_suggest.get_ai_provider",
        return_value=mock_section_ai_provider,
    ):
        response = await client.post(
            f"/rate-cards/cards/{card_id}/ai/suggest",
            json={
                "estimate_id": estimate_id,
                "section": "roles",
                "prompt": "Add DevOps",
            },
            headers=auth_headers,
        )

    assert response.status_code == 404
    assert response.json()["code"] == "ESTIMATE_NOT_LINKED"


@pytest.mark.asyncio
async def test_suggest_rate_card_section_rejects_empty_prompt(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    card = await client.post(
        "/rate-cards/cards",
        json={
            "name": "Prompt Card",
            "activate": False,
            "development_approach": "traditional",
        },
        headers=auth_headers,
    )
    assert card.status_code == 201
    card_id = card.json()["id"]

    response = await client.post(
        f"/rate-cards/cards/{card_id}/ai/suggest",
        json={
            "estimate_id": str(uuid.uuid4()),
            "section": "roles",
            "prompt": "",
        },
        headers=auth_headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_rate_card_estimates_includes_rate_card_id_assignment(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    estimate = await client.post(
        "/estimates",
        json={
            "project_name": "Assigned Only",
            "client_name": "ACME",
            "locale": "en",
        },
        headers=auth_headers,
    )
    estimate_id = estimate.json()["id"]

    card = await client.post(
        "/rate-cards/cards",
        json={
            "name": "Assigned Card",
            "activate": False,
            "development_approach": "traditional",
        },
        headers=auth_headers,
    )
    assert card.status_code == 201
    card_id = card.json()["id"]

    await client.patch(
        f"/estimates/{estimate_id}",
        json={"rate_card_id": card_id},
        headers=auth_headers,
    )

    response = await client.get(
        f"/rate-cards/cards/{card_id}/estimates",
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["estimate_id"] == estimate_id
    assert payload[0]["project_name"] == "Assigned Only"
