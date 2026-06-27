import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import hash_password
from app.dependencies import get_current_user, get_db, require_admin
from app.models.user import ACCOUNT_TYPE_CONTACT, ACCOUNT_TYPE_FULL, User
from app.schemas.user import ResetPasswordRequest, UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/admin/users", tags=["admin"])


def _normalize_company_name(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


async def _get_user_or_404(db: AsyncSession, user_id: uuid.UUID) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=404,
            detail={"error": "User not found", "code": "USER_NOT_FOUND"},
        )
    return user


async def _count_active_admins(db: AsyncSession, exclude_user_id: uuid.UUID | None = None) -> int:
    query = select(func.count()).select_from(User).where(
        User.is_admin.is_(True),
        User.is_active.is_(True),
    )
    if exclude_user_id is not None:
        query = query.where(User.id != exclude_user_id)
    result = await db.execute(query)
    return int(result.scalar_one())


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
        company_name=_normalize_company_name(body.company_name),
        is_admin=body.is_admin,
        is_active=body.is_active,
        preferred_locale=body.preferred_locale,
        preferred_currency=body.preferred_currency,
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
    current_user: User = Depends(require_admin),
):
    user = await _get_user_or_404(db, user_id)
    update_data = body.model_dump(exclude_unset=True)

    if "email" in update_data and update_data["email"] != user.email:
        existing = await db.execute(select(User).where(User.email == update_data["email"]))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail={"error": "Email already registered", "code": "USER_EXISTS"},
            )
        user.email = update_data["email"]

    if "display_name" in update_data:
        user.display_name = update_data["display_name"]
    if "company_name" in update_data:
        user.company_name = _normalize_company_name(update_data["company_name"])
    if "is_admin" in update_data:
        if user.id == current_user.id and update_data["is_admin"] is False:
            raise HTTPException(
                status_code=400,
                detail={"error": "You cannot remove your own admin access", "code": "SELF_DEMOTE"},
            )
        if user.is_admin and update_data["is_admin"] is False:
            remaining_admins = await _count_active_admins(db, exclude_user_id=user.id)
            if remaining_admins == 0:
                raise HTTPException(
                    status_code=400,
                    detail={"error": "At least one active admin is required", "code": "LAST_ADMIN"},
                )
        user.is_admin = update_data["is_admin"]
    if "is_active" in update_data:
        if user.id == current_user.id and update_data["is_active"] is False:
            raise HTTPException(
                status_code=400,
                detail={"error": "You cannot disable your own account", "code": "SELF_DISABLE"},
            )
        if user.is_admin and update_data["is_active"] is False:
            remaining_admins = await _count_active_admins(db, exclude_user_id=user.id)
            if remaining_admins == 0:
                raise HTTPException(
                    status_code=400,
                    detail={"error": "At least one active admin is required", "code": "LAST_ADMIN"},
                )
        user.is_active = update_data["is_active"]
    if "preferred_locale" in update_data:
        user.preferred_locale = update_data["preferred_locale"]
    if "preferred_currency" in update_data:
        user.preferred_currency = update_data["preferred_currency"]

    password = update_data.pop("password", None)

    if "account_type" in update_data:
        new_type = update_data["account_type"]
        if new_type not in (ACCOUNT_TYPE_FULL, ACCOUNT_TYPE_CONTACT):
            raise HTTPException(
                status_code=400,
                detail={"error": "Invalid account type", "code": "INVALID_ACCOUNT_TYPE"},
            )
        if user.account_type == ACCOUNT_TYPE_CONTACT and new_type == ACCOUNT_TYPE_FULL:
            if not password:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Password is required when upgrading a contact account to full",
                        "code": "PASSWORD_REQUIRED",
                    },
                )
            user.password_hash = hash_password(password)
        user.account_type = new_type
    elif password:
        user.password_hash = hash_password(password)

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = await _get_user_or_404(db, user_id)

    if user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail={"error": "You cannot delete your own account", "code": "SELF_DELETE"},
        )

    if user.is_admin:
        remaining_admins = await _count_active_admins(db, exclude_user_id=user.id)
        if remaining_admins == 0:
            raise HTTPException(
                status_code=400,
                detail={"error": "At least one active admin is required", "code": "LAST_ADMIN"},
            )

    await db.delete(user)
    await db.commit()


@router.put("/{user_id}/reset-password", response_model=UserResponse)
async def reset_password(
    user_id: uuid.UUID,
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = await _get_user_or_404(db, user_id)
    user.password_hash = hash_password(body.password)
    await db.commit()
    await db.refresh(user)
    return user
