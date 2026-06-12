import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ExportRequest(BaseModel):
    format: str = Field(pattern=r"^(md|xlsx|pdf)$")
    locale: str | None = Field(default=None, pattern=r"^(ja|en)$")


class ExportEmailRequest(BaseModel):
    to_email: EmailStr
    export_ids: list[uuid.UUID] = Field(min_length=1, max_length=10)
    message: str | None = Field(default=None, max_length=2000)


class ExportEmailResponse(BaseModel):
    to_email: str
    export_ids: list[uuid.UUID]
    sent_at: datetime


class ExportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    estimate_id: uuid.UUID
    format: str
    storage_path: str
    locale: str
    generated_at: datetime
    generated_by: uuid.UUID
