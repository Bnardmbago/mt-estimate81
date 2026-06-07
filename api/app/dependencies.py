import uuid

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import decode_access_token
from app.database import get_db as _get_db
from app.models.user import User

get_db = _get_db

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    token = None
    if credentials:
        token = credentials.credentials
    elif cookie_token := request.cookies.get("access_token"):
        token = cookie_token

    if not token:
        raise HTTPException(
            status_code=401,
            detail={"error": "Not authenticated", "code": "AUTH_REQUIRED"},
        )

    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail={"error": "Invalid token", "code": "AUTH_INVALID"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail={"error": "Invalid token", "code": "AUTH_INVALID"},
        )

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=401,
            detail={"error": "User not found", "code": "AUTH_INVALID"},
        )
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail={"error": "Admin access required", "code": "ADMIN_REQUIRED"},
        )
    return user
