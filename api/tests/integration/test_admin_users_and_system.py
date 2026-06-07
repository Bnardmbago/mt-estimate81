import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.system import get_hermes_client
from app.auth.service import create_access_token, hash_password, verify_password
from app.main import app
from app.models.estimate import Estimate, EstimateStatus
from app.models.user import User


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="admin@example.com",
        password_hash=hash_password("adminpass"),
        display_name="Admin",
        is_admin=True,
        preferred_locale="en",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def admin_headers(admin_user: User) -> dict[str, str]:
    token = create_access_token({"sub": str(admin_user.id), "is_admin": admin_user.is_admin})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_list_users_requires_admin(client: AsyncClient, auth_headers: dict[str, str]):
    response = await client.get("/admin/users", headers=auth_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_users(client: AsyncClient, admin_headers: dict[str, str], admin_user: User):
    response = await client.get("/admin/users", headers=admin_headers)
    assert response.status_code == 200
    users = response.json()
    assert len(users) >= 1
    assert any(user["email"] == admin_user.email for user in users)


@pytest.mark.asyncio
async def test_create_user(client: AsyncClient, admin_headers: dict[str, str]):
    response = await client.post(
        "/admin/users",
        headers=admin_headers,
        json={
            "email": "newuser@example.com",
            "password": "password123",
            "display_name": "New User",
            "preferred_locale": "ja",
            "is_admin": False,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["display_name"] == "New User"
    assert data["is_admin"] is False
    assert data["preferred_locale"] == "ja"


@pytest.mark.asyncio
async def test_create_duplicate_user(client: AsyncClient, admin_headers: dict[str, str], admin_user: User):
    response = await client.post(
        "/admin/users",
        headers=admin_headers,
        json={
            "email": admin_user.email,
            "password": "password123",
            "display_name": "Duplicate",
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_update_user(client: AsyncClient, admin_headers: dict[str, str]):
    user = client.test_user  # type: ignore[attr-defined]
    response = await client.patch(
        f"/admin/users/{user.id}",
        headers=admin_headers,
        json={"is_admin": True, "preferred_locale": "ja"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_admin"] is True
    assert data["preferred_locale"] == "ja"


@pytest.mark.asyncio
async def test_reset_password(
    client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
):
    user = client.test_user  # type: ignore[attr-defined]
    response = await client.put(
        f"/admin/users/{user.id}/reset-password",
        headers=admin_headers,
        json={"password": "newpassword99"},
    )
    assert response.status_code == 200

    result = await db_session.execute(select(User).where(User.id == user.id))
    updated = result.scalar_one()
    assert verify_password("newpassword99", updated.password_hash)


@pytest.mark.asyncio
async def test_system_health(
    client: AsyncClient,
    admin_headers: dict[str, str],
    tmp_path,
):
    mock_hermes = AsyncMock()
    mock_hermes.ping = AsyncMock(return_value="ok")

    from app.storage.local import LocalStorageBackend

    storage = LocalStorageBackend(base_path=str(tmp_path))
    await storage.save("test/file.txt", b"hello")

    app.dependency_overrides[get_hermes_client] = lambda: mock_hermes
    with patch("app.admin.system.get_storage_backend", return_value=storage):
        response = await client.get("/admin/system/health", headers=admin_headers)
    app.dependency_overrides.pop(get_hermes_client, None)

    assert response.status_code == 200
    data = response.json()
    assert data["database"] == "ok"
    assert data["hermes"] == "ok"
    assert data["ai_provider"] == "openai"
    assert data["ai_model"] == "gpt-4o"
    assert data["stuck_extractions"] == 0
    assert data["storage_usage_bytes"] == 5
    assert data["app_version"] == "0.1.0"


@pytest.mark.asyncio
async def test_stuck_extractions_count(
    client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
    admin_user: User,
    tmp_path,
):
    stuck_estimate = Estimate(
        project_name="Stuck",
        client_name="Client",
        status=EstimateStatus.EXTRACTING.value,
        created_by=admin_user.id,
        updated_at=datetime.utcnow() - timedelta(minutes=15),
    )
    fresh_estimate = Estimate(
        project_name="Fresh",
        client_name="Client",
        status=EstimateStatus.EXTRACTING.value,
        created_by=admin_user.id,
        updated_at=datetime.utcnow(),
    )
    db_session.add(stuck_estimate)
    db_session.add(fresh_estimate)
    await db_session.commit()

    mock_hermes = AsyncMock()
    mock_hermes.ping = AsyncMock(return_value="unreachable")

    from app.storage.local import LocalStorageBackend

    app.dependency_overrides[get_hermes_client] = lambda: mock_hermes
    with patch(
        "app.admin.system.get_storage_backend",
        return_value=LocalStorageBackend(base_path=str(tmp_path)),
    ):
        response = await client.get("/admin/system/health", headers=admin_headers)
    app.dependency_overrides.pop(get_hermes_client, None)

    assert response.status_code == 200
    assert response.json()["stuck_extractions"] == 1


@pytest.mark.asyncio
async def test_system_health_requires_admin(client: AsyncClient, auth_headers: dict[str, str]):
    response = await client.get("/admin/system/health", headers=auth_headers)
    assert response.status_code == 403
