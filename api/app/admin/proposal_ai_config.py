"""Admin config for proposal generation purpose presets."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.proposals.generation_presets import (
    DEFAULT_PROPOSAL_AI_SETTINGS,
    GENERATION_PURPOSES,
    GenerationPurpose,
    PURPOSE_PRESETS,
    get_preset,
    normalize_proposal_ai_settings,
    purpose_for_part,
)


async def _get_config_row(db: AsyncSession):
    from app.models.system_config import SystemConfig

    result = await db.execute(select(SystemConfig).where(SystemConfig.id == 1))
    row = result.scalar_one_or_none()
    if row is None:
        row = SystemConfig(id=1, proposal_ai_settings=dict(DEFAULT_PROPOSAL_AI_SETTINGS))
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


async def get_proposal_ai_settings(db: AsyncSession) -> dict[str, GenerationPurpose]:
    row = await _get_config_row(db)
    return normalize_proposal_ai_settings(getattr(row, "proposal_ai_settings", None))


async def update_proposal_ai_settings(
    db: AsyncSession,
    patch: dict[str, Any],
) -> dict[str, GenerationPurpose]:
    current = await get_proposal_ai_settings(db)
    merged = dict(current)
    for key in DEFAULT_PROPOSAL_AI_SETTINGS:
        if key not in patch or patch[key] is None:
            continue
        value = patch[key]
        if value not in GENERATION_PURPOSES:
            raise ValueError(f"{key} must be one of {', '.join(GENERATION_PURPOSES)}")
        merged[key] = value

    row = await _get_config_row(db)
    row.proposal_ai_settings = merged
    row.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(row)
    return normalize_proposal_ai_settings(row.proposal_ai_settings)


def preset_summaries() -> list[dict[str, Any]]:
    items = []
    for purpose in GENERATION_PURPOSES:
        preset = get_preset(purpose)
        items.append(
            {
                "purpose": purpose,
                "max_tokens": preset.max_tokens,
                "timeout_seconds": preset.timeout_seconds,
                "min_diagrams": preset.min_diagrams,
                "min_tables_proposal": preset.min_tables_proposal,
                "min_tables_poc": preset.min_tables_poc,
            }
        )
    return items


def settings_response_payload(settings: dict[str, GenerationPurpose]) -> dict[str, Any]:
    return {
        "assessment_purpose": purpose_for_part(settings, "assessment"),
        "proposal_purpose": purpose_for_part(settings, "proposal"),
        "poc_purpose": purpose_for_part(settings, "poc"),
        "presets": preset_summaries(),
        "purposes": list(GENERATION_PURPOSES),
    }
