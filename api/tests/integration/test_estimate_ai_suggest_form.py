from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import EstimateFormFieldsSuggestion
from app.estimates.form_fields import normalize_suggested_form_data


def test_normalize_suggested_form_data_validates_select_values():
    raw = {
        "nature_of_work": "New build",
        "data_complexity": "MODERATE",
        "ui_complexity": "invalid",
        "development_location": "Japan",
        "unknown_field": "ignored",
    }
    normalized = normalize_suggested_form_data(raw)
    assert normalized["nature_of_work"] == "New build"
    assert normalized["data_complexity"] == "moderate"
    assert normalized["ui_complexity"] == ""
    assert normalized["development_location"] == "japan"
    assert "unknown_field" not in normalized


@pytest.fixture
def mock_form_ai_provider():
    class MockProvider:
        async def extract_requirements(self, *args, **kwargs):
            raise NotImplementedError

        async def generate_rate_card(self, **kwargs):
            raise NotImplementedError

        async def suggest_rate_card_section(self, **kwargs):
            raise NotImplementedError

        async def suggest_estimate_form_fields(self, **kwargs):
            return EstimateFormFieldsSuggestion(
                form_data={
                    "desired_system": "Should be stripped",
                    "nature_of_work": "New web application development",
                    "scope_boundaries": "In scope: user portal. Out of scope: mobile apps.",
                    "business_domain": "Retail",
                    "non_functional_needs": "99.9% availability, SSO",
                    "integrations": "ERP and payment gateway",
                    "data_complexity": "moderate",
                    "ui_complexity": "medium",
                    "technology_preferences": "React, Node.js",
                    "development_approach": "Agile",
                    "rules_and_standards": "PCI-DSS alignment",
                    "team_and_resources": "5-person blended team",
                    "development_location": "hybrid",
                    "maintenance_support": "12-month warranty support",
                    "risks_unknowns": "ERP API documentation incomplete",
                },
                generation_notes="Assumed hybrid Japan/offshore delivery.",
            )

    return MockProvider()


@pytest.mark.asyncio
async def test_suggest_estimate_form_happy_path(
    client: AsyncClient,
    auth_headers: dict[str, str],
    mock_form_ai_provider,
):
    estimate = await client.post(
        "/estimates",
        json={
            "project_name": "Customer Portal",
            "client_name": "ACME",
            "locale": "en",
        },
        headers=auth_headers,
    )
    assert estimate.status_code == 201
    estimate_id = estimate.json()["id"]

    with patch(
        "app.estimates.ai_suggest_form.get_ai_provider",
        return_value=mock_form_ai_provider,
    ):
        response = await client.post(
            f"/estimates/{estimate_id}/ai/suggest-form",
            json={
                "prompt": "E-commerce customer portal with SSO and ERP integration",
                "locale": "en",
            },
            headers=auth_headers,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["form_data"]["nature_of_work"] == "New web application development"
    assert payload["form_data"]["data_complexity"] == "moderate"
    assert "desired_system" not in payload["form_data"]
    assert "hybrid" in payload["generation_notes"]


@pytest.mark.asyncio
async def test_suggest_estimate_form_rejects_empty_prompt(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    estimate = await client.post(
        "/estimates",
        json={
            "project_name": "Empty Prompt",
            "client_name": "ACME",
            "locale": "en",
        },
        headers=auth_headers,
    )
    estimate_id = estimate.json()["id"]

    response = await client.post(
        f"/estimates/{estimate_id}/ai/suggest-form",
        json={"prompt": "   "},
        headers=auth_headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_suggest_estimate_form_rejects_non_draft_status(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    mock_form_ai_provider,
):
    from app.models.estimate import Estimate, EstimateStatus

    user = client.test_user  # type: ignore[attr-defined]
    estimate = Estimate(
        project_name="Review Estimate",
        client_name="ACME",
        locale="en",
        status=EstimateStatus.REVIEW,
        created_by=user.id,
        form_data={},
        maintenance_assumptions={"monthly_support_hours": 0, "support_role": "developer"},
    )
    db_session.add(estimate)
    await db_session.commit()
    await db_session.refresh(estimate)
    estimate_id = estimate.id

    with patch(
        "app.estimates.ai_suggest_form.get_ai_provider",
        return_value=mock_form_ai_provider,
    ):
        response = await client.post(
            f"/estimates/{estimate_id}/ai/suggest-form",
            json={"prompt": "Suggest fields"},
            headers=auth_headers,
        )

    assert response.status_code == 400
    detail = response.json()
    assert detail.get("code") == "INVALID_STATUS" or detail.get("detail", {}).get("code") == "INVALID_STATUS"


@pytest.mark.asyncio
async def test_suggest_estimate_form_access_denied(
    client: AsyncClient,
    auth_headers: dict[str, str],
    other_headers: dict[str, str],
    mock_form_ai_provider,
):
    estimate = await client.post(
        "/estimates",
        json={
            "project_name": "Private Estimate",
            "client_name": "ACME",
            "locale": "en",
        },
        headers=auth_headers,
    )
    estimate_id = estimate.json()["id"]

    with patch(
        "app.estimates.ai_suggest_form.get_ai_provider",
        return_value=mock_form_ai_provider,
    ):
        response = await client.post(
            f"/estimates/{estimate_id}/ai/suggest-form",
            json={"prompt": "Suggest fields"},
            headers=other_headers,
        )

    assert response.status_code == 403
    assert response.json()["code"] == "ESTIMATE_ACCESS_DENIED"
