import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.feedback import ActualsResponse


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


class FeatureItemInput(BaseModel):
    id: uuid.UUID | None = None
    sort_order: int = 0
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    hours: float = Field(gt=0)
    phase: str = Field(min_length=1, max_length=50)
    role: str = Field(min_length=1, max_length=50)
    is_ai_generated: bool = False


class FeatureItemsUpdate(BaseModel):
    items: list[FeatureItemInput]


class ExtractedDataUpdate(BaseModel):
    functional_requirements: list[str] | None = None
    non_functional_requirements: list[str] | None = None
    user_roles: list[str] | None = None
    modules: list[str] | None = None
    external_systems: list[str] | None = None
    risks: list[str] | None = None
    gaps: list[str] | None = None
    confidence_notes: str | None = None


class EstimateStatusResponse(BaseModel):
    status: str
    extraction_progress: dict[str, Any] | None = None


class EstimateDetail(EstimateSummary):
    form_data: dict[str, Any]
    extracted_data: dict[str, Any] | None
    maintenance_assumptions: dict[str, Any]
    calculation_result: dict[str, Any] | None
    rate_card_version_id: uuid.UUID | None
    feature_items: list[FeatureItemResponse]
    documents: list[EstimateDocumentResponse]
    actuals: ActualsResponse | None = None


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    estimate_id: uuid.UUID
    user_id: uuid.UUID
    action: str
    changes: dict[str, Any]
    created_at: datetime
