import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import create_access_token, hash_password
from app.exceptions import AppError
from app.exports.service import export_estimate
from app.models.estimate import Estimate, EstimateStatus, Export
from app.models.rate_card import RateCard, RateCardVersion
from app.models.user import ACCOUNT_TYPE_CONTACT, User
from app.rate_cards.defaults import DEFAULT_RATE_CARD_SETTINGS


@pytest.mark.asyncio
async def test_contact_export_limit_enforced(db_session: AsyncSession):
    admin = User(
        id=uuid.uuid4(),
        email="admin-export@example.com",
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
    await db_session.flush()

    user = User(
        id=uuid.uuid4(),
        email="contact-export@example.com",
        password_hash=None,
        display_name="Contact",
        account_type=ACCOUNT_TYPE_CONTACT,
    )
    db_session.add(user)
    await db_session.flush()

    estimate = Estimate(
        project_name="Export Test",
        client_name="ACME",
        locale="en",
        status=EstimateStatus.CALCULATED.value,
        created_by=user.id,
        rate_card_id=system_card.id,
        rate_card_version_id=version.id,
        calculation_result={"totals": {"grand_total_jpy": 1000}},
    )
    db_session.add(estimate)
    await db_session.flush()

    for index in range(3):
        db_session.add(
            Export(
                estimate_id=estimate.id,
                format="md",
                storage_path=f"exports/{estimate.id}/file-{index}.md",
                locale="en",
                generated_at=datetime.utcnow(),
                generated_by=user.id,
            )
        )
    await db_session.commit()

    with patch("app.exports.service._auto_email_single_export", new=AsyncMock()):
        with pytest.raises(AppError) as exc_info:
            await export_estimate(db_session, estimate.id, "md", "en", user)

    assert exc_info.value.code == "CONTACT_EXPORT_LIMIT"
