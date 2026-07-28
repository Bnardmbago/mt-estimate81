"""Google OAuth + Drive upload/convert for DOCX/XLSX."""

from __future__ import annotations

import json
import logging
import secrets
from urllib.parse import urlencode

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.oauth_app_config import OAuthAppConfig, get_oauth_app_config, google_app_configured
from app.destinations import oauth_store
from app.destinations.mime import (
    google_convert_mime_for_format,
    google_destination_label,
    google_source_mime_for_format,
)
from app.exceptions import AppError
from app.models.oauth_connection import PROVIDER_GOOGLE, OAuthConnection
from app.models.user import User

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_DRIVE_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"
GOOGLE_DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"

GOOGLE_SCOPES = " ".join(
    [
        "https://www.googleapis.com/auth/drive.file",
        "openid",
        "email",
    ]
)


def google_configured(config: OAuthAppConfig) -> bool:
    return google_app_configured(config)


def build_authorize_url(*, state: str, config: OAuthAppConfig) -> str:
    if not google_configured(config):
        raise AppError(
            "Google OAuth is not configured",
            "GOOGLE_NOT_CONFIGURED",
            status_code=503,
        )
    params = {
        "client_id": config.google_oauth_client_id,
        "redirect_uri": config.google_oauth_redirect_uri,
        "response_type": "code",
        "scope": GOOGLE_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def new_oauth_state(user_id: str) -> str:
    return f"{user_id}:{secrets.token_urlsafe(24)}"


async def exchange_code(code: str, *, config: OAuthAppConfig) -> dict:
    if not google_configured(config):
        raise AppError(
            "Google OAuth is not configured",
            "GOOGLE_NOT_CONFIGURED",
            status_code=503,
        )
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": config.google_oauth_client_id,
                "client_secret": config.google_oauth_client_secret,
                "redirect_uri": config.google_oauth_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    if response.status_code >= 400:
        logger.warning("Google token exchange failed: %s", response.text)
        raise AppError(
            "Google authorization failed",
            "GOOGLE_AUTH_FAILED",
            status_code=401,
        )
    return response.json()


async def refresh_access_token(
    conn: OAuthConnection, *, config: OAuthAppConfig
) -> OAuthConnection:
    if not conn.refresh_token:
        raise AppError(
            "Google connection expired; reconnect required",
            "OAUTH_RECONNECT_REQUIRED",
            status_code=401,
        )
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": config.google_oauth_client_id,
                "client_secret": config.google_oauth_client_secret,
                "refresh_token": conn.refresh_token,
                "grant_type": "refresh_token",
            },
        )
    if response.status_code >= 400:
        raise AppError(
            "Google token refresh failed; reconnect required",
            "OAUTH_RECONNECT_REQUIRED",
            status_code=401,
        )
    payload = response.json()
    conn.access_token = payload["access_token"]
    if payload.get("expires_in"):
        from datetime import datetime, timedelta

        conn.token_expires_at = datetime.utcnow() + timedelta(
            seconds=max(0, int(payload["expires_in"]) - 60)
        )
    return conn


async def ensure_access_token(db: AsyncSession, user: User) -> str:
    conn = await oauth_store.require_connection(db, user.id, PROVIDER_GOOGLE)
    if oauth_store.token_is_expired(conn):
        config = await get_oauth_app_config(db)
        await refresh_access_token(conn, config=config)
        await db.commit()
        await db.refresh(conn)
    return conn.access_token


async def upload_and_convert(
    *,
    access_token: str,
    filename: str,
    content: bytes,
    export_format: str,
) -> tuple[str, str, str]:
    """Upload bytes to Drive; convert DOCX/XLSX to Docs/Sheets.

    Returns (destination_label, file_id, web_view_link).
    """
    source_mime = google_source_mime_for_format(export_format)
    convert_mime = google_convert_mime_for_format(export_format)
    destination = google_destination_label(export_format)

    metadata: dict = {"name": filename}
    if convert_mime:
        metadata["mimeType"] = convert_mime

    boundary = f"boundary_{secrets.token_hex(8)}"
    meta_json = json.dumps(metadata)
    body = (
        f"--{boundary}\r\n"
        f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{meta_json}\r\n"
        f"--{boundary}\r\n"
        f"Content-Type: {source_mime}\r\n\r\n"
    ).encode("utf-8") + content + f"\r\n--{boundary}--\r\n".encode("utf-8")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": f"multipart/related; boundary={boundary}",
    }
    params = {"uploadType": "multipart", "fields": "id,webViewLink,mimeType"}

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            GOOGLE_DRIVE_UPLOAD_URL,
            params=params,
            headers=headers,
            content=body,
        )

    if response.status_code == 401:
        raise AppError(
            "Google authorization expired; reconnect required",
            "OAUTH_RECONNECT_REQUIRED",
            status_code=401,
        )
    if response.status_code >= 400:
        logger.warning("Drive upload failed: %s %s", response.status_code, response.text)
        raise AppError(
            "Failed to upload to Google Drive",
            "GOOGLE_UPLOAD_FAILED",
            status_code=502,
        )

    data = response.json()
    file_id = data.get("id")
    web_link = data.get("webViewLink")
    if not file_id or not web_link:
        async with httpx.AsyncClient(timeout=30.0) as client:
            meta = await client.get(
                f"{GOOGLE_DRIVE_FILES_URL}/{file_id}",
                params={"fields": "id,webViewLink"},
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if meta.status_code >= 400 or not meta.json().get("webViewLink"):
            raise AppError(
                "Google Drive upload succeeded but link missing",
                "GOOGLE_UPLOAD_FAILED",
                status_code=502,
            )
        web_link = meta.json()["webViewLink"]
        file_id = meta.json().get("id", file_id)

    return destination, file_id, web_link
