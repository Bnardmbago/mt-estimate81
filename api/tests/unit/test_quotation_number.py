from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.exports.quotation_number import allocate_quotation_export_fields, allocate_quotation_number
from app.models.system_config import SystemConfig


@pytest.mark.asyncio
async def test_allocate_quotation_number_first_of_day(db_session: AsyncSession):
    generated_at = datetime(2026, 6, 29, 10, 0, 0)
    quotation_number, registration_number = await allocate_quotation_number(
        db_session,
        generated_at=generated_at,
    )

    assert quotation_number == "BAI-20260629-001"
    assert registration_number == "T9010001234562"


@pytest.mark.asyncio
async def test_allocate_registration_number_increments(db_session: AsyncSession):
    generated_at = datetime(2026, 6, 29, 10, 0, 0)
    _, first = await allocate_quotation_number(db_session, generated_at=generated_at)
    _, second = await allocate_quotation_number(db_session, generated_at=generated_at)

    assert first == "T9010001234562"
    assert second == "T9010001234563"


@pytest.mark.asyncio
async def test_allocate_quotation_number_increments_same_day(db_session: AsyncSession):
    generated_at = datetime(2026, 6, 29, 10, 0, 0)
    first, _ = await allocate_quotation_number(db_session, generated_at=generated_at)
    second, _ = await allocate_quotation_number(db_session, generated_at=generated_at)

    assert first == "BAI-20260629-001"
    assert second == "BAI-20260629-002"


@pytest.mark.asyncio
async def test_allocate_quotation_number_resets_on_new_day(db_session: AsyncSession):
    day_one = datetime(2026, 6, 29, 10, 0, 0)
    day_two = datetime(2026, 6, 30, 10, 0, 0)

    await allocate_quotation_number(db_session, generated_at=day_one)
    await allocate_quotation_number(db_session, generated_at=day_one)
    quotation_number, _ = await allocate_quotation_number(db_session, generated_at=day_two)

    assert quotation_number == "BAI-20260630-001"


@pytest.mark.asyncio
async def test_allocate_registration_number_seeds_from_legacy_config(db_session: AsyncSession):
    config = SystemConfig(
        id=1,
        registration_number_sequence=0,
        quotation_invoice_registration_number="T9010001234999",
    )
    db_session.add(config)
    await db_session.flush()

    _, registration_number = await allocate_quotation_number(
        db_session,
        generated_at=datetime(2026, 6, 29),
    )

    assert registration_number == "T9010001234999"


@pytest.mark.asyncio
async def test_allocate_quotation_export_fields_includes_contact_person(db_session: AsyncSession):
    config = SystemConfig(id=1, quotation_contact_person="Suzuki Hanako")
    db_session.add(config)
    await db_session.flush()

    _, _, contact_person = await allocate_quotation_export_fields(
        db_session,
        generated_at=datetime(2026, 6, 29),
    )

    assert contact_person == "Suzuki Hanako"
