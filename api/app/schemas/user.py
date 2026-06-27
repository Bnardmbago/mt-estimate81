import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

SUPPORTED_CURRENCIES = ("JPY", "USD", "PHP")
AccountType = Literal["full", "contact"]


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    company_name: str | None
    account_type: AccountType = "full"
    email_verified_at: datetime | None = None
    is_admin: bool
    is_active: bool
    preferred_locale: str
    preferred_currency: str
    created_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=1, max_length=255)
    company_name: str | None = Field(default=None, max_length=255)
    is_admin: bool = False
    is_active: bool = True
    preferred_locale: str = Field(default="ja", pattern="^(ja|en)$")
    preferred_currency: str = Field(default="JPY", pattern="^(JPY|USD|PHP)$")


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    company_name: str | None = Field(default=None, max_length=255)
    account_type: AccountType | None = None
    is_admin: bool | None = None
    is_active: bool | None = None
    preferred_locale: str | None = Field(default=None, pattern="^(ja|en)$")
    preferred_currency: str | None = Field(default=None, pattern="^(JPY|USD|PHP)$")
    password: str | None = Field(default=None, min_length=8)


class ResetPasswordRequest(BaseModel):
    password: str = Field(min_length=8)
