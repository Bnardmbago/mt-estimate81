from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.calculation.engine import HOURS_PER_EFFORT_DAY
from app.models.estimate import Estimate

TEMPLATE_DIR = Path(__file__).parent / "templates"

FORM_FIELD_KEYS = [
    "nature_of_work",
    "scope_boundaries",
    "project_overview",
    "system_type",
    "business_domain",
    "main_functional_needs",
    "non_functional_needs",
    "users_and_load",
    "integrations",
    "data_complexity",
    "ui_complexity",
    "technology_preferences",
    "development_approach",
    "rules_and_standards",
    "team_and_resources",
    "development_location",
    "delivery_timing",
    "maintenance_support",
    "risks_unknowns",
    "budget",
]

LABELS: dict[str, dict[str, str]] = {
    "en": {
        "title": "Project Estimate Report",
        "project_summary": "Project Summary",
        "project_name": "Project Name",
        "client_name": "Client",
        "generated_date": "Generated",
        "input_assumptions": "Input Assumptions",
        "extracted_requirements": "Extracted Requirements",
        "functional_requirements": "Functional Requirements",
        "non_functional_requirements": "Non-Functional Requirements",
        "user_roles": "User Roles",
        "modules": "Modules",
        "external_systems": "External Systems",
        "feature_items": "Feature Line Items",
        "feature_name": "Feature",
        "feature_description": "Description",
        "feature_phase": "Phase",
        "feature_role": "Role",
        "feature_hours": "Hours",
        "feature_days": "Effort Days",
        "effort_summary": "Effort Summary",
        "total_hours": "Total Person-Hours",
        "total_days": "Total Effort Days",
        "phase_breakdown": "Phase Breakdown",
        "phase": "Phase",
        "hours": "Hours",
        "percentage": "Percentage",
        "role_breakdown": "Role Breakdown",
        "role": "Role",
        "rate": "Hourly Rate",
        "cost": "Cost",
        "nrc_breakdown": "NRC Breakdown",
        "labor": "Labor",
        "setup": "Setup Costs",
        "contingency": "Contingency",
        "overhead": "Overhead",
        "nrc_total": "NRC Total",
        "rc_breakdown": "RC Breakdown",
        "monthly_items": "Monthly RC Items",
        "maintenance": "Maintenance",
        "monthly_total": "Monthly RC Total",
        "annual_total": "Annual RC Total",
        "first_year_total": "First Year Total",
        "risks_gaps": "Risks & Gaps",
        "risks": "Risks",
        "gaps": "Gaps",
        "confidence_notes": "AI Confidence Notes",
        "rate_card_reference": "Rate Card Reference",
        "rate_card_name": "Rate Card",
        "rate_card_version": "Version",
        "none": "None",
    },
    "ja": {
        "title": "プロジェクト見積レポート",
        "project_summary": "プロジェクト概要",
        "project_name": "プロジェクト名",
        "client_name": "クライアント",
        "generated_date": "作成日",
        "input_assumptions": "入力前提",
        "extracted_requirements": "抽出要件",
        "functional_requirements": "機能要件",
        "non_functional_requirements": "非機能要件",
        "user_roles": "ユーザーロール",
        "modules": "モジュール",
        "external_systems": "外部システム",
        "feature_items": "機能明細",
        "feature_name": "機能",
        "feature_description": "説明",
        "feature_phase": "フェーズ",
        "feature_role": "ロール",
        "feature_hours": "工数（時間）",
        "feature_days": "工数（日）",
        "effort_summary": "工数サマリー",
        "total_hours": "合計工数（時間）",
        "total_days": "合計工数（日）",
        "phase_breakdown": "フェーズ内訳",
        "phase": "フェーズ",
        "hours": "時間",
        "percentage": "比率",
        "role_breakdown": "ロール内訳",
        "role": "ロール",
        "rate": "時間単価",
        "cost": "コスト",
        "nrc_breakdown": "NRC内訳",
        "labor": "人件費",
        "setup": "初期費用",
        "contingency": "予備費",
        "overhead": "間接費",
        "nrc_total": "NRC合計",
        "rc_breakdown": "RC内訳",
        "monthly_items": "月額RC項目",
        "maintenance": "保守費用",
        "monthly_total": "月額RC合計",
        "annual_total": "年間RC合計",
        "first_year_total": "初年度合計",
        "risks_gaps": "リスク・ギャップ",
        "risks": "リスク",
        "gaps": "ギャップ",
        "confidence_notes": "AI信頼度メモ",
        "rate_card_reference": "レートカード参照",
        "rate_card_name": "レートカード",
        "rate_card_version": "バージョン",
        "none": "なし",
    },
}

FORM_FIELD_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "nature_of_work": "Nature of Work",
        "scope_boundaries": "Scope Boundaries",
        "project_overview": "Project Overview",
        "system_type": "System Type",
        "business_domain": "Business Domain",
        "main_functional_needs": "Main Functional Needs",
        "non_functional_needs": "Non-Functional Needs",
        "users_and_load": "Users and Load",
        "integrations": "Integrations",
        "data_complexity": "Data Complexity",
        "ui_complexity": "UI Complexity",
        "technology_preferences": "Technology Preferences",
        "development_approach": "Development Approach",
        "rules_and_standards": "Rules and Standards",
        "team_and_resources": "Team and Resources",
        "development_location": "Development Location",
        "delivery_timing": "Delivery Timing",
        "maintenance_support": "Maintenance Support",
        "risks_unknowns": "Risks and Unknowns",
        "budget": "Budget",
    },
    "ja": {
        "nature_of_work": "業務の性質",
        "scope_boundaries": "スコープ境界",
        "project_overview": "プロジェクト概要",
        "system_type": "システム種別",
        "business_domain": "業務領域",
        "main_functional_needs": "主要機能要件",
        "non_functional_needs": "非機能要件",
        "users_and_load": "ユーザーと負荷",
        "integrations": "連携",
        "data_complexity": "データ複雑度",
        "ui_complexity": "UI複雑度",
        "technology_preferences": "技術選好",
        "development_approach": "開発アプローチ",
        "rules_and_standards": "ルールと標準",
        "team_and_resources": "チームとリソース",
        "development_location": "開発場所",
        "delivery_timing": "納期",
        "maintenance_support": "保守・サポート",
        "risks_unknowns": "リスク・不明点",
        "budget": "予算",
    },
}


def format_currency(amount: int | float) -> str:
    return f"¥{int(amount):,}"


def format_hours(hours: float) -> str:
    if hours == int(hours):
        return str(int(hours))
    return f"{hours:.2f}".rstrip("0").rstrip(".")


def format_effort_days(hours: float) -> str:
    days = hours / HOURS_PER_EFFORT_DAY
    if days == int(days):
        return str(int(days))
    return f"{days:.2f}".rstrip("0").rstrip(".")


def format_date(dt: datetime, locale: str) -> str:
    if locale == "ja":
        return f"{dt.year}年{dt.month}月{dt.day}日"
    return dt.strftime("%B %d, %Y").replace(" 0", " ")


def _build_form_fields(form_data: dict[str, Any], locale: str) -> list[dict[str, str]]:
    labels = FORM_FIELD_LABELS[locale]
    fields: list[dict[str, str]] = []
    for key in FORM_FIELD_KEYS:
        value = form_data.get(key)
        if value is None or value == "":
            continue
        fields.append({"label": labels[key], "value": str(value)})
    return fields


def _build_feature_rows(estimate: Estimate) -> list[dict[str, Any]]:
    rows = []
    for item in sorted(estimate.feature_items, key=lambda fi: fi.sort_order):
        hours = float(item.hours)
        rows.append(
            {
                "name": item.name,
                "description": item.description,
                "phase": item.phase,
                "role": item.role,
                "hours": hours,
                "days": hours / HOURS_PER_EFFORT_DAY,
            }
        )
    return rows


def generate_markdown(
    estimate: Estimate,
    locale: str,
    *,
    rate_card_name: str | None = None,
    rate_card_version_number: int | None = None,
    generated_at: datetime | None = None,
) -> str:
    if locale not in ("ja", "en"):
        raise ValueError(f"Unsupported locale: {locale}")

    calculation = estimate.calculation_result or {}
    extracted = estimate.extracted_data or {}
    form_data = estimate.form_data or {}
    generated_at = generated_at or datetime.utcnow()

    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(default=False),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("estimate.md.j2")

    return template.render(
        labels=LABELS[locale],
        locale=locale,
        project_name=estimate.project_name,
        client_name=estimate.client_name,
        generated_date=format_date(generated_at, locale),
        form_fields=_build_form_fields(form_data, locale),
        extracted=extracted,
        feature_items=_build_feature_rows(estimate),
        calculation=calculation,
        rate_card_name=rate_card_name,
        rate_card_version_number=rate_card_version_number,
        format_currency=format_currency,
        format_hours=format_hours,
        format_effort_days=format_effort_days,
    )
