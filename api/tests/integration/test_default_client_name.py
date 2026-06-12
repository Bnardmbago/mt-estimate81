import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import create_access_token, hash_password
from app.models.user import User


def _headers_for(user: User) -> dict[str, str]:
    token = create_access_token({"sub": str(user.id), "is_admin": user.is_admin})
    return {"Authorization": f"Bearer {token}"}


async def _create_user_in_db(
    db_session: AsyncSession,
    *,
    email: str,
    display_name: str,
    company_name: str | None = None,
) -> User:
    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash=hash_password("testpass"),
        display_name=display_name,
        company_name=company_name,
        is_admin=False,
        preferred_locale="en",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_default_client_name_uses_company_name(
    client: AsyncClient,
    db_session: AsyncSession,
):
    user = await _create_user_in_db(
        db_session,
        email="corp@example.com",
        display_name="Jane Doe",
        company_name="ACME Corp",
    )
    headers = _headers_for(user)

    response = await client.post(
        "/estimates",
        json={"project_name": "Test Project", "locale": "en"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["client_name"] == "ACME Corp"


@pytest.mark.asyncio
async def test_default_client_name_falls_back_to_display_name(
    client: AsyncClient,
    db_session: AsyncSession,
):
    user = await _create_user_in_db(
        db_session,
        email="display@example.com",
        display_name="Jane Doe",
        company_name=None,
    )
    headers = _headers_for(user)

    response = await client.post(
        "/estimates",
        json={"project_name": "Test Project", "locale": "en"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["client_name"] == "Jane Doe"


@pytest.mark.asyncio
async def test_default_client_name_falls_back_to_email(
    client: AsyncClient,
    db_session: AsyncSession,
):
    user = await _create_user_in_db(
        db_session,
        email="fallback@example.com",
        display_name="   ",
        company_name=None,
    )
    headers = _headers_for(user)

    response = await client.post(
        "/estimates",
        json={"project_name": "Test Project", "locale": "en"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["client_name"] == "fallback@example.com"


@pytest.mark.asyncio
async def test_explicit_client_name_overrides_default(
    client: AsyncClient,
    db_session: AsyncSession,
):
    user = await _create_user_in_db(
        db_session,
        email="override@example.com",
        display_name="Jane Doe",
        company_name="ACME Corp",
    )
    headers = _headers_for(user)

    response = await client.post(
        "/estimates",
        json={
            "project_name": "Test Project",
            "client_name": "Custom Client",
            "locale": "en",
        },
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["client_name"] == "Custom Client"
