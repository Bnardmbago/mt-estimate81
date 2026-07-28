from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


ProposalLocale = Literal["ja", "en"]
ProposalPart = Literal["assessment", "proposal", "poc", "all"]
ProposalExportFormatLiteral = Literal["pdf", "docx", "md", "xlsx"]
ProposalExportVariantLiteral = Literal["full", "assessment", "proposal", "poc"]


class ProposalGenerateRequest(BaseModel):
    estimate_id: UUID
    locale: ProposalLocale = "en"
    include_poc: bool = False
    theme_id: str | None = Field(default=None, max_length=64)
    style_id: str | None = Field(default=None, max_length=64)
    template_id: str | None = Field(default=None, max_length=64)


class ProposalRegenerateRequest(BaseModel):
    part: ProposalPart = "all"


class ProposalPresentationPatch(BaseModel):
    theme_id: str | None = Field(default=None, max_length=64)
    style_id: str | None = Field(default=None, max_length=64)
    template_id: str | None = Field(default=None, max_length=64)


class ProposalCoverValuesPatch(BaseModel):
    locale: ProposalLocale
    values: dict[str, Any] = Field(default_factory=dict)


class ProposalSectionPatch(BaseModel):
    part: Literal["assessment", "proposal", "poc"]
    section_id: str
    body: str | None = None
    bullets: list[str] | None = None
    rating: str | None = None
    extra: dict[str, Any] | None = None


class ProposalSectionsPatchRequest(BaseModel):
    sections: list[ProposalSectionPatch] = Field(min_length=1)


class ProposalExportRequest(BaseModel):
    format: ProposalExportFormatLiteral
    variant: ProposalExportVariantLiteral = "full"
    locale: ProposalLocale | None = None
    project_name: str | None = Field(default=None, max_length=255)
    theme_id: str | None = Field(default=None, max_length=64)
    style_id: str | None = Field(default=None, max_length=64)
    template_id: str | None = Field(default=None, max_length=64)
    include_cover: bool | None = None
    cover_template_id: str | None = Field(default=None, max_length=64)
    cover_values: dict[str, Any] | None = None


class ProposalExportRecord(BaseModel):
    id: UUID
    format: str
    variant: str
    locale: str
    revision: int
    generated_at: datetime
    theme_id: str | None = None
    style_id: str | None = None
    template_id: str | None = None
    destination: str | None = None
    external_file_id: str | None = None
    external_url: str | None = None
    manually_edited_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProposalSummary(BaseModel):
    id: UUID
    estimate_id: UUID
    project_name: str = ""
    client_name: str = ""
    locale: str
    include_poc: bool
    status: str
    updated_at: datetime
    source_stale: bool = False
    theme_id: str | None = None
    style_id: str | None = None
    template_id: str | None = None

    model_config = {"from_attributes": True}


class ProposalStatusResponse(BaseModel):
    id: UUID
    status: str
    generation_meta: dict[str, Any] = Field(default_factory=dict)
    assessment_ready: bool = False
    proposal_ready: bool = False
    poc_ready: bool = False


class ProposalDetail(BaseModel):
    id: UUID
    estimate_id: UUID
    locale: str
    include_poc: bool
    status: str
    source_snapshot: dict[str, Any] = Field(default_factory=dict)
    assessment: dict[str, Any] | None = None
    proposal_body: dict[str, Any] | None = None
    poc: dict[str, Any] | None = None
    diagrams: list[dict[str, Any]] = Field(default_factory=list)
    milestones: list[dict[str, Any]] = Field(default_factory=list)
    generation_meta: dict[str, Any] = Field(default_factory=dict)
    source_fingerprint: str = ""
    source_stale: bool = False
    theme_id: str | None = None
    style_id: str | None = None
    template_id: str | None = None
    theme_name: str | None = None
    style_name: str | None = None
    template_name: str | None = None
    presentation_meta: dict[str, Any] = Field(default_factory=dict)
    presentation_css_vars: dict[str, str] = Field(default_factory=dict)
    presentation_layout_class: str = "proposal-layout-linear"
    cover_values: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    finalized_at: datetime | None = None
    exports: list[ProposalExportRecord] = Field(default_factory=list)

    model_config = {"from_attributes": True}
