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
        "generated_date": "Estimate date",
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
        "developers": "Developers",
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
        "executive_cost_summary": "Development Cost Summary",
        "estimate_id": "Estimate number",
        "export_revision": "Estimate version",
        "estimate_type": "System type",
        "estimate_creator": "Estimate prepared by",
        "maintenance_cost_monthly_annual": "Maintenance & operations (monthly / annual)",
        "development_period": "Development period",
        "amount_jpy": "Amount (JPY)",
        "monthly_rc": "Monthly RC",
        "annual_rc": "Annual RC",
        "first_year_total_cost": "First Year Total Cost",
        "total_development_cost": "Development cost",
        "total_development_cost_formula": "NRC total through deployment and delivery acceptance",
        "development_cost_original": "Development Cost",
        "limited_time_discount": "Limited-Time Discount",
        "special_price": "Special Price",
        "excluding_tax": "(excluding tax)",
        "campaign_terms_title": "Campaign Terms",
        "confidence_score": "AI Confidence Score",
        "accuracy_level": "Estimate Accuracy Level",
        "accuracy_high": "High",
        "accuracy_medium": "Medium",
        "accuracy_low": "Low",
        "key_assumptions": "Key Assumptions",
        "questionnaire": "Project Questionnaire",
        "questionnaire_header": "Client requirements",
        "questionnaire_specification": "Technical assumptions",
        "questionnaire_appendix": "Project Questionnaire (Appendix)",
        "development_model": "Development Model",
        "team_size": "Team Size",
        "delivery_location": "Delivery Location",
        "security_requirements": "Security Requirements",
        "compliance_requirements": "Compliance Requirements",
        "major_constraints": "Major Constraints",
        "estimated_duration": "Estimated Duration",
        "recommended_team_size": "Recommended Team Size",
        "days": "Days",
        "subtotal": "Subtotal",
        "grand_total": "Grand Total",
        "nrc_detailed": "NRC Breakdown (Detailed)",
        "category": "Category",
        "item": "Item",
        "service_description": "Service Description",
        "rc_detailed": "RC Breakdown (Detailed)",
        "monthly": "Monthly",
        "annual": "Annual",
        "cost_drivers_title": "Cost Drivers",
        "driver": "Driver",
        "impact": "Impact",
        "missing_information": "Missing Information",
        "estimation_warnings": "Estimation Warnings",
        "assumption_risks": "Assumption Risks",
        "estimate_exclusions": "Estimate Exclusions",
        "confidence_factors": "Confidence Factors",
        "missing_inputs": "Missing Inputs",
        "recommendations": "Recommendations",
        "effective_date": "Effective Date",
        "policy_version": "Calculation Policy Version",
        "approval": "Approval",
        "prepared_by": "Prepared By",
        "reviewed_by": "Reviewed By",
        "approved_by": "Approved By",
        "approval_date": "Date",
        "prepared_by_value": "AI Driven Estimate System",
        "nrc_total_formula": "NRC Total = Sum of all NRC items",
        "rc_monthly_formula": "Monthly RC Total",
        "rc_annual_formula": "Annual RC Total",
        "gantt_title": "Project Timeline (Gantt)",
        "gantt_assumption": "Working days Mon-Fri; tasks may overlap by role; duration = hours ÷ (headcount × 8).",
        "gantt_project_start": "Project start",
        "gantt_project_end": "Project end",
        "gantt_total_working_days": "Total working days",
        "gantt_task": "Task",
        "gantt_start_date": "Start date",
        "gantt_end_date": "End date",
        "gantt_duration_days": "Duration (days)",
        "gantt_timeline_bar": "Timeline",
    },
    "ja": {
        "title": "プロジェクト見積レポート",
        "project_summary": "プロジェクト概要",
        "project_name": "プロジェクト名",
        "client_name": "お客様名",
        "generated_date": "見積作成日",
        "input_assumptions": "入力前提",
        "extracted_requirements": "抽出要件",
        "functional_requirements": "機能要件",
        "non_functional_requirements": "非機能要件",
        "user_roles": "ユーザーロール",
        "modules": "モジュール",
        "external_systems": "外部システム",
        "feature_items": "機能詳細",
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
        "developers": "開発者数",
        "rate": "時間単価",
        "cost": "コスト",
        "nrc_breakdown": "非経常費用",
        "labor": "人件費",
        "setup": "初期費用",
        "contingency": "予備費",
        "overhead": "間接費",
        "nrc_total": "非経常費用",
        "nrc_total_note": "初期に一度だけ発生するコスト",
        "rc_breakdown": "ランニングコスト",
        "monthly_items": "月額ランニングコスト項目",
        "maintenance": "保守費用",
        "monthly_total": "月額ランニングコスト合計",
        "annual_total": "年額ランニングコスト合計",
        "first_year_total": "初年度合計",
        "risks_gaps": "リスク・ギャップ",
        "risks": "リスク",
        "gaps": "ギャップ",
        "confidence_notes": "AI信頼度メモ",
        "rate_card_reference": "レートカード参照",
        "rate_card_name": "レートカード",
        "rate_card_version": "バージョン",
        "none": "なし",
        "executive_cost_summary": "開発コストの概要",
        "estimate_id": "見積番号",
        "export_revision": "見積バージョン",
        "estimate_type": "システムの種類",
        "estimate_creator": "見積作成者",
        "maintenance_cost_monthly_annual": "保守運用費用　月額 /年間",
        "development_period": "開発期間",
        "amount_jpy": "金額（円）",
        "monthly_rc": "月額ランニングコスト",
        "annual_rc": "年額ランニングコスト",
        "first_year_total_cost": "初年度合計コスト",
        "total_development_cost": "開発費用",
        "total_development_cost_formula": "デプロイ・引渡し検収までのNRC合計",
        "development_cost_original": "開発費用",
        "limited_time_discount": "期間限定割引",
        "special_price": "特別価格",
        "excluding_tax": "（税抜）",
        "campaign_terms_title": "キャンペーン条件",
        "confidence_score": "AI信頼度スコア",
        "accuracy_level": "見積精度レベル",
        "accuracy_high": "高",
        "accuracy_medium": "中",
        "accuracy_low": "低",
        "key_assumptions": "主要前提",
        "questionnaire": "プロジェクト質問票",
        "questionnaire_header": "クライアント要件",
        "questionnaire_specification": "技術的前提",
        "questionnaire_appendix": "プロジェクト質問票（別紙）",
        "development_model": "開発モデル",
        "team_size": "チーム規模",
        "delivery_location": "開発場所",
        "security_requirements": "セキュリティ要件",
        "compliance_requirements": "コンプライアンス要件",
        "major_constraints": "主要制約",
        "estimated_duration": "見積期間",
        "recommended_team_size": "推奨チーム人数",
        "days": "日",
        "subtotal": "小計",
        "grand_total": "合計",
        "nrc_detailed": "非経常費用  内訳",
        "category": "カテゴリ",
        "item": "項目",
        "service_description": "サービス内容",
        "rc_detailed": "ランニングコスト  内訳",
        "monthly": "月額",
        "annual": "年額",
        "cost_drivers_title": "コスト要因",
        "driver": "要因",
        "impact": "影響",
        "missing_information": "不足情報",
        "estimation_warnings": "見積警告",
        "assumption_risks": "前提リスク",
        "estimate_exclusions": "見積対象外",
        "confidence_factors": "信頼度要因",
        "missing_inputs": "不足入力",
        "recommendations": "推奨事項",
        "effective_date": "適用日",
        "policy_version": "計算ポリシーバージョン",
        "approval": "承認",
        "prepared_by": "作成者",
        "reviewed_by": "レビュー者",
        "approved_by": "承認者",
        "approval_date": "日付",
        "prepared_by_value": "AI見積システム",
        "nrc_total_formula": "非経常費用 = すべての項目の合計",
        "rc_monthly_formula": "月額ランニングコスト合計",
        "rc_annual_formula": "年額ランニングコスト合計",
        "gantt_title": "プロジェクトタイムライン（ガント）",
        "gantt_assumption": "稼働日は月〜金。ロール別にタスクが重なる場合があります。期間 = 時間 ÷ (人数 × 8)。",
        "gantt_project_start": "開始日",
        "gantt_project_end": "終了日",
        "gantt_total_working_days": "総稼働日数",
        "gantt_task": "タスク",
        "gantt_start_date": "開始日",
        "gantt_end_date": "終了日",
        "gantt_duration_days": "期間（日）",
        "gantt_timeline_bar": "タイムライン",
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
        "maintenance_support": "Maintenance and Support",
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
    return f"¥{int(round(float(amount))):,}"


def format_currency_yen(amount: int | float) -> str:
    """Japanese yen style for client-facing estimates, e.g. 1,000,000円."""
    return f"{int(round(float(amount))):,}円"


def format_hours(hours: float) -> str:
    if hours == int(hours):
        return str(int(hours))
    return f"{hours:.2f}".rstrip("0").rstrip(".")


def format_effort_days(hours: float) -> str:
    days = hours / HOURS_PER_EFFORT_DAY
    return format_person_days(days)


def format_person_days(days: float) -> str:
    if days == int(days):
        return str(int(days))
    return f"{days:.2f}".rstrip("0").rstrip(".")


def format_person_months(months: float) -> str:
    if months == int(months):
        return str(int(months))
    return f"{months:.2f}".rstrip("0").rstrip(".")


def format_date(dt: datetime, locale: str) -> str:
    if locale == "ja":
        return f"{dt.year}年{dt.month}月{dt.day}日"
    return dt.strftime("%B %d, %Y").replace(" 0", " ")


def _build_form_fields(
    form_data: dict[str, Any],
    locale: str,
    schema: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    from app.exports.questionnaire import build_flat_form_fields

    return build_flat_form_fields(form_data, schema, locale)


def _build_feature_rows(
    estimate: Estimate,
    locale: str | None = None,
) -> list[dict[str, Any]]:
    from app.i18n.localized_content import resolve_feature_item_fields

    rows = []
    fallback_locale = getattr(estimate, "locale", None) or "ja"
    display_locale = locale or fallback_locale
    for item in sorted(estimate.feature_items, key=lambda fi: fi.sort_order):
        hours = float(item.hours)
        fields = resolve_feature_item_fields(
            name=item.name,
            description=item.description,
            phase=item.phase,
            role=item.role,
            localizations=getattr(item, "localizations", None),
            display_locale=display_locale,
            fallback_locale=fallback_locale,
        )
        rows.append(
            {
                "id": getattr(item, "id", None),
                "name": fields["name"],
                "description": fields["description"],
                "phase": fields["phase"],
                "role": fields["role"],
                "hours": hours,
                "days": hours / HOURS_PER_EFFORT_DAY,
            }
        )
    return rows


def generate_markdown(report_context: dict[str, Any]) -> str:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(default=False),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("estimate.md.j2")
    return template.render(
        ctx=report_context,
        format_currency=format_currency,
        format_hours=format_hours,
        format_effort_days=format_effort_days,
        format_person_days=format_person_days,
    )
