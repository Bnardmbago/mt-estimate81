import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import create_access_token, hash_password
from app.models.estimate import Estimate, EstimateStatus
from app.models.rate_card import RateCard, RateCardVersion
from app.models.user import ACCOUNT_TYPE_CONTACT, User
from app.rate_cards.defaults import DEFAULT_RATE_CARD_SETTINGS


@pytest.fixture
async def contact_user_headers(db_session: AsyncSession) -> tuple[User, dict[str, str]]:
    admin = User(
        id=uuid.uuid4(),
        email="admin-est@example.com",
        password_hash=hash_password("adminpass"),
        display_name="Admin",
        is_admin=True,
    )
    db_session.add(admin)
    await db_session.flush()

    system_card = RateCard(
        name="System",
        is_active=True,
        is_system=True,
        created_by=admin.id,
    )
    db_session.add(system_card)
    await db_session.flush()
    version = RateCardVersion(
        rate_card_id=system_card.id,
        version_number=1,
        settings=DEFAULT_RATE_CARD_SETTINGS,
    )
    db_session.add(version)

    user = User(
        id=uuid.uuid4(),
        email="contact-est@example.com",
        password_hash=None,
        display_name="Contact",
        company_name="ACME",
        account_type=ACCOUNT_TYPE_CONTACT,
        preferred_locale="en",
    )
    db_session.add(user)
    await db_session.commit()

    headers = {
        "Authorization": f"Bearer {create_access_token({'sub': str(user.id), 'is_admin': False, 'account_type': ACCOUNT_TYPE_CONTACT})}"
    }
    return user, headers


@pytest.mark.asyncio
async def test_contact_user_limited_to_one_estimate(
    client: AsyncClient,
    db_session: AsyncSession,
    contact_user_headers: tuple[User, dict[str, str]],
):
    user, headers = contact_user_headers

    estimate = Estimate(
        project_name="Existing",
        client_name="ACME",
        locale="en",
        status=EstimateStatus.DRAFT.value,
        created_by=user.id,
        rate_card_id=None,
    )
    db_session.add(estimate)
    await db_session.commit()

    response = await client.post(
        "/estimates",
        headers=headers,
        json={"project_name": "Second", "locale": "en"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "CONTACT_ESTIMATE_LIMIT"
