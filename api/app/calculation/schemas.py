from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.calculation.development_approach import DevelopmentApproach
from app.rate_cards.defaults import DEFAULT_CURRENCY, DEFAULT_REGION

Region = Literal["japan", "philippines", "usa"]
Currency = Literal["JPY", "USD", "PHP"]
CostBreakdownMode = Literal["standard", "flexible"]


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
    hourly_rate: int = 0
    daily_rate: int | None = None
    hourly_rate_jpy: int | None = None
    daily_rate_jpy: int | None = None

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_fields(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        if "hourly_rate" not in data and data.get("hourly_rate_jpy") is not None:
            data["hourly_rate"] = data["hourly_rate_jpy"]
        if "daily_rate" not in data and data.get("daily_rate_jpy") is not None:
            data["daily_rate"] = data["daily_rate_jpy"]
        return data


class PhasePercentage(BaseModel):
    name: str
    percentage: float


class MonthlyRcItem(BaseModel):
    name: str
    amount: int = 0
    amount_jpy: int | None = None
    category: str | None = None
    service_description: str | None = None

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_fields(cls, data: object) -> object:
        if isinstance(data, dict) and "amount" not in data and data.get("amount_jpy") is not None:
            data["amount"] = data["amount_jpy"]
        return data


class SetupCostItem(BaseModel):
    name: str = Field(min_length=1)
    amount: int = Field(default=0, ge=0)
    amount_jpy: int | None = None

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_fields(cls, data: object) -> object:
        if isinstance(data, dict) and "amount" not in data and data.get("amount_jpy") is not None:
            data["amount"] = data["amount_jpy"]
        return data


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
    default_maintenance_monthly_jpy: int = Field(default=0, ge=0)
    setup_cost_items: list[SetupCostItem] = Field(default_factory=list)
    setup_costs: SetupCosts | None = None
    productivity: ProductivitySettings
    tax_rate: float
    region: Region = DEFAULT_REGION
    currency: Currency = DEFAULT_CURRENCY
    cost_breakdown_mode: CostBreakdownMode = "standard"

    @model_validator(mode="after")
    def migrate_legacy_setup_costs(self) -> "RateCardSettings":
        if not self.setup_cost_items and self.setup_costs is not None:
            self.setup_cost_items = [
                SetupCostItem(name="Infrastructure", amount=self.setup_costs.infrastructure_jpy),
                SetupCostItem(name="Tooling", amount=self.setup_costs.tooling_jpy),
                SetupCostItem(name="Third party", amount=self.setup_costs.third_party_jpy),
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
    nrc_original_total_jpy: int | None = None
    discount_rate_applied: float | None = None
    discount_amount_jpy: int | None = None
    internal_pricing: dict | None = None
