from typing import Literal

Region = Literal["japan", "philippines", "usa"]
Currency = Literal["JPY", "USD", "PHP"]

DEFAULT_REGION: Region = "philippines"
DEFAULT_CURRENCY: Currency = "JPY"

DEFAULT_RATE_CARD_SETTINGS = {
    "region": DEFAULT_REGION,
    "currency": DEFAULT_CURRENCY,
    "roles": [
        {"name": "PM", "hourly_rate": 8000, "daily_rate": 64000},
        {"name": "developer", "hourly_rate": 6000, "daily_rate": 48000},
        {"name": "QA", "hourly_rate": 5000, "daily_rate": 40000},
    ],
    "phases": [
        {"name": "requirement", "percentage": 0.10},
        {"name": "design", "percentage": 0.15},
        {"name": "development", "percentage": 0.40},
        {"name": "testing", "percentage": 0.25},
        {"name": "deployment", "percentage": 0.10},
    ],
    "development_approach": "traditional",
    "contingency_rate": 0.15,
    "overhead_rate": 0.10,
    "monthly_rc_items": [{"name": "hosting", "amount": 50000}],
    "setup_cost_items": [
        {"name": "Infrastructure", "amount": 300000},
        {"name": "Tooling", "amount": 100000},
        {"name": "Third party", "amount": 0},
    ],
    "productivity": {"hours_per_feature_default": 40},
    "tax_rate": 0.10,
}

DEFAULT_RATE_CARD_NAME = "2026 Standard Rates"
