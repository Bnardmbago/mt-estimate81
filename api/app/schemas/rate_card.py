import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.calculation.development_approach import DevelopmentApproach
from app.calculation.schemas import RateCardSettings


class RateCardUpdate(BaseModel):
    settings: RateCardSettings
    name: str | None = Field(default=None, min_length=1, max_length=255)
    version_label: str | None = Field(default=None, min_length=1, max_length=255)


class RateCardVersionLabelUpdate(BaseModel):
    label: str = Field(min_length=1, max_length=255)


class RateCardVersionUpdate(BaseModel):
    settings: RateCardSettings
    label: str | None = Field(default=None, min_length=1, max_length=255)
    name: str | None = Field(default=None, min_length=1, max_length=255)


class RateCardVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rate_card_id: uuid.UUID
    version_number: int
    label: str | None
    settings: dict
    created_at: datetime
    estimate_count: int = 0


class RateCardVersionOption(BaseModel):
    id: uuid.UUID
    version_number: int
    label: str | None
    rate_card_name: str


class RateCardOption(BaseModel):
    id: uuid.UUID
    name: str
    is_active: bool
    development_approach: DevelopmentApproach


class ActiveRateCardResponse(BaseModel):
    id: uuid.UUID
    name: str
    is_active: bool
    version_number: int
    version_id: uuid.UUID
    version_label: str | None
    settings: dict
    created_at: datetime
    estimate_count: int = 0
    is_locked: bool = False
    duplicated_from_name: str | None = None


class RateCardSummary(BaseModel):
    id: uuid.UUID
    name: str
    is_active: bool
    development_approach: DevelopmentApproach
    version_count: int
    latest_version_number: int
    created_at: datetime
    estimate_count: int = 0
    is_locked: bool = False
    duplicated_from_name: str | None = None


class RateCardCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    activate: bool = True
    development_approach: DevelopmentApproach


class RateCardDuplicate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class RateCardEstimateUsage(BaseModel):
    estimate_id: uuid.UUID
    project_name: str
    client_name: str
    status: str
    updated_at: datetime


RateCardAiSection = Literal["roles", "phases", "setup_cost_items", "monthly_rc_items"]


class RateCardAiSuggestRequest(BaseModel):
    estimate_id: uuid.UUID | None = None
    section: RateCardAiSection
    prompt: str = Field(min_length=1, max_length=2000)
    locale: Literal["ja", "en"] | None = None

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Prompt is required")
        return trimmed


class RateCardAiSuggestResponse(BaseModel):
    section: RateCardAiSection
    items: list[dict]
    generation_notes: str
    replace_all: bool = False
    estimate: RateCardEstimateUsage | None = None
