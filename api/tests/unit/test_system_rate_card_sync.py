import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rate_card import RateCard, RateCardVersion
from app.models.user import User
from app.rate_cards.defaults import DEFAULT_RATE_CARD_NAME, DEFAULT_RATE_CARD_SETTINGS
from app.rate_cards.service import get_latest_version_for_card
from app.rate_cards.system import (
    sync_system_rate_card_from_defaults,
    system_rate_card_settings_drifted,
)


@pytest.mark.asyncio
async def test_system_rate_card_settings_drifted_detects_approach_change():
    settings = dict(DEFAULT_RATE_CARD_SETTINGS)
    settings["development_approach"] = "traditional"
    assert system_rate_card_settings_drifted(settings) is True
    assert system_rate_card_settings_drifted(DEFAULT_RATE_CARD_SETTINGS) is False


@pytest.mark.asyncio
async def test_sync_system_rate_card_from_defaults_creates_new_version(db_session: AsyncSession):
    admin = User(
        id=uuid.uuid4(),
        email="sync-admin@example.com",
        password_hash="hash",
        display_name="Admin",
        is_admin=True,
    )
    db_session.add(admin)
    await db_session.flush()

    stale_settings = dict(DEFAULT_RATE_CARD_SETTINGS)
    stale_settings["development_approach"] = "traditional"
    stale_settings["roles"] = [
        {"name": "PM", "hourly_rate": 10000, "daily_rate": 80000},
        {"name": "Developer", "hourly_rate": 8000, "daily_rate": 64000},
    ]

    card = RateCard(
        name="Legacy System Name",
        is_active=True,
        is_system=True,
        created_by=admin.id,
    )
    db_session.add(card)
    await db_session.flush()
    db_session.add(
        RateCardVersion(
            rate_card_id=card.id,
            version_number=1,
            settings=stale_settings,
        )
    )
    await db_session.flush()

    synced = await sync_system_rate_card_from_defaults(db_session, admin=admin)
    latest = await get_latest_version_for_card(db_session, synced.id)

    assert synced.name == DEFAULT_RATE_CARD_NAME

    assert latest.version_number == 2
    assert latest.settings["development_approach"] == "ai_assisted"
    assert len(latest.settings["roles"]) == len(DEFAULT_RATE_CARD_SETTINGS["roles"])
