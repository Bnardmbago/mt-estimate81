from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class InternalDossierRateCard(BaseModel):
    rate_card_id: str | None = None
    name: str | None = None
    version_number: int | None = None
    effective_date: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)


class InternalDossierProposal(BaseModel):
    id: str
    locale: str
    status: str
    include_poc: bool
    assessment: dict[str, Any] | None = None
    proposal_body: dict[str, Any] | None = None
    poc: dict[str, Any] | None = None


class InternalDossierResponse(BaseModel):
    estimate_id: str
    project_name: str
    client_name: str
    status: str
    locale: str
    has_calculation: bool
    rate_card_stale: bool
    warnings: list[str] = Field(default_factory=list)
    report: dict[str, Any]
    rate_card: InternalDossierRateCard | None = None
    proposals: list[InternalDossierProposal] = Field(default_factory=list)
