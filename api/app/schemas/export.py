import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ExportRequest(BaseModel):
    format: str = Field(pattern=r"^(md|xlsx|pdf)$")
    locale: str | None = Field(default=None, pattern=r"^(ja|en)$")


class ExportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    estimate_id: uuid.UUID
    format: str
    storage_path: str
    locale: str
    generated_at: datetime
    generated_by: uuid.UUID
