"""Align feature-item role labels with the estimate's rate card."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.calculation.role_allocation import resolve_feature_item_role
from app.i18n.localized_content import store_feature_item_localization
from app.models.estimate import FeatureItem
from app.rate_cards.normalize import role_hourly_rate
from app.rate_cards.service import get_rate_card_roles


def role_rates_from_settings(roles: list[dict[str, Any]]) -> dict[str, int]:
    return {
        str(role.get("name", "")).strip(): role_hourly_rate(role)
        for role in roles
        if str(role.get("name", "")).strip()
    }


def align_feature_item_role_fields(
    *,
    role: str,
    phase: str,
    role_rates: dict[str, int],
) -> str | None:
    """Return the rate-card role name for a feature item, or None if unmapped."""
    return resolve_feature_item_role(role, role_rates, phase=phase)


async def align_feature_items_to_rate_card(
    db: AsyncSession,
    estimate_id: uuid.UUID,
    rate_card_id: uuid.UUID,
    user,
    *,
    locale: str,
) -> int:
    """Rewrite feature-item roles to exact rate-card role names after card changes."""
    roles = await get_rate_card_roles(db, rate_card_id, user)
    if not roles:
        return 0

    role_rates = role_rates_from_settings(roles)
    result = await db.execute(
        select(FeatureItem).where(FeatureItem.estimate_id == estimate_id).order_by(FeatureItem.sort_order)
    )
    items = list(result.scalars().all())
    updated = 0

    for item in items:
        resolved = align_feature_item_role_fields(
            role=item.role,
            phase=item.phase,
            role_rates=role_rates,
        )
        if resolved is None or resolved == item.role:
            continue
        item.role = resolved
        item.localizations = store_feature_item_localization(
            item.localizations,
            locale,
            name=item.name,
            description=item.description,
            phase=item.phase,
            role=resolved,
        )
        updated += 1

    return updated
