import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ActualsInput(BaseModel):
    actual_effort_hours: float = Field(gt=0)
    actual_duration_days: float = Field(gt=0)
    actual_nrc_jpy: int = Field(ge=0)
    actual_rc_monthly_jpy: int = Field(ge=0)
    variance_notes: str | None = None


class ActualsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    estimate_id: uuid.UUID
    actual_effort_hours: float
    actual_duration_days: float
    actual_nrc_jpy: int
    actual_rc_monthly_jpy: int
    variance_notes: str | None
    entered_by: uuid.UUID
    entered_at: datetime


class VarianceMetric(BaseModel):
    estimated: float | int
    actual: float | int
    variance_pct: float
    severity: str


class VarianceSummary(BaseModel):
    effort_hours: VarianceMetric
    effort_days: VarianceMetric
    nrc_jpy: VarianceMetric
    rc_monthly_jpy: VarianceMetric


class VarianceDashboardRow(BaseModel):
    estimate_id: uuid.UUID
    project_name: str
    client_name: str
    completed_at: datetime
    actuals_entered_at: datetime | None
    variance: VarianceSummary | None
    variance_notes: str | None


class CompleteResponse(BaseModel):
    id: uuid.UUID
    status: str
    variance: VarianceSummary | None = None


class ActualsWithVariance(BaseModel):
    actuals: ActualsResponse
    variance: VarianceSummary | None = None


class EstimateDetailWithActuals(BaseModel):
    """Extended detail returned after complete/actuals operations."""

    id: uuid.UUID
    status: str
    actuals: ActualsResponse | None = None
    variance: dict[str, Any] | None = None
