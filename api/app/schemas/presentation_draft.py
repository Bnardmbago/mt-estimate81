from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class PresentationDraftCreate(BaseModel):
    source_locale: Literal["en", "ja"] = "en"
    target_theme_id: str | None = Field(default=None, max_length=64)
    target_style_id: str | None = Field(default=None, max_length=64)
    target_template_id: str | None = Field(default=None, max_length=64)


class PresentationDraftUpdate(BaseModel):
    theme_draft: dict[str, Any] | None = None
    style_draft: dict[str, Any] | None = None
    template_draft: dict[str, Any] | None = None


class PresentationDraftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    source_locale: str
    theme_draft: dict[str, Any] = Field(default_factory=dict)
    style_draft: dict[str, Any] = Field(default_factory=dict)
    template_draft: dict[str, Any] = Field(default_factory=dict)
    target_theme_id: str | None = None
    target_style_id: str | None = None
    target_template_id: str | None = None
    generation_meta: dict[str, Any] = Field(default_factory=dict)
    errors: list[Any] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    expires_at: datetime


class PresentationConsistencySuggestion(BaseModel):
    id: str
    target: Literal["theme", "style"]
    field_path: str
    before: Any = None
    after: Any = None
    confidence: float = Field(ge=0, le=1)
    rationale: str


class PresentationConsistencyResponse(BaseModel):
    suggestions: list[PresentationConsistencySuggestion] = Field(default_factory=list)


class PresentationApplySuggestions(BaseModel):
    suggestion_ids: list[str] | None = None


class PresentationDraftApprove(BaseModel):
    source_locale: Literal["en", "ja"] | None = None


class PresentationDraftApprovalResult(BaseModel):
    theme_id: str
    style_id: str
    template_id: str


class PresentationDraftAsset(BaseModel):
    id: str
    storage_path: str
    filename: str
    content_type: str | None = None
    size_bytes: int
