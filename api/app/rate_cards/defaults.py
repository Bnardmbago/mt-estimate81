from typing import Literal

from app.rate_cards.standard_rates import default_roles_for_region

Region = Literal["japan", "philippines", "usa"]
Currency = Literal["JPY", "USD", "PHP"]

DEFAULT_REGION: Region = "japan"
DEFAULT_CURRENCY: Currency = "JPY"

DEFAULT_RATE_CARD_SETTINGS = {
    "region": DEFAULT_REGION,
    "currency": DEFAULT_CURRENCY,
    "roles": default_roles_for_region(DEFAULT_REGION),
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
    "monthly_rc_items": [
        {
            "name": "Cloud infrastructure",
            "amount": 50000,
            "category": "cloud_infrastructure",
            "service_description": "Server & database usage",
        },
        {
            "name": "System monitoring",
            "amount": 0,
            "category": "system_monitoring",
            "service_description": "24/7 monitoring & incident response",
        },
        {
            "name": "Maintenance and Support",
            "amount": 0,
            "category": "maintenance_support",
            "service_description": "Minor fixes & inquiry support",
        },
        {
            "name": "Security",
            "amount": 0,
            "category": "security",
            "service_description": "Security updates & vulnerability management",
        },
        {
            "name": "Backup",
            "amount": 0,
            "category": "backup",
            "service_description": "Data backup & restoration",
        },
    ],
    "default_maintenance_monthly_jpy": 0,
    "setup_cost_items": [
        {"name": "Infrastructure", "amount": 300000},
        {"name": "Tooling", "amount": 100000},
        {"name": "Third party", "amount": 0},
    ],
    "productivity": {"hours_per_feature_default": 40},
    "tax_rate": 0.10,
}

DEFAULT_RATE_CARD_NAME = "2026 Standard Rates"
