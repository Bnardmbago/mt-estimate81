from pydantic import BaseModel, Field


class FeatureItemSuggestion(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    suggested_hours: float = Field(gt=0)
    phase: str
    role: str


class MaintenanceAssumptions(BaseModel):
    monthly_support_hours: float = Field(ge=0, default=0)
    notes: str = ""


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
