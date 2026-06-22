import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.ai_settings import get_hermes_client as get_ai_settings_hermes_client
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
            "company_name": "ACME Corp",
            "preferred_locale": "ja",
            "preferred_currency": "USD",
            "is_admin": False,
            "is_active": True,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["display_name"] == "New User"
    assert data["company_name"] == "ACME Corp"
    assert data["is_admin"] is False
    assert data["is_active"] is True
    assert data["preferred_locale"] == "ja"
    assert data["preferred_currency"] == "USD"


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
        json={
            "is_admin": True,
            "preferred_locale": "ja",
            "preferred_currency": "PHP",
            "display_name": "Updated Name",
            "company_name": "Updated Co",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_admin"] is True
    assert data["preferred_locale"] == "ja"
    assert data["preferred_currency"] == "PHP"
    assert data["display_name"] == "Updated Name"
    assert data["company_name"] == "Updated Co"


@pytest.mark.asyncio
async def test_disable_user_blocks_login(
    client: AsyncClient,
    admin_headers: dict[str, str],
):
    create = await client.post(
        "/admin/users",
        headers=admin_headers,
        json={
            "email": "disabled@example.com",
            "password": "password123",
            "display_name": "Disabled User",
            "is_active": True,
        },
    )
    user_id = create.json()["id"]

    disable = await client.patch(
        f"/admin/users/{user_id}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert disable.status_code == 200

    login = await client.post(
        "/auth/login",
        json={"email": "disabled@example.com", "password": "password123"},
    )
    assert login.status_code == 403
    assert login.json()["code"] == "USER_DISABLED"


@pytest.mark.asyncio
async def test_delete_user(client: AsyncClient, admin_headers: dict[str, str]):
    create = await client.post(
        "/admin/users",
        headers=admin_headers,
        json={
            "email": "delete-me@example.com",
            "password": "password123",
            "display_name": "Delete Me",
        },
    )
    user_id = create.json()["id"]

    delete = await client.delete(f"/admin/users/{user_id}", headers=admin_headers)
    assert delete.status_code == 204

    get = await client.get("/admin/users", headers=admin_headers)
    assert all(user["id"] != user_id for user in get.json())


@pytest.mark.asyncio
async def test_get_current_user_profile(client: AsyncClient, admin_headers: dict[str, str], admin_user: User):
    response = await client.get("/auth/me", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == admin_user.email
    assert data["is_admin"] is True
    assert data["preferred_currency"] == "JPY"
    assert "company_name" in data


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
    assert "openai_api_key_configured" in data
    assert "anthropic_api_key_configured" in data
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


@pytest.mark.asyncio
async def test_get_ai_settings(client: AsyncClient, admin_headers: dict[str, str]):
    mock_hermes = AsyncMock()
    mock_hermes.ping = AsyncMock(return_value="ok")

    app.dependency_overrides[get_ai_settings_hermes_client] = lambda: mock_hermes
    response = await client.get("/admin/ai-settings", headers=admin_headers)
    app.dependency_overrides.pop(get_ai_settings_hermes_client, None)

    assert response.status_code == 200
    data = response.json()
    assert data["ai_provider"] == "openai"
    assert data["ai_model"] == "gpt-4o"
    assert data["openai_models"]
    assert data["anthropic_models"]
    assert data["hermes"] == "ok"


@pytest.mark.asyncio
async def test_update_ai_settings(client: AsyncClient, admin_headers: dict[str, str]):
    mock_hermes = AsyncMock()
    mock_hermes.ping = AsyncMock(return_value="ok")

    app.dependency_overrides[get_ai_settings_hermes_client] = lambda: mock_hermes
    response = await client.patch(
        "/admin/ai-settings",
        headers=admin_headers,
        json={
            "ai_provider": "anthropic",
            "ai_model": "claude-sonnet-4-6",
            "anthropic_api_key": "sk-ant-test-key",
        },
    )
    app.dependency_overrides.pop(get_ai_settings_hermes_client, None)

    assert response.status_code == 200
    data = response.json()
    assert data["ai_provider"] == "anthropic"
    assert data["ai_model"] == "claude-sonnet-4-6"
    assert data["anthropic_api_key_configured"] is True
    assert data["anthropic_api_key_hint"] == "...-key"


@pytest.mark.asyncio
async def test_ai_settings_requires_admin(client: AsyncClient, auth_headers: dict[str, str]):
    response = await client.get("/admin/ai-settings", headers=auth_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_ai_connection_test_success(client: AsyncClient, admin_headers: dict[str, str]):
    with patch(
        "app.admin.ai_settings.verify_openai_connection",
        new=AsyncMock(return_value=(True, "Connection successful")),
    ):
        response = await client.post(
            "/admin/ai-settings/test-connection",
            headers=admin_headers,
            json={"provider": "openai", "api_key": "sk-test"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["provider"] == "openai"


@pytest.mark.asyncio
async def test_ai_connection_test_failure(client: AsyncClient, admin_headers: dict[str, str]):
    with patch(
        "app.admin.ai_settings.verify_anthropic_connection",
        new=AsyncMock(return_value=(False, "Invalid API key")),
    ):
        response = await client.post(
            "/admin/ai-settings/test-connection",
            headers=admin_headers,
            json={"provider": "anthropic", "api_key": "bad-key", "model": "claude-haiku-4-5"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["message"] == "Invalid API key"


@pytest.mark.asyncio
async def test_get_smtp_settings(client: AsyncClient, admin_headers: dict[str, str]):
    response = await client.get("/admin/smtp-settings", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()
    assert "smtp_host" in data
    assert data["smtp_port"] == 587
    assert "smtp_configured" in data


@pytest.mark.asyncio
async def test_update_smtp_settings(client: AsyncClient, admin_headers: dict[str, str]):
    response = await client.patch(
        "/admin/smtp-settings",
        headers=admin_headers,
        json={
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_user": "mail-user",
            "smtp_password": "secret-pass",
            "smtp_from": "estimates@yourcompany.com",
            "smtp_use_tls": True,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["smtp_host"] == "smtp.example.com"
    assert data["smtp_user"] == "mail-user"
    assert data["smtp_from"] == "estimates@yourcompany.com"
    assert data["smtp_password_configured"] is True
    assert data["smtp_password_hint"] == "...pass"
    assert data["smtp_configured"] is True


@pytest.mark.asyncio
async def test_smtp_settings_requires_admin(client: AsyncClient, auth_headers: dict[str, str]):
    response = await client.get("/admin/smtp-settings", headers=auth_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_discount_settings_defaults(client: AsyncClient, admin_headers: dict[str, str]):
    response = await client.get("/admin/discount-settings", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["estimate_discount_rate"] == 0.30


@pytest.mark.asyncio
async def test_update_discount_settings(client: AsyncClient, admin_headers: dict[str, str]):
    response = await client.patch(
        "/admin/discount-settings",
        headers=admin_headers,
        json={"estimate_discount_rate": 0.30},
    )
    assert response.status_code == 200
    assert response.json()["estimate_discount_rate"] == 0.30

    get_response = await client.get("/admin/discount-settings", headers=admin_headers)
    assert get_response.json()["estimate_discount_rate"] == 0.30


@pytest.mark.asyncio
async def test_discount_settings_requires_admin(client: AsyncClient, auth_headers: dict[str, str]):
    response = await client.get("/admin/discount-settings", headers=auth_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_smtp_connection_test_success(client: AsyncClient, admin_headers: dict[str, str]):
    with patch(
        "app.admin.smtp_settings.test_smtp_connection",
        new=AsyncMock(return_value=(True, "Connection successful")),
    ):
        response = await client.post(
            "/admin/smtp-settings/test-connection",
            headers=admin_headers,
            json={"smtp_host": "smtp.example.com", "smtp_port": 587},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
