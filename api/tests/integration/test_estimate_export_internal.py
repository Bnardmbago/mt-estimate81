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
async def test_internal_export_without_calculation_returns_422(
    db_session: AsyncSession,
    client: AsyncClient,
    admin_headers: dict[str, str],
):
    user = client.test_user  # type: ignore[attr-defined]
    estimate = Estimate(
        project_name="Missing Calculation",
        client_name="Stakeholder Co",
        locale="en",
        status=EstimateStatus.CALCULATED.value,
        created_by=user.id,
        form_data={},
        extracted_data={},
        calculation_result=None,
    )
    db_session.add(estimate)
    await db_session.commit()
    await db_session.refresh(estimate)

    response = await client.post(
        f"/estimates/{estimate.id}/export",
        headers=admin_headers,
        json={"format": "pdf_internal", "locale": "en"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "CALCULATION_REQUIRED"


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


@pytest.mark.asyncio
async def test_default_list_excludes_internal_exports(
    client: AsyncClient,
    auth_headers: dict[str, str],
    admin_headers: dict[str, str],
    calculated_estimate_id: str,
):
    client_export = await client.post(
        f"/estimates/{calculated_estimate_id}/export",
        headers=auth_headers,
        json={"format": "md", "locale": "en"},
    )
    assert client_export.status_code == 201, client_export.text

    internal_export = await client.post(
        f"/estimates/{calculated_estimate_id}/export",
        headers=admin_headers,
        json={"format": "pdf_internal", "locale": "en"},
    )
    assert internal_export.status_code == 201, internal_export.text

    listed = await client.get(
        f"/estimates/{calculated_estimate_id}/exports",
        headers=auth_headers,
    )
    assert listed.status_code == 200
    formats = [row["format"] for row in listed.json()]
    assert "md" in formats
    assert "pdf_internal" not in formats


@pytest.mark.asyncio
async def test_list_audience_internal_requires_admin(
    client: AsyncClient,
    auth_headers: dict[str, str],
    calculated_estimate_id: str,
):
    r = await client.get(
        f"/estimates/{calculated_estimate_id}/exports?audience=internal",
        headers=auth_headers,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_list_audience_internal_returns_only_internal(
    client: AsyncClient,
    auth_headers: dict[str, str],
    admin_headers: dict[str, str],
    calculated_estimate_id: str,
):
    client_export = await client.post(
        f"/estimates/{calculated_estimate_id}/export",
        headers=auth_headers,
        json={"format": "md", "locale": "en"},
    )
    assert client_export.status_code == 201, client_export.text

    internal_export = await client.post(
        f"/estimates/{calculated_estimate_id}/export",
        headers=admin_headers,
        json={"format": "pdf_internal", "locale": "en"},
    )
    assert internal_export.status_code == 201, internal_export.text

    listed = await client.get(
        f"/estimates/{calculated_estimate_id}/exports?audience=internal",
        headers=admin_headers,
    )
    assert listed.status_code == 200
    formats = [row["format"] for row in listed.json()]
    assert formats == ["pdf_internal"]


@pytest.mark.asyncio
async def test_non_admin_cannot_download_internal_export_owned_by_own_estimate(
    client: AsyncClient,
    auth_headers: dict[str, str],
    admin_headers: dict[str, str],
    calculated_estimate_id: str,
):
    created = await client.post(
        f"/estimates/{calculated_estimate_id}/export",
        headers=admin_headers,
        json={"format": "pdf_internal", "locale": "en"},
    )
    assert created.status_code == 201, created.text
    export_id = created.json()["id"]

    r = await client.get(f"/exports/{export_id}/download", headers=auth_headers)
    assert r.status_code == 403
    assert r.json()["code"] == "INTERNAL_EXPORT_ADMIN_REQUIRED"


@pytest.mark.asyncio
async def test_non_admin_cannot_delete_internal_export_owned_by_own_estimate(
    client: AsyncClient,
    auth_headers: dict[str, str],
    admin_headers: dict[str, str],
    calculated_estimate_id: str,
):
    created = await client.post(
        f"/estimates/{calculated_estimate_id}/export",
        headers=admin_headers,
        json={"format": "pdf_internal", "locale": "en"},
    )
    assert created.status_code == 201, created.text
    export_id = created.json()["id"]

    r = await client.delete(f"/exports/{export_id}", headers=auth_headers)
    assert r.status_code == 403
    assert r.json()["code"] == "INTERNAL_EXPORT_ADMIN_REQUIRED"


@pytest.mark.asyncio
async def test_non_admin_cannot_email_internal_export(
    client: AsyncClient,
    auth_headers: dict[str, str],
    admin_headers: dict[str, str],
    calculated_estimate_id: str,
):
    created = await client.post(
        f"/estimates/{calculated_estimate_id}/export",
        headers=admin_headers,
        json={"format": "pdf_internal", "locale": "en"},
    )
    assert created.status_code == 201, created.text
    export_id = created.json()["id"]

    r = await client.post(
        f"/estimates/{calculated_estimate_id}/exports/email",
        headers=auth_headers,
        json={"to_email": "client@example.com", "export_ids": [export_id]},
    )
    assert r.status_code == 403
    assert r.json()["code"] == "INTERNAL_EXPORT_ADMIN_REQUIRED"
