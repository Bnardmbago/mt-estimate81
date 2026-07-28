"""OAuth connect/disconnect for Google and Canva export destinations."""

from __future__ import annotations

import uuid
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.oauth_app_config import get_oauth_app_config
from app.config import settings
from app.dependencies import get_db, require_full_account
from app.destinations import canva as canva_client
from app.destinations import google as google_client
from app.destinations import oauth_store
from app.exceptions import AppError
from app.models.oauth_connection import PROVIDER_CANVA, PROVIDER_GOOGLE
from app.models.user import User

router = APIRouter(prefix="/integrations", tags=["integrations"])


class ConnectionStatus(BaseModel):
    provider: str
    connected: bool
    configured: bool


@router.get("/status", response_model=list[ConnectionStatus])
async def integration_status(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
):
    config = await get_oauth_app_config(db)
    google_conn = await oauth_store.get_connection(db, user.id, PROVIDER_GOOGLE)
    canva_conn = await oauth_store.get_connection(db, user.id, PROVIDER_CANVA)
    return [
        ConnectionStatus(
            provider="google",
            connected=google_conn is not None,
            configured=google_client.google_configured(config),
        ),
        ConnectionStatus(
            provider="canva",
            connected=canva_conn is not None,
            configured=canva_client.canva_configured(config),
        ),
    ]


@router.get("/google/connect")
async def google_connect(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
):
    config = await get_oauth_app_config(db)
    state = google_client.new_oauth_state(str(user.id))
    url = google_client.build_authorize_url(state=state, config=config)
    return {"authorize_url": url, "state": state}


@router.get("/google/callback")
async def google_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    if error:
        return _redirect_settings(ok=False, provider="google", reason=error)
    if not code or not state or ":" not in state:
        raise AppError("Invalid OAuth callback", "OAUTH_CALLBACK_INVALID", status_code=400)

    user_id_str, _nonce = state.split(":", 1)
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError as exc:
        raise AppError("Invalid OAuth state", "OAUTH_CALLBACK_INVALID", status_code=400) from exc

    config = await get_oauth_app_config(db)
    tokens = await google_client.exchange_code(code, config=config)
    await oauth_store.upsert_connection(
        db,
        user_id=user_id,
        provider=PROVIDER_GOOGLE,
        access_token=tokens["access_token"],
        refresh_token=tokens.get("refresh_token"),
        expires_in=tokens.get("expires_in"),
        scopes=tokens.get("scope"),
    )
    return _redirect_settings(ok=True, provider="google")


@router.delete("/google", status_code=204)
async def google_disconnect(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
):
    await oauth_store.delete_connection(db, user.id, PROVIDER_GOOGLE)


@router.get("/canva/connect")
async def canva_connect(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
):
    config = await get_oauth_app_config(db)
    state = canva_client.new_oauth_state(str(user.id))
    url = canva_client.build_authorize_url(state=state, config=config)
    return {"authorize_url": url, "state": state}


@router.get("/canva/callback")
async def canva_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    if error:
        return _redirect_settings(ok=False, provider="canva", reason=error)
    if not code or not state or ":" not in state:
        raise AppError("Invalid OAuth callback", "OAUTH_CALLBACK_INVALID", status_code=400)

    user_id_str, _nonce = state.split(":", 1)
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError as exc:
        raise AppError("Invalid OAuth state", "OAUTH_CALLBACK_INVALID", status_code=400) from exc

    config = await get_oauth_app_config(db)
    tokens = await canva_client.exchange_code(code, config=config)
    await oauth_store.upsert_connection(
        db,
        user_id=user_id,
        provider=PROVIDER_CANVA,
        access_token=tokens["access_token"],
        refresh_token=tokens.get("refresh_token"),
        expires_in=tokens.get("expires_in"),
        scopes=tokens.get("scope"),
    )
    return _redirect_settings(ok=True, provider="canva")


@router.delete("/canva", status_code=204)
async def canva_disconnect(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
):
    await oauth_store.delete_connection(db, user.id, PROVIDER_CANVA)


def _redirect_settings(*, ok: bool, provider: str, reason: str | None = None) -> RedirectResponse:
    params = {"oauth": "ok" if ok else "error", "provider": provider}
    if reason:
        params["reason"] = reason
    return RedirectResponse(
        url=f"{settings.web_base_url}/{settings.default_locale}/settings?{urlencode(params)}",
        status_code=302,
    )
