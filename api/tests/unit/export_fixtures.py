import uuid
from datetime import datetime
from types import SimpleNamespace

from app.exports.quotation_context import build_quotation_context
from app.exports.report_context import build_report_context
from app.i18n.localized_content import store_localized_dict


def sample_estimate_with_calculation(*, estimate_id: uuid.UUID | None = None):
    feature_item = SimpleNamespace(
        sort_order=0,
        name="User login & auth",
        description="OAuth and session management",
        phase="development",
        role="developer",
        hours=40,
    )
    return SimpleNamespace(
        id=estimate_id or uuid.uuid4(),
        project_name="Portal Redesign",
        client_name="ACME Corp",
        locale="en",
        form_data={
            "nature_of_work": "Greenfield web application",
            "main_functional_needs": "User login and dashboard",
            "budget": "¥5,000,000",
            "development_approach": "Agile",
        },
        extracted_data={
            "functional_requirements": ["User authentication", "Dashboard"],
            "non_functional_requirements": ["99.9% uptime"],
            "user_roles": ["Admin", "User"],
            "modules": ["Auth", "Dashboard"],
            "external_systems": ["Stripe"],
            "risks": ["Third-party API changes"],
            "gaps": ["Mobile support scope unclear"],
            "confidence_notes": "High confidence on auth module.",
            "confidence_score": 85,
            "accuracy_level": "high",
            "confidence_factors": ["Clear auth scope"],
            "estimate_type": "Web Application",
            "estimate_exclusions": ["Mobile native apps"],
            "cost_drivers": [{"name": "OAuth integration", "impact_jpy": 120000}],
        },
        feature_items=[feature_item],
        form_schema_snapshot=[],
        calculation_result={
            "total_effort_hours": 40,
            "total_effort_days": 5.0,
            "estimated_duration_days": 5.0,
            "recommended_team_size": 1,
            "phase_breakdown": [
                {"phase": "development", "hours": 16.0, "percentage": 0.40, "days": 2.0},
                {"phase": "testing", "hours": 10.0, "percentage": 0.25, "days": 1.25},
            ],
            "role_breakdown": [
                {
                    "role": "developer",
                    "hours": 40,
                    "rate_jpy": 6000,
                    "cost_jpy": 240000,
                }
            ],
            "nrc": {
                "labor_jpy": 240000,
                "setup_jpy": 400000,
                "contingency_jpy": 36000,
                "overhead_jpy": 24000,
                "total_jpy": 700000,
            },
            "nrc_line_items": [
                {"category": "Development", "item": "Development", "cost_jpy": 240000},
                {"category": "Infrastructure Setup", "item": "Infrastructure Setup", "cost_jpy": 400000},
                {"category": "Contingency", "item": "Contingency", "cost_jpy": 36000},
                {"category": "Overhead", "item": "Overhead", "cost_jpy": 24000},
            ],
            "rc": {
                "monthly_items": [{"name": "hosting", "amount_jpy": 50000}],
                "maintenance_jpy": 120000,
                "monthly_total_jpy": 170000,
                "annual_total_jpy": 2040000,
            },
            "rc_line_items": [
                {
                    "category": "Cloud Hosting",
                    "item": "hosting",
                    "monthly_jpy": 50000,
                    "annual_jpy": 600000,
                },
                {
                    "category": "Maintenance",
                    "item": "Maintenance and Support",
                    "monthly_jpy": 120000,
                    "annual_jpy": 1440000,
                },
            ],
            "first_year_total_jpy": 2740000,
            "cost_drivers": [{"name": "OAuth integration", "impact_jpy": 120000}],
            "rate_card_version_id": str(uuid.uuid4()),
            "gantt": {
                "project_start_date": "2026-06-09",
                "project_end_date": "2026-06-13",
                "total_working_days": 5,
                "phases": [
                    {
                        "phase": "development",
                        "start_date": "2026-06-09",
                        "end_date": "2026-06-13",
                        "duration_working_days": 5,
                    }
                ],
                "tasks": [
                    {
                        "feature_item_id": str(uuid.uuid4()),
                        "name": "User login & auth",
                        "phase": "development",
                        "role": "developer",
                        "hours": 40,
                        "effort_days": 5.0,
                        "start_date": "2026-06-09",
                        "end_date": "2026-06-13",
                        "duration_working_days": 5,
                    }
                ],
            },
        },
    )


def sample_estimate_with_discount(*, estimate_id: uuid.UUID | None = None):
    estimate = sample_estimate_with_calculation(estimate_id=estimate_id)
    estimate.calculation_result = {
        **estimate.calculation_result,
        "nrc_original_total_jpy": 1000000,
        "discount_rate_applied": 0.30,
        "discount_amount_jpy": 300000,
    }
    return estimate


def sample_estimate_with_localized_form(*, estimate_id: uuid.UUID | None = None):
    estimate = sample_estimate_with_calculation(estimate_id=estimate_id)
    estimate.form_data = store_localized_dict(
        None,
        "en",
        {
            "desired_system": "Customer portal",
            "usage_platform": "web_browser",
            "development_approach": "Agile",
            "nature_of_work": "Greenfield web application",
        },
    )
    estimate.form_data = store_localized_dict(
        estimate.form_data,
        "ja",
        {
            "desired_system": "顧客ポータル",
            "usage_platform": "web_browser",
            "development_approach": "アジャイル",
            "nature_of_work": "新規Webアプリケーション",
        },
    )
    return estimate


def sample_report_context(
    estimate=None,
    *,
    locale: str = "en",
    generated_at: datetime | None = None,
    rate_card_name: str | None = "2026 Standard Rates",
    rate_card_version_number: int | None = 2,
    rate_card_effective_date: datetime | None = None,
    export_revision: int = 1,
    export_user_display_name: str | None = None,
):
    estimate = estimate or sample_estimate_with_calculation()
    return build_report_context(
        estimate,
        locale,
        generated_at=generated_at or datetime(2026, 6, 7),
        rate_card_name=rate_card_name,
        rate_card_version_number=rate_card_version_number,
        rate_card_effective_date=rate_card_effective_date or datetime(2026, 1, 1),
        export_revision=export_revision,
        export_user_display_name=export_user_display_name,
    )


def sample_quotation_context(
    estimate=None,
    *,
    locale: str = "en",
    generated_at: datetime | None = None,
    rate_card_name: str | None = "2026 Standard Rates",
    rate_card_version_number: int | None = 2,
    rate_card_effective_date: datetime | None = None,
    export_revision: int = 1,
    tax_rate: float = 0.10,
):
    estimate = estimate or sample_estimate_with_calculation()
    return build_quotation_context(
        estimate,
        locale,
        generated_at=generated_at or datetime(2026, 6, 7),
        rate_card_name=rate_card_name,
        rate_card_version_number=rate_card_version_number,
        rate_card_effective_date=rate_card_effective_date or datetime(2026, 1, 1),
        export_revision=export_revision,
        tax_rate=tax_rate,
    )
