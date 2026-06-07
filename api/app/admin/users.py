import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import hash_password
from app.dependencies import get_db, require_admin
from app.models.user import User
from app.schemas.user import ResetPasswordRequest, UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/admin/users", tags=["admin"])


@router.get("", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return list(result.scalars().all())


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail={"error": "Email already registered", "code": "USER_EXISTS"},
        )

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
        is_admin=body.is_admin,
        preferred_locale=body.preferred_locale,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=404,
            detail={"error": "User not found", "code": "USER_NOT_FOUND"},
        )

    if body.is_admin is not None:
        user.is_admin = body.is_admin
    if body.preferred_locale is not None:
        user.preferred_locale = body.preferred_locale

    await db.commit()
    await db.refresh(user)
    return user


@router.put("/{user_id}/reset-password", response_model=UserResponse)
async def reset_password(
    user_id: uuid.UUID,
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=404,
            detail={"error": "User not found", "code": "USER_NOT_FOUND"},
        )

    user.password_hash = hash_password(body.password)
    await db.commit()
    await db.refresh(user)
    return user
