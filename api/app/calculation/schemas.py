from pydantic import BaseModel, Field


class FeatureItemInput(BaseModel):
    name: str = Field(min_length=1)
    hours: float = Field(ge=0)
    phase: str
    role: str


class RoleRate(BaseModel):
    name: str
    hourly_rate_jpy: int
    daily_rate_jpy: int | None = None


class PhasePercentage(BaseModel):
    name: str
    percentage: float


class MonthlyRcItem(BaseModel):
    name: str
    amount_jpy: int


class SetupCosts(BaseModel):
    infrastructure_jpy: int = 0
    tooling_jpy: int = 0
    third_party_jpy: int = 0


class ProductivitySettings(BaseModel):
    hours_per_feature_default: int = 40


class RateCardSettings(BaseModel):
    roles: list[RoleRate]
    phases: list[PhasePercentage]
    contingency_rate: float
    overhead_rate: float
    monthly_rc_items: list[MonthlyRcItem]
    setup_costs: SetupCosts
    productivity: ProductivitySettings
    tax_rate: float


class CalculationResult(BaseModel):
    total_effort_hours: float
    total_effort_days: float
    phase_breakdown: list[dict]
    role_breakdown: list[dict]
    nrc: dict
    rc: dict
    first_year_total_jpy: int
    rate_card_version_id: str
