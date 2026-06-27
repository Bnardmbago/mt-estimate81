import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.estimate import Estimate, EstimateStatus
from app.models.rate_card import RateCard, RateCardVersion
from app.models.user import User
from app.rate_cards.defaults import DEFAULT_RATE_CARD_SETTINGS
from app.rate_cards.system import attach_system_rate_card, get_system_rate_card


@pytest.mark.asyncio
async def test_attach_system_rate_card_sets_estimate_fields(db_session: AsyncSession):
    admin = User(
        id=uuid.uuid4(),
        email="admin-rc@example.com",
        password_hash="hash",
        display_name="Admin",
        is_admin=True,
    )
    db_session.add(admin)
    await db_session.flush()

    card = RateCard(
        name="System",
        is_active=True,
        is_system=True,
        created_by=admin.id,
    )
    db_session.add(card)
    await db_session.flush()
    version = RateCardVersion(
        rate_card_id=card.id,
        version_number=1,
        settings=DEFAULT_RATE_CARD_SETTINGS,
    )
    db_session.add(version)
    await db_session.flush()

    estimate = Estimate(
        project_name="Test",
        client_name="ACME",
        locale="en",
        status=EstimateStatus.DRAFT.value,
        created_by=admin.id,
    )
    db_session.add(estimate)
    await db_session.flush()

    await attach_system_rate_card(db_session, estimate)

    assert estimate.rate_card_id == card.id
    assert estimate.rate_card_version_id == version.id
    system = await get_system_rate_card(db_session)
    assert system is not None
    assert system.is_system is True
