import pytest
from httpx import AsyncClient


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
