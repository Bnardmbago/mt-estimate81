from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.email.smtp import SMTPRuntimeConfig


@dataclass(frozen=True)
class SMTPConfig:
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    smtp_from: str
    smtp_use_tls: bool


def mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 4:
        return "****"
    return f"...{value[-4:]}"


async def _get_config_row(db: AsyncSession):
    from app.models.system_config import SystemConfig

    result = await db.execute(select(SystemConfig).where(SystemConfig.id == 1))
    row = result.scalar_one_or_none()
    if row is None:
        row = SystemConfig(id=1)
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


async def get_smtp_config(db: AsyncSession) -> SMTPConfig:
    row = await _get_config_row(db)
    return SMTPConfig(
        smtp_host=row.smtp_host if row.smtp_host is not None else settings.smtp_host,
        smtp_port=row.smtp_port if row.smtp_port is not None else settings.smtp_port,
        smtp_user=row.smtp_user if row.smtp_user is not None else settings.smtp_user,
        smtp_password=row.smtp_password if row.smtp_password is not None else settings.smtp_password,
        smtp_from=row.smtp_from if row.smtp_from is not None else settings.smtp_from,
        smtp_use_tls=row.smtp_use_tls if row.smtp_use_tls is not None else settings.smtp_use_tls,
    )


def smtp_runtime_config(config: SMTPConfig) -> SMTPRuntimeConfig:
    return SMTPRuntimeConfig(
        host=config.smtp_host,
        port=config.smtp_port,
        user=config.smtp_user,
        password=config.smtp_password,
        from_address=config.smtp_from,
        use_tls=config.smtp_use_tls,
    )


async def update_smtp_config(
    db: AsyncSession,
    *,
    smtp_host: str | None = None,
    smtp_port: int | None = None,
    smtp_user: str | None = None,
    smtp_password: str | None = None,
    smtp_from: str | None = None,
    smtp_use_tls: bool | None = None,
    clear_smtp_password: bool = False,
) -> SMTPConfig:
    row = await _get_config_row(db)

    if smtp_host is not None:
        row.smtp_host = smtp_host
    if smtp_port is not None:
        row.smtp_port = smtp_port
    if smtp_user is not None:
        row.smtp_user = smtp_user
    if smtp_password is not None:
        row.smtp_password = smtp_password
    elif clear_smtp_password:
        row.smtp_password = None
    if smtp_from is not None:
        row.smtp_from = smtp_from
    if smtp_use_tls is not None:
        row.smtp_use_tls = smtp_use_tls

    row.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(row)
    return await get_smtp_config(db)
