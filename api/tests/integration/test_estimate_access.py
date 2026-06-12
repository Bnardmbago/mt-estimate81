import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.estimate import Estimate, EstimateStatus, Export


async def _create_estimate(client: AsyncClient, headers: dict[str, str], project_name: str) -> str:
    response = await client.post(
        "/estimates",
        json={
            "project_name": project_name,
            "client_name": "ACME",
            "locale": "en",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.asyncio
async def test_owner_lists_only_own_estimates(
    client: AsyncClient,
    auth_headers: dict[str, str],
    other_headers: dict[str, str],
):
    owner_estimate_id = await _create_estimate(client, auth_headers, "Owner Project")
    other_estimate_id = await _create_estimate(client, other_headers, "Other Project")

    response = await client.get("/estimates", headers=auth_headers)
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert owner_estimate_id in ids
    assert other_estimate_id not in ids


@pytest.mark.asyncio
async def test_other_user_does_not_see_owner_estimate_in_list(
    client: AsyncClient,
    auth_headers: dict[str, str],
    other_headers: dict[str, str],
):
    owner_estimate_id = await _create_estimate(client, auth_headers, "Owner Only")

    response = await client.get("/estimates", headers=other_headers)
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert owner_estimate_id not in ids


@pytest.mark.asyncio
async def test_admin_lists_all_estimates(
    client: AsyncClient,
    auth_headers: dict[str, str],
    other_headers: dict[str, str],
    admin_headers: dict[str, str],
):
    owner_estimate_id = await _create_estimate(client, auth_headers, "Owner Project")
    other_estimate_id = await _create_estimate(client, other_headers, "Other Project")

    response = await client.get("/estimates", headers=admin_headers)
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert owner_estimate_id in ids
    assert other_estimate_id in ids


@pytest.mark.asyncio
async def test_owner_can_get_patch_and_delete_own_estimate(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    estimate_id = await _create_estimate(client, auth_headers, "Owned")

    get_response = await client.get(f"/estimates/{estimate_id}", headers=auth_headers)
    assert get_response.status_code == 200

    patch_response = await client.patch(
        f"/estimates/{estimate_id}",
        json={"project_name": "Updated Owned"},
        headers=auth_headers,
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["project_name"] == "Updated Owned"

    delete_response = await client.delete(f"/estimates/{estimate_id}", headers=auth_headers)
    assert delete_response.status_code == 204


@pytest.mark.asyncio
async def test_other_user_cannot_get_owner_estimate(
    client: AsyncClient,
    auth_headers: dict[str, str],
    other_headers: dict[str, str],
):
    estimate_id = await _create_estimate(client, auth_headers, "Private")

    response = await client.get(f"/estimates/{estimate_id}", headers=other_headers)
    assert response.status_code == 403
    assert response.json()["code"] == "ESTIMATE_ACCESS_DENIED"


@pytest.mark.asyncio
async def test_other_user_cannot_delete_owner_estimate(
    client: AsyncClient,
    auth_headers: dict[str, str],
    other_headers: dict[str, str],
):
    estimate_id = await _create_estimate(client, auth_headers, "Protected")

    response = await client.delete(f"/estimates/{estimate_id}", headers=other_headers)
    assert response.status_code == 403
    assert response.json()["code"] == "ESTIMATE_ACCESS_DENIED"

    owner_get = await client.get(f"/estimates/{estimate_id}", headers=auth_headers)
    assert owner_get.status_code == 200


@pytest.mark.asyncio
async def test_admin_can_get_any_estimate(
    client: AsyncClient,
    auth_headers: dict[str, str],
    admin_headers: dict[str, str],
):
    estimate_id = await _create_estimate(client, auth_headers, "Admin Visible")

    response = await client.get(f"/estimates/{estimate_id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["project_name"] == "Admin Visible"


@pytest.mark.asyncio
async def test_other_user_cannot_export_or_download_owner_export(
    client: AsyncClient,
    auth_headers: dict[str, str],
    other_headers: dict[str, str],
    db_session: AsyncSession,
):
    estimate_id = await _create_estimate(client, auth_headers, "Export Protected")
    owner = client.test_user  # type: ignore[attr-defined]

    estimate = await db_session.get(Estimate, uuid.UUID(estimate_id))
    assert estimate is not None
    estimate.status = EstimateStatus.CALCULATED.value
    estimate.calculation_result = {
        "total_effort_hours": 40,
        "total_effort_days": 5,
        "nrc": {"total_jpy": 100000},
        "rc": {"monthly_total_jpy": 10000},
    }
    export_id = uuid.uuid4()
    db_session.add(
        Export(
            id=export_id,
            estimate_id=estimate.id,
            format="md",
            storage_path=f"exports/{estimate_id}/{export_id}.md",
            locale="en",
            generated_by=owner.id,
        )
    )
    await db_session.commit()

    export_response = await client.post(
        f"/estimates/{estimate_id}/export",
        json={"format": "md", "locale": "en"},
        headers=other_headers,
    )
    assert export_response.status_code == 403

    list_response = await client.get(
        f"/estimates/{estimate_id}/exports",
        headers=other_headers,
    )
    assert list_response.status_code == 403

    download_response = await client.get(
        f"/exports/{export_id}/download",
        headers=other_headers,
    )
    assert download_response.status_code == 403
