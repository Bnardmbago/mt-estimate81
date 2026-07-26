import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.estimate import Estimate, EstimateStatus


@pytest.fixture
async def calculated_estimate(
    db_session: AsyncSession,
    client: AsyncClient,
) -> Estimate:
    user = client.test_user  # type: ignore[attr-defined]
    estimate = Estimate(
        project_name="Internal Dossier Source",
        client_name="Stakeholder Co",
        locale="en",
        status=EstimateStatus.CALCULATED.value,
        created_by=user.id,
        form_data={},
        extracted_data={},
        calculation_result={
            "total_effort_hours": 120,
            "total_effort_days": 15,
            "first_year_total_jpy": 5_000_000,
            "nrc": {"total_jpy": 4_000_000},
            "rc": {"monthly_total_jpy": 80_000, "annual_total_jpy": 960_000},
            "role_breakdown": [],
            "phase_breakdown": [],
        },
    )
    db_session.add(estimate)
    await db_session.commit()
    await db_session.refresh(estimate)
    return estimate


@pytest.mark.asyncio
async def test_internal_dossier_forbidden_for_non_admin(
    client: AsyncClient,
    auth_headers: dict[str, str],
    calculated_estimate: Estimate,
):
    response = await client.get(
        f"/estimates/{calculated_estimate.id}/internal-dossier",
        headers=auth_headers,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_internal_dossier_ok_for_admin(
    client: AsyncClient,
    admin_headers: dict[str, str],
    calculated_estimate: Estimate,
):
    response = await client.get(
        f"/estimates/{calculated_estimate.id}/internal-dossier",
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["estimate_id"] == str(calculated_estimate.id)
    assert data["report"]
    assert "rate_card" in data
    assert "proposals" in data
