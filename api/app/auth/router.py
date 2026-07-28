from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import contact as contact_service
from app.auth.service import create_access_token, hash_password, verify_password
from app.database import get_db
from app.dependencies import get_current_user
from app.exceptions import AppError
from app.models.user import ACCOUNT_TYPE_CONTACT, User
from app.schemas.user import UserResponse
from app.users.access import is_contact_user

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    user: dict


class ContactRequestLinkBody(BaseModel):
    email: EmailStr
    display_name: str = Field(default="", max_length=255)
    company_name: str = Field(default="", max_length=255)
    locale: str = Field(default="ja", pattern="^(ja|en)$")
    captcha_token: str = Field(min_length=1)


class ContactVerifyBody(BaseModel):
    token: str = Field(min_length=1)


class ContactVerifyResponse(BaseModel):
    access_token: str
    estimate_id: str
    user: dict


class ProfileUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    company_name: str | None = Field(default=None, max_length=255)
    preferred_locale: str | None = Field(default=None, pattern="^(ja|en)$")


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)

@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=401,
            detail={"error": "Invalid credentials", "code": "AUTH_INVALID"},
        )
    if user.account_type == ACCOUNT_TYPE_CONTACT and not user.password_hash:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Contact accounts must use the magic link from the contact page",
                "code": "CONTACT_USE_MAGIC_LINK",
            },
        )
    if not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail={"error": "Invalid credentials", "code": "AUTH_INVALID"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail={"error": "Account is disabled", "code": "USER_DISABLED"},
        )

    token = create_access_token(
        {
            "sub": str(user.id),
            "is_admin": user.is_admin,
            "account_type": user.account_type,
        }
    )
    return LoginResponse(
        access_token=token,
        user={
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "account_type": user.account_type,
            "is_admin": user.is_admin,
            "is_active": user.is_active,
            "preferred_locale": user.preferred_locale,
            "preferred_currency": user.preferred_currency,
        },
    )


@router.post("/contact/request-link", status_code=204)
async def contact_request_link(
    body: ContactRequestLinkBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host if request.client else None
    await contact_service.request_magic_link(
        db,
        email=body.email,
        display_name=body.display_name,
        company_name=body.company_name,
        locale=body.locale,
        request_ip=client_ip,
        captcha_token=body.captcha_token,
        request=request,
    )


@router.post("/contact/verify", response_model=ContactVerifyResponse)
async def contact_verify(
    body: ContactVerifyBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host if request.client else None
    return await contact_service.verify_magic_link(
        db,
        token=body.token,
        request_ip=client_ip,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserResponse)
async def update_current_user_profile(
    body: ProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if body.display_name is not None:
        user.display_name = body.display_name.strip()
    if body.company_name is not None:
        stripped = body.company_name.strip()
        user.company_name = stripped or None
    if body.preferred_locale is not None:
        user.preferred_locale = body.preferred_locale
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/change-password", status_code=204)
async def change_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if is_contact_user(user) or not user.password_hash:
        raise AppError(
            "Password change is not available for this account",
            "PASSWORD_CHANGE_FORBIDDEN",
            status_code=403,
        )
    if not verify_password(body.current_password, user.password_hash):
        raise AppError(
            "Current password is incorrect",
            "PASSWORD_INCORRECT",
            status_code=400,
        )
    user.password_hash = hash_password(body.new_password)
    await db.commit()
