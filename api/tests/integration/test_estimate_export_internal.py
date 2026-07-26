import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.estimate import Estimate, EstimateStatus


@pytest.fixture
async def calculated_estimate_id(
    db_session: AsyncSession,
    client: AsyncClient,
) -> str:
    user = client.test_user  # type: ignore[attr-defined]
    estimate = Estimate(
        project_name="Internal Export Source",
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
    return str(estimate.id)


@pytest.mark.asyncio
async def test_non_admin_cannot_create_pdf_internal(
    client: AsyncClient,
    auth_headers: dict[str, str],
    calculated_estimate_id: str,
):
    r = await client.post(
        f"/estimates/{calculated_estimate_id}/export",
        headers=auth_headers,
        json={"format": "pdf_internal", "locale": "en"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_create_pdf_internal(
    client: AsyncClient,
    admin_headers: dict[str, str],
    calculated_estimate_id: str,
):
    r = await client.post(
        f"/estimates/{calculated_estimate_id}/export",
        headers=admin_headers,
        json={"format": "pdf_internal", "locale": "en"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["format"] == "pdf_internal"


@pytest.mark.asyncio
async def test_admin_can_create_all_internal_formats(
    client: AsyncClient,
    admin_headers: dict[str, str],
    calculated_estimate_id: str,
):
    for export_format in ("md_internal", "docx_internal", "xlsx_internal"):
        r = await client.post(
            f"/estimates/{calculated_estimate_id}/export",
            headers=admin_headers,
            json={"format": export_format, "locale": "en"},
        )
        assert r.status_code == 201, r.text
        assert r.json()["format"] == export_format


@pytest.mark.asyncio
async def test_admin_download_internal_export_has_internal_suffix(
    client: AsyncClient,
    admin_headers: dict[str, str],
    calculated_estimate_id: str,
):
    created = await client.post(
        f"/estimates/{calculated_estimate_id}/export",
        headers=admin_headers,
        json={"format": "docx_internal", "locale": "en"},
    )
    assert created.status_code == 201, created.text
    export_id = created.json()["id"]

    downloaded = await client.get(
        f"/exports/{export_id}/download",
        headers=admin_headers,
    )
    assert downloaded.status_code == 200
    disposition = downloaded.headers["content-disposition"]
    assert "-internal.docx" in disposition
