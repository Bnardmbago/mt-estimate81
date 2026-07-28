"""Admin endpoints for Google/Canva OAuth *app* credentials."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.oauth_app_config import (
    canva_app_configured,
    get_oauth_app_config,
    google_app_configured,
    mask_secret,
    update_oauth_app_config,
)
from app.dependencies import get_db, require_admin
from app.models.user import User

router = APIRouter(prefix="/admin/oauth-app-settings", tags=["admin"])


class OAuthAppSettingsResponse(BaseModel):
    google_oauth_client_id: str
    google_oauth_redirect_uri: str
    google_oauth_client_secret_configured: bool
    google_oauth_client_secret_hint: str | None
    google_configured: bool
    canva_client_id: str
    canva_redirect_uri: str
    canva_client_secret_configured: bool
    canva_client_secret_hint: str | None
    canva_configured: bool
    canva_template_proposal_en: str
    canva_template_proposal_ja: str
    canva_template_poc_en: str
    canva_template_poc_ja: str


class OAuthAppSettingsUpdate(BaseModel):
    google_oauth_client_id: str | None = Field(default=None, max_length=255)
    google_oauth_client_secret: str | None = Field(default=None, max_length=255)
    google_oauth_redirect_uri: str | None = Field(default=None, max_length=512)
    clear_google_oauth_client_secret: bool = False
    canva_client_id: str | None = Field(default=None, max_length=255)
    canva_client_secret: str | None = Field(default=None, max_length=255)
    canva_redirect_uri: str | None = Field(default=None, max_length=512)
    clear_canva_client_secret: bool = False
    canva_template_proposal_en: str | None = Field(default=None, max_length=128)
    canva_template_proposal_ja: str | None = Field(default=None, max_length=128)
    canva_template_poc_en: str | None = Field(default=None, max_length=128)
    canva_template_poc_ja: str | None = Field(default=None, max_length=128)


async def build_oauth_app_settings_response(db: AsyncSession) -> OAuthAppSettingsResponse:
    config = await get_oauth_app_config(db)
    return OAuthAppSettingsResponse(
        google_oauth_client_id=config.google_oauth_client_id,
        google_oauth_redirect_uri=config.google_oauth_redirect_uri,
        google_oauth_client_secret_configured=bool(config.google_oauth_client_secret),
        google_oauth_client_secret_hint=mask_secret(config.google_oauth_client_secret),
        google_configured=google_app_configured(config),
        canva_client_id=config.canva_client_id,
        canva_redirect_uri=config.canva_redirect_uri,
        canva_client_secret_configured=bool(config.canva_client_secret),
        canva_client_secret_hint=mask_secret(config.canva_client_secret),
        canva_configured=canva_app_configured(config),
        canva_template_proposal_en=config.canva_template_proposal_en,
        canva_template_proposal_ja=config.canva_template_proposal_ja,
        canva_template_poc_en=config.canva_template_poc_en,
        canva_template_poc_ja=config.canva_template_poc_ja,
    )


@router.get("", response_model=OAuthAppSettingsResponse)
async def get_oauth_app_settings(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    return await build_oauth_app_settings_response(db)


@router.patch("", response_model=OAuthAppSettingsResponse)
async def patch_oauth_app_settings(
    body: OAuthAppSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    google_secret = body.google_oauth_client_secret.strip() if body.google_oauth_client_secret else None
    canva_secret = body.canva_client_secret.strip() if body.canva_client_secret else None

    await update_oauth_app_config(
        db,
        google_oauth_client_id=(
            body.google_oauth_client_id.strip() if body.google_oauth_client_id is not None else None
        ),
        google_oauth_client_secret=google_secret if google_secret else None,
        google_oauth_redirect_uri=(
            body.google_oauth_redirect_uri.strip()
            if body.google_oauth_redirect_uri is not None
            else None
        ),
        clear_google_oauth_client_secret=body.clear_google_oauth_client_secret,
        canva_client_id=body.canva_client_id.strip() if body.canva_client_id is not None else None,
        canva_client_secret=canva_secret if canva_secret else None,
        canva_redirect_uri=(
            body.canva_redirect_uri.strip() if body.canva_redirect_uri is not None else None
        ),
        clear_canva_client_secret=body.clear_canva_client_secret,
        canva_template_proposal_en=(
            body.canva_template_proposal_en.strip()
            if body.canva_template_proposal_en is not None
            else None
        ),
        canva_template_proposal_ja=(
            body.canva_template_proposal_ja.strip()
            if body.canva_template_proposal_ja is not None
            else None
        ),
        canva_template_poc_en=(
            body.canva_template_poc_en.strip() if body.canva_template_poc_en is not None else None
        ),
        canva_template_poc_ja=(
            body.canva_template_poc_ja.strip() if body.canva_template_poc_ja is not None else None
        ),
    )
    return await build_oauth_app_settings_response(db)
