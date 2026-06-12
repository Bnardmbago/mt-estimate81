from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_ESTIMATE_DISCOUNT_RATE = 0.30


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


async def get_estimate_discount_rate(db: AsyncSession) -> float:
    row = await _get_config_row(db)
    if row.estimate_discount_rate is None:
        return DEFAULT_ESTIMATE_DISCOUNT_RATE
    return float(row.estimate_discount_rate)


async def update_estimate_discount_rate(db: AsyncSession, rate: float) -> float:
    if rate < 0.0 or rate > 1.0:
        raise ValueError("estimate_discount_rate must be between 0.0 and 1.0")

    row = await _get_config_row(db)
    row.estimate_discount_rate = rate
    row.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(row)
    return float(row.estimate_discount_rate)
