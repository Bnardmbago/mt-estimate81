"""Resolve Google/Canva OAuth *app* credentials from system_config with env fallback."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.smtp_config import _get_config_row, mask_secret
from app.config import settings


@dataclass(frozen=True)
class OAuthAppConfig:
    google_oauth_client_id: str
    google_oauth_client_secret: str
    google_oauth_redirect_uri: str
    canva_client_id: str
    canva_client_secret: str
    canva_redirect_uri: str
    canva_template_proposal_en: str
    canva_template_proposal_ja: str
    canva_template_poc_en: str
    canva_template_poc_ja: str


def _pick(db_value: str | None, env_value: str) -> str:
    if db_value is not None and str(db_value).strip() != "":
        return str(db_value).strip()
    return (env_value or "").strip()


async def get_oauth_app_config(db: AsyncSession) -> OAuthAppConfig:
    row = await _get_config_row(db)
    return OAuthAppConfig(
        google_oauth_client_id=_pick(row.google_oauth_client_id, settings.google_oauth_client_id),
        google_oauth_client_secret=_pick(
            row.google_oauth_client_secret, settings.google_oauth_client_secret
        ),
        google_oauth_redirect_uri=_pick(
            row.google_oauth_redirect_uri, settings.google_oauth_redirect_uri
        ),
        canva_client_id=_pick(row.canva_client_id, settings.canva_client_id),
        canva_client_secret=_pick(row.canva_client_secret, settings.canva_client_secret),
        canva_redirect_uri=_pick(row.canva_redirect_uri, settings.canva_redirect_uri),
        canva_template_proposal_en=_pick(
            row.canva_template_proposal_en, settings.canva_template_proposal_en
        ),
        canva_template_proposal_ja=_pick(
            row.canva_template_proposal_ja, settings.canva_template_proposal_ja
        ),
        canva_template_poc_en=_pick(row.canva_template_poc_en, settings.canva_template_poc_en),
        canva_template_poc_ja=_pick(row.canva_template_poc_ja, settings.canva_template_poc_ja),
    )


def google_app_configured(config: OAuthAppConfig) -> bool:
    return bool(config.google_oauth_client_id and config.google_oauth_client_secret)


def canva_app_configured(config: OAuthAppConfig) -> bool:
    return bool(config.canva_client_id and config.canva_client_secret)


async def update_oauth_app_config(
    db: AsyncSession,
    *,
    google_oauth_client_id: str | None = None,
    google_oauth_client_secret: str | None = None,
    google_oauth_redirect_uri: str | None = None,
    clear_google_oauth_client_secret: bool = False,
    canva_client_id: str | None = None,
    canva_client_secret: str | None = None,
    canva_redirect_uri: str | None = None,
    clear_canva_client_secret: bool = False,
    canva_template_proposal_en: str | None = None,
    canva_template_proposal_ja: str | None = None,
    canva_template_poc_en: str | None = None,
    canva_template_poc_ja: str | None = None,
) -> OAuthAppConfig:
    row = await _get_config_row(db)

    if google_oauth_client_id is not None:
        row.google_oauth_client_id = google_oauth_client_id or None
    if google_oauth_client_secret is not None:
        row.google_oauth_client_secret = google_oauth_client_secret
    elif clear_google_oauth_client_secret:
        row.google_oauth_client_secret = None
    if google_oauth_redirect_uri is not None:
        row.google_oauth_redirect_uri = google_oauth_redirect_uri or None

    if canva_client_id is not None:
        row.canva_client_id = canva_client_id or None
    if canva_client_secret is not None:
        row.canva_client_secret = canva_client_secret
    elif clear_canva_client_secret:
        row.canva_client_secret = None
    if canva_redirect_uri is not None:
        row.canva_redirect_uri = canva_redirect_uri or None

    if canva_template_proposal_en is not None:
        row.canva_template_proposal_en = canva_template_proposal_en or None
    if canva_template_proposal_ja is not None:
        row.canva_template_proposal_ja = canva_template_proposal_ja or None
    if canva_template_poc_en is not None:
        row.canva_template_poc_en = canva_template_poc_en or None
    if canva_template_poc_ja is not None:
        row.canva_template_poc_ja = canva_template_poc_ja or None

    row.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(row)
    return await get_oauth_app_config(db)


__all__ = [
    "OAuthAppConfig",
    "canva_app_configured",
    "get_oauth_app_config",
    "google_app_configured",
    "mask_secret",
    "update_oauth_app_config",
]
