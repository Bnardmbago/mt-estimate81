import pytest

from app.admin.discount_config import (
    DEFAULT_ESTIMATE_DISCOUNT_RATE,
    get_estimate_discount_rate,
    update_estimate_discount_rate,
)
from app.models.system_config import SystemConfig


@pytest.mark.asyncio
async def test_get_estimate_discount_rate_defaults_when_null(db_session):
    db_session.add(SystemConfig(id=1))
    await db_session.commit()

    rate = await get_estimate_discount_rate(db_session)

    assert rate == DEFAULT_ESTIMATE_DISCOUNT_RATE
    assert rate == 0.30


@pytest.mark.asyncio
async def test_get_estimate_discount_rate_reads_stored_value(db_session):
    db_session.add(SystemConfig(id=1, estimate_discount_rate=0.15))
    await db_session.commit()

    rate = await get_estimate_discount_rate(db_session)

    assert rate == 0.15


@pytest.mark.asyncio
async def test_update_estimate_discount_rate_persists(db_session):
    db_session.add(SystemConfig(id=1))
    await db_session.commit()

    updated = await update_estimate_discount_rate(db_session, 0.25)

    assert updated == 0.25
    assert await get_estimate_discount_rate(db_session) == 0.25


@pytest.mark.asyncio
async def test_update_estimate_discount_rate_rejects_out_of_range(db_session):
    db_session.add(SystemConfig(id=1))
    await db_session.commit()

    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        await update_estimate_discount_rate(db_session, 1.5)
