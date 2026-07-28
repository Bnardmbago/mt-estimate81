"""Canva Connect OAuth + design-from-template (autofill) client."""

from __future__ import annotations

import logging
import secrets
from urllib.parse import urlencode

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.oauth_app_config import OAuthAppConfig, canva_app_configured, get_oauth_app_config
from app.destinations import oauth_store
from app.exceptions import AppError
from app.models.oauth_connection import PROVIDER_CANVA, OAuthConnection
from app.models.user import User

logger = logging.getLogger(__name__)

CANVA_AUTH_URL = "https://www.canva.com/api/oauth/authorize"
CANVA_TOKEN_URL = "https://api.canva.com/rest/v1/oauth/token"
CANVA_API_BASE = "https://api.canva.com/rest/v1"

CANVA_SCOPES = " ".join(
    [
        "design:content:write",
        "design:meta:read",
        "folder:read",
    ]
)


def canva_configured(config: OAuthAppConfig) -> bool:
    return canva_app_configured(config)


def template_id_for(*, variant: str, locale: str, config: OAuthAppConfig) -> str:
    locale = (locale or "en").lower()
    if variant == "poc":
        tid = (
            config.canva_template_poc_ja if locale == "ja" else config.canva_template_poc_en
        )
    else:
        tid = (
            config.canva_template_proposal_ja
            if locale == "ja"
            else config.canva_template_proposal_en
        )
    if not tid:
        raise AppError(
            "Canva template id is not configured for this variant/locale",
            "CANVA_TEMPLATE_NOT_CONFIGURED",
            status_code=503,
        )
    return tid


def build_authorize_url(*, state: str, config: OAuthAppConfig) -> str:
    if not canva_configured(config):
        raise AppError(
            "Canva OAuth is not configured",
            "CANVA_NOT_CONFIGURED",
            status_code=503,
        )
    params = {
        "client_id": config.canva_client_id,
        "redirect_uri": config.canva_redirect_uri,
        "response_type": "code",
        "scope": CANVA_SCOPES,
        "state": state,
    }
    return f"{CANVA_AUTH_URL}?{urlencode(params)}"


def new_oauth_state(user_id: str) -> str:
    return f"{user_id}:{secrets.token_urlsafe(24)}"


async def exchange_code(code: str, *, config: OAuthAppConfig) -> dict:
    if not canva_configured(config):
        raise AppError(
            "Canva OAuth is not configured",
            "CANVA_NOT_CONFIGURED",
            status_code=503,
        )
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            CANVA_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": config.canva_redirect_uri,
                "client_id": config.canva_client_id,
                "client_secret": config.canva_client_secret,
            },
        )
    if response.status_code >= 400:
        logger.warning("Canva token exchange failed: %s", response.text)
        raise AppError(
            "Canva authorization failed",
            "CANVA_AUTH_FAILED",
            status_code=401,
        )
    return response.json()


async def refresh_access_token(
    conn: OAuthConnection, *, config: OAuthAppConfig
) -> OAuthConnection:
    if not conn.refresh_token:
        raise AppError(
            "Canva connection expired; reconnect required",
            "OAUTH_RECONNECT_REQUIRED",
            status_code=401,
        )
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            CANVA_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": conn.refresh_token,
                "client_id": config.canva_client_id,
                "client_secret": config.canva_client_secret,
            },
        )
    if response.status_code >= 400:
        raise AppError(
            "Canva token refresh failed; reconnect required",
            "OAUTH_RECONNECT_REQUIRED",
            status_code=401,
        )
    payload = response.json()
    conn.access_token = payload["access_token"]
    if payload.get("refresh_token"):
        conn.refresh_token = payload["refresh_token"]
    if payload.get("expires_in"):
        from datetime import datetime, timedelta

        conn.token_expires_at = datetime.utcnow() + timedelta(
            seconds=max(0, int(payload["expires_in"]) - 60)
        )
    return conn


async def ensure_access_token(db: AsyncSession, user: User) -> str:
    conn = await oauth_store.require_connection(db, user.id, PROVIDER_CANVA)
    if oauth_store.token_is_expired(conn):
        config = await get_oauth_app_config(db)
        await refresh_access_token(conn, config=config)
        await db.commit()
        await db.refresh(conn)
    return conn.access_token


async def create_design_from_template(
    *,
    access_token: str,
    template_id: str,
    title: str,
    autofill_data: dict,
) -> tuple[str, str]:
    """Create a Canva design from a Brand template + autofill.

    Returns (design_id, edit_url).
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{CANVA_API_BASE}/autofills",
            headers=headers,
            json={
                "brand_template_id": template_id,
                "title": title,
                "data": _to_canva_autofill_fields(autofill_data),
            },
        )
        if response.status_code == 404:
            response = await client.post(
                f"{CANVA_API_BASE}/designs",
                headers=headers,
                json={
                    "design_type": {"type": "preset", "name": "presentation"},
                    "title": title,
                },
            )

    if response.status_code == 401:
        raise AppError(
            "Canva authorization expired; reconnect required",
            "OAUTH_RECONNECT_REQUIRED",
            status_code=401,
        )
    if response.status_code >= 400:
        logger.warning("Canva create failed: %s %s", response.status_code, response.text)
        raise AppError(
            "Failed to create Canva design",
            "CANVA_CREATE_FAILED",
            status_code=502,
        )

    data = response.json()
    job = data.get("job") or data
    design = job.get("design") or data.get("design") or data
    design_id = design.get("id") or job.get("id")
    urls = design.get("urls") or {}
    edit_url = urls.get("edit_url") or design.get("url") or data.get("url")
    if not design_id or not edit_url:
        raise AppError(
            "Canva create succeeded but design URL missing",
            "CANVA_CREATE_FAILED",
            status_code=502,
        )
    return design_id, edit_url


def _to_canva_autofill_fields(fields: dict) -> dict:
    result = {}
    for key, value in fields.items():
        if value is None:
            continue
        result[key] = {"type": "text", "text": str(value)}
    return result
