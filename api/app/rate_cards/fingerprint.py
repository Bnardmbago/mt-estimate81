import hashlib
import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rate_card import RateCardVersion
from app.rate_cards.normalize import normalize_settings_dict


def rate_card_settings_fingerprint(settings: dict[str, Any]) -> str:
    normalized = normalize_settings_dict(settings)
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def get_latest_rate_card_fingerprint(
    db: AsyncSession,
    rate_card_id: uuid.UUID,
) -> str | None:
    result = await db.execute(
        select(RateCardVersion)
        .where(RateCardVersion.rate_card_id == rate_card_id)
        .order_by(RateCardVersion.version_number.desc())
        .limit(1)
    )
    version = result.scalar_one_or_none()
    if not version or not version.settings:
        return None
    return rate_card_settings_fingerprint(version.settings)
