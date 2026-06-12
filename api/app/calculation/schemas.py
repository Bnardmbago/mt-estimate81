from pydantic import BaseModel, Field, model_validator

from app.calculation.development_approach import DevelopmentApproach


class FeatureItemInput(BaseModel):
    name: str = Field(min_length=1)
    hours: float = Field(ge=0)
    phase: str
    role: str


class GanttFeatureItemInput(BaseModel):
    id: str | None = None
    sort_order: int = 0
    name: str
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


class SetupCostItem(BaseModel):
    name: str = Field(min_length=1)
    amount_jpy: int = Field(ge=0)


class SetupCosts(BaseModel):
    infrastructure_jpy: int = 0
    tooling_jpy: int = 0
    third_party_jpy: int = 0


class ProductivitySettings(BaseModel):
    hours_per_feature_default: int = 40


class RateCardSettings(BaseModel):
    roles: list[RoleRate]
    phases: list[PhasePercentage]
    development_approach: DevelopmentApproach
    contingency_rate: float
    overhead_rate: float
    monthly_rc_items: list[MonthlyRcItem]
    setup_cost_items: list[SetupCostItem] = Field(default_factory=list)
    setup_costs: SetupCosts | None = None
    productivity: ProductivitySettings
    tax_rate: float

    @model_validator(mode="after")
    def migrate_legacy_setup_costs(self) -> "RateCardSettings":
        if not self.setup_cost_items and self.setup_costs is not None:
            self.setup_cost_items = [
                SetupCostItem(name="Infrastructure", amount_jpy=self.setup_costs.infrastructure_jpy),
                SetupCostItem(name="Tooling", amount_jpy=self.setup_costs.tooling_jpy),
                SetupCostItem(name="Third party", amount_jpy=self.setup_costs.third_party_jpy),
            ]
        return self


class CalculationResult(BaseModel):
    total_effort_hours: float
    total_effort_days: float
    estimated_duration_days: float
    recommended_team_size: int
    development_approach: str
    development_approach_effort_multiplier: float
    phase_breakdown: list[dict]
    role_breakdown: list[dict]
    nrc: dict
    rc: dict
    nrc_line_items: list[dict]
    rc_line_items: list[dict]
    cost_drivers: list[dict]
    first_year_total_jpy: int
    rate_card_version_id: str
    gantt: dict = Field(default_factory=dict)
