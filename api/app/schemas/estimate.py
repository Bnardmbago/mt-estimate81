import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.ai.constants import MAX_AI_USER_PROMPT_CHARS
from app.schemas.feedback import ActualsResponse


class EstimateCreate(BaseModel):
    project_name: str = Field(min_length=1, max_length=255)
    client_name: str | None = Field(default=None, max_length=255)
    locale: str = Field(default="ja", pattern=r"^(ja|en)$")
    form_data: dict[str, Any] = Field(default_factory=dict)
    form_template_id: uuid.UUID | None = None


class EstimateUpdate(BaseModel):
    project_name: str | None = Field(default=None, min_length=1, max_length=255)
    client_name: str | None = Field(default=None, min_length=1, max_length=255)
    locale: str | None = Field(default=None, pattern=r"^(ja|en)$")
    form_data: dict[str, Any] | None = None
    form_template_id: uuid.UUID | None = None
    project_start_date: date | None = None
    rate_card_id: uuid.UUID | None = None
    theme_id: str | None = Field(default=None, max_length=64)
    style_id: str | None = Field(default=None, max_length=64)
    template_id: str | None = Field(default=None, max_length=64)
    cover_values: dict[str, Any] | None = None


class CalculateEstimateRequest(BaseModel):
    project_start_date: date | None = None


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


class NrcRcLineItemInput(BaseModel):
    name: str = Field(min_length=1)
    amount: int = Field(default=0, ge=0)
    category: str | None = None
    service_description: str | None = None


class NrcRcAssumptionsUpdate(BaseModel):
    setup_cost_items: list[NrcRcLineItemInput] = Field(default_factory=list)
    monthly_rc_items: list[NrcRcLineItemInput] = Field(default_factory=list)
    complexity_level: Literal["low", "medium", "high"] | None = None


class EstimateStatusResponse(BaseModel):
    status: str
    extraction_progress: dict[str, Any] | None = None
    extraction_error: str | None = None
    constraint_confirmation: dict[str, Any] | None = None


class ConstraintConfirmationRequest(BaseModel):
    decision: Literal["stop", "continue"]


class EstimateDetail(EstimateSummary):
    form_data: dict[str, Any]
    form_template_id: uuid.UUID | None = None
    form_template_name: str | None = None
    form_schema_snapshot: list[dict[str, Any]] = Field(default_factory=list)
    extracted_data: dict[str, Any] | None
    maintenance_assumptions: dict[str, Any]
    nrc_rc_assumptions: dict[str, Any] = Field(default_factory=dict)
    calculation_result: dict[str, Any] | None
    rate_card_id: uuid.UUID | None
    rate_card_name: str | None = None
    rate_card_version_id: uuid.UUID | None
    rate_card_stale: bool = False
    complexity_profile: dict[str, Any] | None = None
    rate_card_auto_tuned: bool = False
    rate_card_tune_recommended: bool = False
    rate_card_auto_tune_enabled: bool = True
    project_start_date: date | None
    theme_id: str | None = None
    style_id: str | None = None
    template_id: str | None = None
    cover_values: dict[str, Any] = Field(default_factory=dict)
    feature_items: list[FeatureItemResponse]
    documents: list[EstimateDocumentResponse]
    actuals: ActualsResponse | None = None


class GanttTimelineResponse(BaseModel):
    gantt: dict[str, Any]


class GenerateRateCardResponse(BaseModel):
    name: str
    settings: dict[str, Any]
    generation_notes: str
    used_defaults: bool
    default_fields: list[str]


class CreateEstimateRateCardRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    settings: dict[str, Any]
    activate: bool = True


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    estimate_id: uuid.UUID
    user_id: uuid.UUID
    action: str
    changes: dict[str, Any]
    created_at: datetime


class EstimateAiSuggestFormRequest(BaseModel):
    prompt: str = Field(default="", max_length=MAX_AI_USER_PROMPT_CHARS)
    locale: Literal["ja", "en"] | None = None

    @field_validator("prompt")
    @classmethod
    def normalize_prompt(cls, value: str) -> str:
        return value.strip()


class EstimateAiSuggestFormResponse(BaseModel):
    form_data: dict[str, str]
    generation_notes: str = ""
