from typing import Literal

from pydantic import BaseModel, Field, model_validator


class FeatureItemSuggestion(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    suggested_hours: float = Field(gt=0)
    phase: str
    role: str


class MaintenanceAssumptions(BaseModel):
    monthly_support_hours: float = Field(ge=0, default=0)
    notes: str = ""


class CostDriverSuggestion(BaseModel):
    name: str = Field(min_length=1)
    impact_jpy: int


class GeneratedRoleRate(BaseModel):
    name: str = Field(min_length=1)
    hourly_rate_jpy: int = Field(ge=0)


class GeneratedPhasePercentage(BaseModel):
    name: str = Field(min_length=1)
    percentage: float = Field(ge=0, le=1)


class GeneratedLineItem(BaseModel):
    name: str = Field(min_length=1)
    amount_jpy: int = Field(ge=0)
    service_description: str | None = None


class GeneratedProductivity(BaseModel):
    hours_per_feature_default: int = Field(ge=1)


class RateCardRolesSectionSuggestion(BaseModel):
    items: list[GeneratedRoleRate]
    generation_notes: str = ""


class RateCardPhasesSectionSuggestion(BaseModel):
    items: list[GeneratedPhasePercentage]
    generation_notes: str = ""
    replace_all: bool = False


class RateCardLineItemsSectionSuggestion(BaseModel):
    items: list[GeneratedLineItem]
    generation_notes: str = ""


class GeneratedRateCardSuggestion(BaseModel):
    development_approach: Literal["traditional", "ai_assisted", "hybrid", "low_code"]
    roles: list[GeneratedRoleRate]
    phases: list[GeneratedPhasePercentage]
    contingency_rate: float = Field(ge=0, le=1)
    overhead_rate: float = Field(ge=0, le=1)
    tax_rate: float = Field(ge=0, le=1)
    productivity: GeneratedProductivity
    setup_cost_items: list[GeneratedLineItem]
    monthly_rc_items: list[GeneratedLineItem]
    generation_notes: str = ""
    used_default_assumptions: list[str] = Field(default_factory=list)


class ExtractedRequirements(BaseModel):
    functional_requirements: list[str]
    non_functional_requirements: list[str]
    user_roles: list[str]
    modules: list[str]
    external_systems: list[str]
    risks: list[str]
    gaps: list[str]
    confidence_notes: str
    feature_items: list[FeatureItemSuggestion]
    maintenance_assumptions: MaintenanceAssumptions
    confidence_score: float = Field(default=50.0, ge=0, le=100)
    accuracy_level: Literal["high", "medium", "low"] = "medium"
    confidence_factors: list[str] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    estimation_warnings: list[str] = Field(default_factory=list)
    assumption_risks: list[str] = Field(default_factory=list)
    estimate_exclusions: list[str] = Field(default_factory=list)
    estimate_type: str = ""
    cost_drivers: list[CostDriverSuggestion] = Field(default_factory=list)

    @model_validator(mode="after")
    def align_accuracy_with_score(self) -> "ExtractedRequirements":
        self.accuracy_level = accuracy_level_from_score(self.confidence_score)
        return self


def accuracy_level_from_score(score: float) -> Literal["high", "medium", "low"]:
    if score >= 80:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


class EstimateFormFieldsSuggestion(BaseModel):
    form_data: dict[str, str] = Field(default_factory=dict)
    generation_notes: str = ""

    @model_validator(mode="before")
    @classmethod
    def coerce_form_data_values(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        form_data = data.get("form_data")
        if not isinstance(form_data, dict):
            return data
        coerced = dict(data)
        coerced["form_data"] = {
            key: "" if value is None else str(value)
            for key, value in form_data.items()
        }
        return coerced
