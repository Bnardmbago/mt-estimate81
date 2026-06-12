from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.ai.schemas import (
    GeneratedLineItem,
    GeneratedPhasePercentage,
    GeneratedProductivity,
    GeneratedRateCardSuggestion,
    GeneratedRoleRate,
)


@pytest.fixture
def mock_ai_provider_with_rate_card():
    class MockProvider:
        async def extract_requirements(self, form_data, document_texts, locale, **kwargs):
            raise NotImplementedError

        async def generate_rate_card(self, **kwargs):
            return GeneratedRateCardSuggestion(
                development_approach="ai_assisted",
                roles=[
                    GeneratedRoleRate(name="PM", hourly_rate_jpy=9000),
                    GeneratedRoleRate(name="developer", hourly_rate_jpy=7000),
                    GeneratedRoleRate(name="QA", hourly_rate_jpy=5500),
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
                    GeneratedLineItem(name="Infrastructure", amount_jpy=250000),
                ],
                monthly_rc_items=[
                    GeneratedLineItem(name="hosting", amount_jpy=60000),
                ],
                generation_notes="AI-assisted web project with moderate complexity.",
                used_default_assumptions=[],
            )

    return MockProvider()


@pytest.mark.asyncio
async def test_generate_rate_card_for_estimate(
    client: AsyncClient,
    auth_headers: dict[str, str],
    mock_ai_provider_with_rate_card,
):
    create = await client.post(
        "/estimates",
        json={
            "project_name": "Portal Revamp",
            "client_name": "ACME",
            "locale": "en",
            "form_data": {"delivery_model": "agile"},
        },
        headers=auth_headers,
    )
    estimate_id = create.json()["id"]

    with patch("app.rate_cards.generation.get_ai_provider", return_value=mock_ai_provider_with_rate_card):
        response = await client.post(
            f"/estimates/{estimate_id}/rate-card/generate",
            headers=auth_headers,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Portal Revamp"
    assert payload["settings"]["development_approach"] == "ai_assisted"
    assert payload["settings"]["productivity"]["hours_per_feature_default"] == 32
    assert "generation_notes" in payload


@pytest.mark.asyncio
async def test_create_generated_rate_card_assigns_estimate(
    client: AsyncClient,
    auth_headers: dict[str, str],
    mock_ai_provider_with_rate_card,
):
    create = await client.post(
        "/estimates",
        json={
            "project_name": "Mobile App",
            "client_name": "ACME",
            "locale": "en",
        },
        headers=auth_headers,
    )
    estimate_id = create.json()["id"]

    with patch("app.rate_cards.generation.get_ai_provider", return_value=mock_ai_provider_with_rate_card):
        generated = await client.post(
            f"/estimates/{estimate_id}/rate-card/generate",
            headers=auth_headers,
        )

    settings = generated.json()["settings"]
    created = await client.post(
        f"/estimates/{estimate_id}/rate-card",
        json={"name": "Mobile App", "settings": settings, "activate": True},
        headers=auth_headers,
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["rate_card_id"] is not None
    assert payload["rate_card_name"] == "Mobile App"

    extract = await client.post(f"/estimates/{estimate_id}/extract", headers=auth_headers)
    assert extract.status_code == 202


@pytest.mark.asyncio
async def test_generate_rate_card_falls_back_to_defaults_on_ai_failure(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    create = await client.post(
        "/estimates",
        json={
            "project_name": "Fallback Project",
            "client_name": "ACME",
            "locale": "en",
        },
        headers=auth_headers,
    )
    estimate_id = create.json()["id"]

    class FailingProvider:
        async def generate_rate_card(self, **kwargs):
            raise RuntimeError("AI unavailable")

    with patch("app.rate_cards.generation.get_ai_provider", return_value=FailingProvider()):
        response = await client.post(
            f"/estimates/{estimate_id}/rate-card/generate",
            headers=auth_headers,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["used_defaults"] is True
    assert payload["settings"]["development_approach"] == "traditional"
    assert "roles" in payload["settings"]
