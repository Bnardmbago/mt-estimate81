"""Cleanup for expired presentation drafts and their temporary assets."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.presentation_draft import PresentationPresetDraft
from app.presentation.asset_paths import draft_prefixes_for
from app.storage.factory import get_storage_backend


async def cleanup_stale_presentation_drafts(db: AsyncSession) -> int:
    result = await db.execute(
        select(PresentationPresetDraft).where(
            PresentationPresetDraft.expires_at < datetime.utcnow()
        )
    )
    drafts = list(result.scalars().all())
    if not drafts:
        return 0

    prefixes = [
        prefix
        for draft in drafts
        for prefix in draft_prefixes_for(str(draft.id))
    ]
    for draft in drafts:
        await db.delete(draft)
    await db.commit()

    storage = get_storage_backend()
    for prefix in prefixes:
        await storage.delete_prefix(prefix)
    return len(drafts)
