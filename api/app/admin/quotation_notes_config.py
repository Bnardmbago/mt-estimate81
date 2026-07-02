from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exports.pricing_summary import DEFAULT_QUOTATION_SPECIAL_NOTES


@dataclass(frozen=True)
class QuotationNotesConfig:
    title_ja: str
    title_en: str
    body_ja: str
    body_en: str


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


def _resolved_title(stored: str | None, locale: str) -> str:
    if stored is not None and stored.strip():
        return stored.strip()
    return DEFAULT_QUOTATION_SPECIAL_NOTES[locale]["title"]


def _resolved_body(stored: str | None, locale: str) -> str:
    if stored is not None and stored.strip():
        return stored.strip()
    return DEFAULT_QUOTATION_SPECIAL_NOTES[locale]["body"]


def default_quotation_notes_config() -> QuotationNotesConfig:
    return QuotationNotesConfig(
        title_ja=DEFAULT_QUOTATION_SPECIAL_NOTES["ja"]["title"],
        title_en=DEFAULT_QUOTATION_SPECIAL_NOTES["en"]["title"],
        body_ja=DEFAULT_QUOTATION_SPECIAL_NOTES["ja"]["body"],
        body_en=DEFAULT_QUOTATION_SPECIAL_NOTES["en"]["body"],
    )


async def get_quotation_notes_config(db: AsyncSession) -> QuotationNotesConfig:
    row = await _get_config_row(db)
    return QuotationNotesConfig(
        title_ja=_resolved_title(row.quotation_special_notes_title_ja, "ja"),
        title_en=_resolved_title(row.quotation_special_notes_title_en, "en"),
        body_ja=_resolved_body(row.quotation_special_notes_body_ja, "ja"),
        body_en=_resolved_body(row.quotation_special_notes_body_en, "en"),
    )


async def update_quotation_notes_config(
    db: AsyncSession,
    *,
    title_ja: str | None = None,
    title_en: str | None = None,
    body_ja: str | None = None,
    body_en: str | None = None,
) -> QuotationNotesConfig:
    row = await _get_config_row(db)

    if title_ja is not None:
        row.quotation_special_notes_title_ja = title_ja.strip() or None
    if title_en is not None:
        row.quotation_special_notes_title_en = title_en.strip() or None
    if body_ja is not None:
        row.quotation_special_notes_body_ja = body_ja.strip() or None
    if body_en is not None:
        row.quotation_special_notes_body_en = body_en.strip() or None

    row.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(row)
    return await get_quotation_notes_config(db)
