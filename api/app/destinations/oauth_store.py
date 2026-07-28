"""Persist and refresh OAuth connections for export destinations."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import AppError
from app.models.oauth_connection import OAuthConnection


async def get_connection(
    db: AsyncSession,
    user_id: uuid.UUID,
    provider: str,
) -> OAuthConnection | None:
    result = await db.execute(
        select(OAuthConnection).where(
            OAuthConnection.user_id == user_id,
            OAuthConnection.provider == provider,
        )
    )
    return result.scalar_one_or_none()


async def require_connection(
    db: AsyncSession,
    user_id: uuid.UUID,
    provider: str,
) -> OAuthConnection:
    conn = await get_connection(db, user_id, provider)
    if not conn:
        raise AppError(
            f"{provider.title()} account not connected",
            "OAUTH_NOT_CONNECTED",
            status_code=401,
        )
    return conn


async def upsert_connection(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    provider: str,
    access_token: str,
    refresh_token: str | None,
    expires_in: int | None,
    scopes: str | None = None,
) -> OAuthConnection:
    conn = await get_connection(db, user_id, provider)
    expires_at = None
    if expires_in is not None:
        expires_at = datetime.utcnow() + timedelta(seconds=max(0, expires_in - 60))

    if conn is None:
        conn = OAuthConnection(
            user_id=user_id,
            provider=provider,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=expires_at,
            scopes=scopes,
        )
        db.add(conn)
    else:
        conn.access_token = access_token
        if refresh_token:
            conn.refresh_token = refresh_token
        conn.token_expires_at = expires_at
        if scopes is not None:
            conn.scopes = scopes
        conn.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(conn)
    return conn


async def delete_connection(
    db: AsyncSession,
    user_id: uuid.UUID,
    provider: str,
) -> None:
    conn = await get_connection(db, user_id, provider)
    if conn:
        await db.delete(conn)
        await db.commit()


def token_is_expired(conn: OAuthConnection) -> bool:
    if conn.token_expires_at is None:
        return False
    return conn.token_expires_at <= datetime.utcnow()
