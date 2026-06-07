import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    is_admin: bool
    preferred_locale: str
    created_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=1, max_length=255)
    is_admin: bool = False
    preferred_locale: str = Field(default="ja", pattern="^(ja|en)$")


class UserUpdate(BaseModel):
    is_admin: bool | None = None
    preferred_locale: str | None = Field(default=None, pattern="^(ja|en)$")


class ResetPasswordRequest(BaseModel):
    password: str = Field(min_length=8)
