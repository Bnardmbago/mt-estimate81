from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.system_config import SystemConfig

DEFAULT_REGISTRATION_SEQUENCE = 9010001234561


async def _get_config_row(db: AsyncSession) -> SystemConfig:
    result = await db.execute(select(SystemConfig).where(SystemConfig.id == 1))
    row = result.scalar_one_or_none()
    if row is None:
        row = SystemConfig(id=1)
        db.add(row)
        await db.flush()
    return row


def format_registration_number(sequence: int) -> str:
    return f"T{sequence}"


def preview_next_registration_number(config: SystemConfig) -> str:
    sequence = _current_registration_sequence(config)
    return format_registration_number(sequence + 1)


def _current_registration_sequence(config: SystemConfig) -> int:
    if config.registration_number_sequence:
        return int(config.registration_number_sequence)

    stored = (config.quotation_invoice_registration_number or "").strip()
    if not stored:
        stored = settings.quotation_invoice_registration_number.strip()
    if stored.startswith("T") and stored[1:].isdigit():
        return int(stored[1:]) - 1

    return DEFAULT_REGISTRATION_SEQUENCE


def _allocate_registration_number(config: SystemConfig) -> str:
    sequence = _current_registration_sequence(config) + 1
    config.registration_number_sequence = sequence
    return format_registration_number(sequence)


def resolved_contact_person(config: SystemConfig) -> str:
    stored = (config.quotation_contact_person or "").strip()
    if stored:
        return stored
    return settings.quotation_contact_person.strip()


def set_registration_sequence_from_value(config: SystemConfig, value: str) -> None:
    cleaned = value.strip()
    if not cleaned:
        config.registration_number_sequence = DEFAULT_REGISTRATION_SEQUENCE
        return
    if not cleaned.startswith("T") or not cleaned[1:].isdigit():
        raise ValueError("Registration number must be T followed by digits")
    config.registration_number_sequence = int(cleaned[1:]) - 1


async def allocate_quotation_export_fields(
    db: AsyncSession,
    *,
    generated_at: datetime,
) -> tuple[str, str, str]:
    """Return (quotation_number, registration_number, contact_person) for a quotation export."""
    config = await _get_config_row(db)
    issue_date = generated_at.date()
    prefix = (config.quotation_number_prefix or "BAI").strip() or "BAI"

    if config.quotation_number_date != issue_date:
        config.quotation_number_date = issue_date
        config.quotation_number_sequence = 0

    config.quotation_number_sequence += 1
    sequence = config.quotation_number_sequence
    config.updated_at = datetime.utcnow()
    await db.flush()

    date_part = issue_date.strftime("%Y%m%d")
    quotation_number = f"{prefix}-{date_part}-{sequence:03d}"
    registration_number = _allocate_registration_number(config)
    contact_person = resolved_contact_person(config)
    await db.flush()
    return quotation_number, registration_number, contact_person


async def allocate_quotation_number(
    db: AsyncSession,
    *,
    generated_at: datetime,
) -> tuple[str, str]:
    """Backward-compatible wrapper returning quotation and registration numbers only."""
    quotation_number, registration_number, _contact_person = await allocate_quotation_export_fields(
        db,
        generated_at=generated_at,
    )
    return quotation_number, registration_number
