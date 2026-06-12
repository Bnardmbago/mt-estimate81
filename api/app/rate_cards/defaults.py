DEFAULT_RATE_CARD_SETTINGS = {
    "roles": [
        {"name": "PM", "hourly_rate_jpy": 8000, "daily_rate_jpy": 64000},
        {"name": "developer", "hourly_rate_jpy": 6000, "daily_rate_jpy": 48000},
        {"name": "QA", "hourly_rate_jpy": 5000, "daily_rate_jpy": 40000},
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
    "monthly_rc_items": [{"name": "hosting", "amount_jpy": 50000}],
    "setup_cost_items": [
        {"name": "Infrastructure", "amount_jpy": 300000},
        {"name": "Tooling", "amount_jpy": 100000},
        {"name": "Third party", "amount_jpy": 0},
    ],
    "productivity": {"hours_per_feature_default": 40},
    "tax_rate": 0.10,
}

DEFAULT_RATE_CARD_NAME = "2026 Standard Rates"
