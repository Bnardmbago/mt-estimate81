"""Unit tests for OAuth app config resolve (DB over env) and change-password gates."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.admin.oauth_app_config import (
    OAuthAppConfig,
    canva_app_configured,
    get_oauth_app_config,
    google_app_configured,
)
from app.exceptions import AppError
from app.models.user import ACCOUNT_TYPE_CONTACT, ACCOUNT_TYPE_FULL, User


@pytest.mark.asyncio
async def test_oauth_app_config_prefers_db_over_env():
    row = SimpleNamespace(
        google_oauth_client_id="db-google-id",
        google_oauth_client_secret="db-google-secret",
        google_oauth_redirect_uri="http://db/google/callback",
        canva_client_id="db-canva-id",
        canva_client_secret="db-canva-secret",
        canva_redirect_uri="http://db/canva/callback",
        canva_template_proposal_en="tpl-pe",
        canva_template_proposal_ja="tpl-pj",
        canva_template_poc_en="tpl-ce",
        canva_template_poc_ja="tpl-cj",
    )
    db = AsyncMock()
    with (
        patch("app.admin.oauth_app_config._get_config_row", AsyncMock(return_value=row)),
        patch("app.admin.oauth_app_config.settings") as mock_settings,
    ):
        mock_settings.google_oauth_client_id = "env-google-id"
        mock_settings.google_oauth_client_secret = "env-google-secret"
        mock_settings.google_oauth_redirect_uri = "http://env/google"
        mock_settings.canva_client_id = "env-canva-id"
        mock_settings.canva_client_secret = "env-canva-secret"
        mock_settings.canva_redirect_uri = "http://env/canva"
        mock_settings.canva_template_proposal_en = ""
        mock_settings.canva_template_proposal_ja = ""
        mock_settings.canva_template_poc_en = ""
        mock_settings.canva_template_poc_ja = ""
        config = await get_oauth_app_config(db)

    assert config.google_oauth_client_id == "db-google-id"
    assert config.google_oauth_client_secret == "db-google-secret"
    assert config.canva_client_id == "db-canva-id"
    assert google_app_configured(config)
    assert canva_app_configured(config)


@pytest.mark.asyncio
async def test_oauth_app_config_falls_back_to_env_when_db_empty():
    row = SimpleNamespace(
        google_oauth_client_id=None,
        google_oauth_client_secret=None,
        google_oauth_redirect_uri=None,
        canva_client_id="",
        canva_client_secret="",
        canva_redirect_uri="",
        canva_template_proposal_en=None,
        canva_template_proposal_ja=None,
        canva_template_poc_en=None,
        canva_template_poc_ja=None,
    )
    db = AsyncMock()
    with (
        patch("app.admin.oauth_app_config._get_config_row", AsyncMock(return_value=row)),
        patch("app.admin.oauth_app_config.settings") as mock_settings,
    ):
        mock_settings.google_oauth_client_id = "env-google-id"
        mock_settings.google_oauth_client_secret = "env-google-secret"
        mock_settings.google_oauth_redirect_uri = "http://env/google"
        mock_settings.canva_client_id = ""
        mock_settings.canva_client_secret = ""
        mock_settings.canva_redirect_uri = ""
        mock_settings.canva_template_proposal_en = ""
        mock_settings.canva_template_proposal_ja = ""
        mock_settings.canva_template_poc_en = ""
        mock_settings.canva_template_poc_ja = ""
        config = await get_oauth_app_config(db)

    assert config.google_oauth_client_id == "env-google-id"
    assert google_app_configured(config)
    assert not canva_app_configured(config)


@pytest.mark.asyncio
async def test_change_password_rejects_contact():
    from app.auth import router as auth_router

    user = User(
        id=uuid.uuid4(),
        email="c@example.com",
        display_name="Contact",
        account_type=ACCOUNT_TYPE_CONTACT,
        password_hash=None,
    )
    db = AsyncMock()
    body = auth_router.ChangePasswordRequest(
        current_password="oldpassword",
        new_password="newpassword1",
    )
    with pytest.raises(AppError) as exc:
        await auth_router.change_password(body, db, user)
    assert exc.value.code == "PASSWORD_CHANGE_FORBIDDEN"


@pytest.mark.asyncio
async def test_change_password_rejects_wrong_current():
    from app.auth import router as auth_router
    from app.auth.service import hash_password

    user = User(
        id=uuid.uuid4(),
        email="u@example.com",
        display_name="User",
        account_type=ACCOUNT_TYPE_FULL,
        password_hash=hash_password("correct-password"),
    )
    db = AsyncMock()
    body = auth_router.ChangePasswordRequest(
        current_password="wrong-password",
        new_password="newpassword1",
    )
    with pytest.raises(AppError) as exc:
        await auth_router.change_password(body, db, user)
    assert exc.value.code == "PASSWORD_INCORRECT"


@pytest.mark.asyncio
async def test_change_password_happy_path():
    from app.auth import router as auth_router
    from app.auth.service import hash_password, verify_password

    user = User(
        id=uuid.uuid4(),
        email="u@example.com",
        display_name="User",
        account_type=ACCOUNT_TYPE_FULL,
        password_hash=hash_password("correct-password"),
    )
    db = AsyncMock()
    body = auth_router.ChangePasswordRequest(
        current_password="correct-password",
        new_password="newpassword1",
    )
    await auth_router.change_password(body, db, user)
    assert verify_password("newpassword1", user.password_hash)
    db.commit.assert_awaited()
