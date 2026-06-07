import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EstimateCreate(BaseModel):
    project_name: str = Field(min_length=1, max_length=255)
    client_name: str = Field(min_length=1, max_length=255)
    locale: str = Field(default="ja", pattern=r"^(ja|en)$")
    form_data: dict[str, Any] = Field(default_factory=dict)


class EstimateUpdate(BaseModel):
    project_name: str | None = Field(default=None, min_length=1, max_length=255)
    client_name: str | None = Field(default=None, min_length=1, max_length=255)
    locale: str | None = Field(default=None, pattern=r"^(ja|en)$")
    form_data: dict[str, Any] | None = None


class FeatureItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sort_order: int
    name: str
    description: str
    hours: float
    phase: str
    role: str
    is_ai_generated: bool
    created_at: datetime
    updated_at: datetime


class EstimateDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    file_type: str
    storage_path: str
    extracted_text: str | None
    extraction_status: str
    uploaded_at: datetime


class EstimateSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_name: str
    client_name: str
    status: str
    locale: str
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class EstimateDetail(EstimateSummary):
    form_data: dict[str, Any]
    extracted_data: dict[str, Any] | None
    calculation_result: dict[str, Any] | None
    rate_card_version_id: uuid.UUID | None
    feature_items: list[FeatureItemResponse]
    documents: list[EstimateDocumentResponse]


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    estimate_id: uuid.UUID
    user_id: uuid.UUID
    action: str
    changes: dict[str, Any]
    created_at: datetime
