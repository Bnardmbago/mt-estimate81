import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.contact import _hash_token
from app.auth.service import create_access_token, hash_password
from app.models.contact_magic_link import ContactMagicLink
from app.models.rate_card import RateCard, RateCardVersion
from app.models.user import ACCOUNT_TYPE_CONTACT, User
from app.rate_cards.defaults import DEFAULT_RATE_CARD_SETTINGS


@pytest.fixture
async def contact_headers(db_session: AsyncSession) -> dict[str, str]:
    admin = User(
        id=uuid.uuid4(),
        email="admin-contact@example.com",
        password_hash=hash_password("adminpass"),
        display_name="Admin",
        is_admin=True,
    )
    db_session.add(admin)
    await db_session.flush()

    system_card = RateCard(
        name="System Rates",
        is_active=True,
        is_system=True,
        created_by=admin.id,
    )
    db_session.add(system_card)
    await db_session.flush()
    db_session.add(
        RateCardVersion(
            rate_card_id=system_card.id,
            version_number=1,
            settings=DEFAULT_RATE_CARD_SETTINGS,
        )
    )

    user = User(
        id=uuid.uuid4(),
        email="contact@example.com",
        password_hash=None,
        display_name="Contact User",
        company_name="ACME",
        account_type=ACCOUNT_TYPE_CONTACT,
        preferred_locale="en",
    )
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(
        {"sub": str(user.id), "is_admin": False, "account_type": ACCOUNT_TYPE_CONTACT}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_request_magic_link_creates_contact_user(client: AsyncClient):
    with patch("app.auth.contact.send_email", new=AsyncMock()) as mock_send:
        response = await client.post(
            "/auth/contact/request-link",
            json={
                "email": "newcontact@example.com",
                "display_name": "Contact User",
                "company_name": "ACME",
                "locale": "en",
                "captcha_token": "dev-bypass",
            },
        )

    assert response.status_code == 204
    mock_send.assert_awaited_once()


@pytest.mark.asyncio
async def test_verify_magic_link_endpoint(client: AsyncClient, db_session: AsyncSession):
    user = User(
        id=uuid.uuid4(),
        email="verify@example.com",
        password_hash=None,
        display_name="Verify User",
        company_name="ACME",
        account_type=ACCOUNT_TYPE_CONTACT,
        preferred_locale="en",
    )
    admin = User(
        id=uuid.uuid4(),
        email="admin-verify@example.com",
        password_hash=hash_password("adminpass"),
        display_name="Admin",
        is_admin=True,
    )
    db_session.add_all([user, admin])
    await db_session.flush()

    system_card = RateCard(
        name="System",
        is_active=True,
        is_system=True,
        created_by=admin.id,
    )
    db_session.add(system_card)
    await db_session.flush()
    db_session.add(
        RateCardVersion(
            rate_card_id=system_card.id,
            version_number=1,
            settings=DEFAULT_RATE_CARD_SETTINGS,
        )
    )

    raw_token = "verify-token-123"
    db_session.add(
        ContactMagicLink(
            user_id=user.id,
            token_hash=_hash_token(raw_token),
            expires_at=datetime.utcnow() + timedelta(minutes=15),
        )
    )
    await db_session.commit()

    response = await client.post("/auth/contact/verify", json={"token": raw_token})
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["estimate_id"]
    assert data["user"]["account_type"] == ACCOUNT_TYPE_CONTACT


@pytest.mark.asyncio
async def test_full_user_email_rejected_for_contact_flow(client: AsyncClient, db_session: AsyncSession):
    user = User(
        id=uuid.uuid4(),
        email="full@example.com",
        password_hash=hash_password("password123"),
        display_name="Full User",
        account_type="full",
    )
    db_session.add(user)
    await db_session.commit()

    with patch("app.auth.contact.send_email", new=AsyncMock()):
        response = await client.post(
            "/auth/contact/request-link",
            json={
                "email": "full@example.com",
                "display_name": "Full User",
                "company_name": "ACME",
                "locale": "en",
                "captcha_token": "dev-bypass",
            },
        )

    assert response.status_code == 409
    assert response.json()["code"] == "USE_FULL_LOGIN"


@pytest.mark.asyncio
async def test_request_magic_link_name_only(client: AsyncClient):
    with patch("app.auth.contact.send_email", new=AsyncMock()) as mock_send:
        response = await client.post(
            "/auth/contact/request-link",
            json={
                "email": "nameonly@example.com",
                "display_name": "Name Only",
                "company_name": "",
                "locale": "en",
                "captcha_token": "dev-bypass",
            },
        )

    assert response.status_code == 204
    mock_send.assert_awaited_once()


@pytest.mark.asyncio
async def test_request_magic_link_company_only(client: AsyncClient, db_session: AsyncSession):
    with patch("app.auth.contact.send_email", new=AsyncMock()) as mock_send:
        response = await client.post(
            "/auth/contact/request-link",
            json={
                "email": "companyonly@example.com",
                "display_name": "",
                "company_name": "ACME Corp",
                "locale": "en",
                "captcha_token": "dev-bypass",
            },
        )

    assert response.status_code == 204
    mock_send.assert_awaited_once()

    from sqlalchemy import select

    result = await db_session.execute(
        select(User).where(User.email == "companyonly@example.com")
    )
    user = result.scalar_one()
    assert user.display_name == "ACME Corp"
    assert user.company_name == "ACME Corp"


@pytest.mark.asyncio
async def test_request_magic_link_requires_name_or_company(client: AsyncClient):
    response = await client.post(
        "/auth/contact/request-link",
        json={
            "email": "missing@example.com",
            "display_name": "",
            "company_name": "",
            "locale": "en",
            "captcha_token": "dev-bypass",
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "NAME_OR_COMPANY_REQUIRED"
