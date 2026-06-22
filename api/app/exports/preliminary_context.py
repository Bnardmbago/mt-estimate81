from datetime import datetime
from typing import Any

from app.config import settings
from app.exports.markdown import format_date
from app.exports.quotation_context import DEFAULT_TAX_RATE
from app.exports.report_context import build_report_context
from app.models.estimate import Estimate

HOURS_PER_DAY = 8
WORKING_DAYS_PER_MONTH = 20

ROLE_BUCKETS: dict[str, set[str]] = {
    "pm": {"pm", "project_manager", "project manager"},
    "engineer": {
        "developer",
        "senior_developer",
        "frontend_developer",
        "backend_developer",
        "full_stack_developer",
        "architect",
        "tech_lead",
        "devops",
        "full stack developer",
        "frontend developer",
        "backend developer",
        "senior developer",
    },
    "designer": {"designer", "ui_designer", "ux_designer", "ui designer", "ux designer"},
    "qa": {"qa", "qa_engineer", "qa engineer"},
}

PHASE_KEYS = ("requirement", "design", "development", "testing", "management")

FEATURE_SECTIONS: list[tuple[str, str, set[str]]] = [
    ("system_dev_header", "system_dev", set()),
    ("requirement", "requirement", {"requirement", "requirements", "analysis"}),
    ("design", "design", {"design"}),
    ("infrastructure", "infrastructure", {"deployment", "infrastructure", "devops"}),
    ("app_dev", "app_dev", {"development", "implementation"}),
    ("buffer", "buffer", set()),
    ("testing", "testing", {"testing", "test", "qa"}),
    ("pm_header", "pm_section", set()),
    ("pm", "pm", {"management", "project_management", "pm"}),
]

PRELIMINARY_LABELS: dict[str, dict[str, Any]] = {
    "ja": {
        "title": "概算見積書（テンプレート）",
        "issue_date": "見積日",
        "recipient": "宛先",
        "recipient_suffix": "様",
        "intro": "下記の通り御見積もり申し上げます。",
        "company_name": "会社名",
        "company_address": "住所",
        "contact_person": "担当者",
        "project_info": "プロジェクト情報",
        "item": "項目",
        "content": "内容",
        "project_name": "プロジェクト名",
        "total_with_tax": "見積合計（税込）",
        "summary_title": "見積概要",
        "role": "役割",
        "unit_rate": "単価（円）",
        "utilization": "稼働率（%）",
        "headcount": "人数",
        "months": "月数",
        "amount": "金額（円）",
        "role_pm": "PM",
        "role_engineer": "エンジニア",
        "role_designer": "デザイナー",
        "role_qa": "QA",
        "role_other": "その他",
        "subtotal_ex_tax": "合計（税抜）",
        "effort_detail": "工数詳細",
        "phase_effort_title": "1. 工程別の見積工数",
        "phase": "工程",
        "percentage": "割合",
        "assignee": "担当",
        "effort_days": "工数（人日）",
        "effort_months": "工数（人月）",
        "phase_requirement": "要件定義／仕様分析",
        "phase_design": "設計",
        "phase_development": "実装",
        "phase_testing": "動作確認（QA）",
        "phase_management": "管理工数",
        "total_effort": "合計工数",
        "dev_effort_title": "2. 開発工数",
        "dev_effort_note": "本見積は、備考欄および「3. 見積の前提条件」に記載する内容を前提としています。",
        "no_col": "No.",
        "feature": "要求の機能",
        "feature_summary": "機能概要",
        "phase_item": "工程項目",
        "remarks": "備考",
        "section_system_dev": "■ システム開発",
        "section_requirement": "□ 要件定義／仕様分析",
        "section_design": "□ 設計",
        "section_infrastructure": "□ インフラ構築",
        "section_app_dev": "□ アプリ開発",
        "section_buffer": "□ バッファ",
        "section_testing": "□ 動作テスト",
        "section_pm": "■ プロジェクト管理",
        "section_pm_item": "□ プロジェクト管理",
        "assumptions_title": "3. 見積の前提条件",
        "assumptions": [
            "本見積は、お客様との協議内容に基づき作成しております。要件に変更が発生した場合は、再見積となる場合があります。",
            "保守・運用費用については、別途保守要件（メンテナンス・サポート内容等）を協議の上、お見積りいたします。",
            "本見積に含まれる範囲については別途定義するものとします。",
            "本見積に含まれない作業・機能については別途お見積りいたします。",
            "納品後の仕様変更、追加開発については別途お見積りとなります。",
        ],
        "approval_title": "承認欄",
        "approval_company": "会社名",
        "approver": "承認者",
        "approval_date": "承認日",
        "signature": "署名",
        "blank": "__________________",
        "dash": "—",
    },
    "en": {
        "title": "Preliminary Estimate (Template)",
        "issue_date": "Estimate Date",
        "recipient": "To",
        "recipient_suffix": "",
        "intro": "We are pleased to submit the following estimate.",
        "company_name": "Company",
        "company_address": "Address",
        "contact_person": "Contact",
        "project_info": "Project Information",
        "item": "Item",
        "content": "Details",
        "project_name": "Project Name",
        "total_with_tax": "Total Estimate (incl. tax)",
        "summary_title": "Estimate Summary",
        "role": "Role",
        "unit_rate": "Unit Rate (JPY)",
        "utilization": "Utilization (%)",
        "headcount": "Headcount",
        "months": "Months",
        "amount": "Amount (JPY)",
        "role_pm": "PM",
        "role_engineer": "Engineer",
        "role_designer": "Designer",
        "role_qa": "QA",
        "role_other": "Other",
        "subtotal_ex_tax": "Subtotal (excl. tax)",
        "effort_detail": "Effort Details",
        "phase_effort_title": "1. Effort by Phase",
        "phase": "Phase",
        "percentage": "Share",
        "assignee": "Assignee",
        "effort_days": "Effort (person-days)",
        "effort_months": "Effort (person-months)",
        "phase_requirement": "Requirements / Analysis",
        "phase_design": "Design",
        "phase_development": "Implementation",
        "phase_testing": "QA / Testing",
        "phase_management": "Project Management",
        "total_effort": "Total Effort",
        "dev_effort_title": "2. Development Effort",
        "dev_effort_note": "This estimate is based on the remarks and the assumptions in section 3.",
        "no_col": "No.",
        "feature": "Requested Feature",
        "feature_summary": "Summary",
        "phase_item": "Phase",
        "remarks": "Remarks",
        "section_system_dev": "■ System Development",
        "section_requirement": "□ Requirements / Analysis",
        "section_design": "□ Design",
        "section_infrastructure": "□ Infrastructure",
        "section_app_dev": "□ Application Development",
        "section_buffer": "□ Buffer / Contingency",
        "section_testing": "□ Testing",
        "section_pm": "■ Project Management",
        "section_pm_item": "□ Project Management",
        "assumptions_title": "3. Estimate Assumptions",
        "assumptions": [
            "This estimate is based on discussions with the client. Changes to requirements may require a re-estimate.",
            "Maintenance and operations costs will be quoted separately after maintenance requirements are agreed.",
            "The scope included in this estimate will be defined separately.",
            "Work and features not included in this estimate will be quoted separately.",
            "Post-delivery specification changes and additional development will be quoted separately.",
        ],
        "approval_title": "Approval",
        "approval_company": "Company",
        "approver": "Approver",
        "approval_date": "Approval Date",
        "signature": "Signature",
        "blank": "__________________",
        "dash": "—",
    },
}


def _normalize_role(role: str) -> str:
    return role.strip().lower().replace("-", "_").replace(" ", "_")


def _role_bucket(role: str) -> str:
    normalized = _normalize_role(role)
    compact = normalized.replace("_", " ")
    for bucket, keys in ROLE_BUCKETS.items():
        if normalized in keys or compact in keys:
            return bucket
    if "pm" in normalized or "project" in normalized:
        return "pm"
    if "design" in normalized or "ui" in normalized or "ux" in normalized:
        return "designer"
    if "qa" in normalized or "test" in normalized:
        return "qa"
    if any(token in normalized for token in ("dev", "engineer", "architect", "devops", "sre")):
        return "engineer"
    return "other"


def _normalize_phase(phase: str) -> str:
    normalized = phase.strip().lower()
    if normalized in {"requirement", "requirements", "analysis"}:
        return "requirement"
    if normalized in {"design"}:
        return "design"
    if normalized in {"development", "implementation", "dev"}:
        return "development"
    if normalized in {"testing", "test", "qa"}:
        return "testing"
    if normalized in {"deployment", "management", "project_management", "pm"}:
        return "management"
    if normalized in {"infrastructure", "devops"}:
        return "infrastructure"
    return normalized


def _hours_to_days(hours: float) -> float:
    return round(hours / HOURS_PER_DAY, 2)


def _days_to_months(days: float) -> float:
    return round(days / WORKING_DAYS_PER_MONTH, 2)


def _build_role_summary(
    role_breakdown: list[dict[str, Any]],
    estimated_duration_days: float,
    labels: dict[str, Any],
) -> tuple[list[dict[str, Any]], int]:
    buckets: dict[str, dict[str, Any]] = {
        key: {
            "key": key,
            "label": labels[f"role_{key}"],
            "hours": 0.0,
            "cost_jpy": 0,
            "headcount": 0,
            "rate_weighted_sum": 0.0,
            "utilization": labels["dash"],
        }
        for key in ("pm", "engineer", "designer", "qa", "other")
    }

    for row in role_breakdown:
        bucket_key = _role_bucket(str(row.get("role", "")))
        bucket = buckets[bucket_key]
        hours = float(row.get("hours") or 0)
        cost = int(row.get("cost_jpy") or 0)
        headcount = int(row.get("personnel_count") or 0)
        rate = int(row.get("rate_jpy") or 0)
        bucket["hours"] += hours
        bucket["cost_jpy"] += cost
        bucket["headcount"] += headcount
        if hours > 0:
            bucket["rate_weighted_sum"] += rate * hours

    months = _days_to_months(estimated_duration_days) if estimated_duration_days > 0 else 0.0
    rows: list[dict[str, Any]] = []
    total_amount = 0

    for key in ("pm", "engineer", "designer", "qa", "other"):
        bucket = buckets[key]
        hours = bucket["hours"]
        amount = bucket["cost_jpy"]
        total_amount += amount
        unit_rate = int(round(bucket["rate_weighted_sum"] / hours)) if hours > 0 else 0
        rows.append(
            {
                "label": bucket["label"],
                "unit_rate_jpy": unit_rate if amount > 0 else None,
                "utilization": bucket["utilization"],
                "headcount": bucket["headcount"] if bucket["headcount"] > 0 else None,
                "months": months if amount > 0 else None,
                "amount_jpy": amount if amount > 0 else None,
            }
        )

    return rows, total_amount


def _phase_label(phase_key: str, labels: dict[str, Any]) -> str:
    mapping = {
        "requirement": labels["phase_requirement"],
        "design": labels["phase_design"],
        "development": labels["phase_development"],
        "testing": labels["phase_testing"],
        "management": labels["phase_management"],
    }
    return mapping.get(phase_key, phase_key)


def _build_phase_effort_rows(
    phase_breakdown: list[dict[str, Any]],
    role_breakdown: list[dict[str, Any]],
    labels: dict[str, Any],
) -> tuple[list[dict[str, Any]], float, float]:
    phase_hours: dict[str, float] = {key: 0.0 for key in PHASE_KEYS}
    phase_roles: dict[str, set[str]] = {key: set() for key in PHASE_KEYS}

    for row in phase_breakdown:
        phase_key = _normalize_phase(str(row.get("phase", "")))
        if phase_key == "infrastructure":
            phase_key = "development"
        if phase_key not in phase_hours:
            phase_key = "development"
        phase_hours[phase_key] += float(row.get("hours") or 0)

    for row in role_breakdown:
        role = str(row.get("role", ""))
        bucket = _role_bucket(role)
        if bucket == "pm":
            phase_roles["management"].add(role)
        hours = float(row.get("hours") or 0)
        if hours <= 0:
            continue
        phase_key = _normalize_phase(str(row.get("phase", role)))
        if phase_key == "infrastructure":
            phase_key = "development"
        if phase_key not in phase_roles:
            phase_key = "development"
        phase_roles[phase_key].add(role)

    rows: list[dict[str, Any]] = []
    total_hours = 0.0
    total_days = 0.0

    for phase_key in PHASE_KEYS:
        hours = phase_hours[phase_key]
        total_hours += hours
        days = _hours_to_days(hours)
        total_days += days
        percentage = 0.0
        assignees = ", ".join(sorted(phase_roles[phase_key])) if phase_roles[phase_key] else labels["dash"]
        rows.append(
            {
                "phase": _phase_label(phase_key, labels),
                "percentage": percentage,
                "assignee": assignees,
                "effort_days": days if hours > 0 else None,
                "effort_months": _days_to_months(days) if hours > 0 else None,
                "hours": hours,
            }
        )

    if total_hours > 0:
        for row in rows:
            row["percentage"] = round((row["hours"] / total_hours) * 100)

    return rows, total_days, _days_to_months(total_days)


def _feature_section_label(section_key: str, labels: dict[str, Any]) -> str:
    return labels.get(f"section_{section_key}", section_key)


def _build_feature_effort_sections(
    feature_items: list[dict[str, Any]],
    contingency_jpy: int,
    labor_jpy: int,
    total_effort_days: float,
    labels: dict[str, Any],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {
        "requirement": [],
        "design": [],
        "infrastructure": [],
        "app_dev": [],
        "testing": [],
        "pm": [],
    }

    for index, item in enumerate(feature_items, start=1):
        phase_key = _normalize_phase(str(item.get("phase", "")))
        if phase_key == "requirement":
            target = "requirement"
        elif phase_key == "design":
            target = "design"
        elif phase_key in {"infrastructure", "deployment", "devops"}:
            target = "infrastructure"
        elif phase_key == "testing":
            target = "testing"
        elif phase_key == "management":
            target = "pm"
        else:
            target = "app_dev"

        hours = float(item.get("hours") or 0)
        grouped[target].append(
            {
                "no": index,
                "name": item.get("name") or "",
                "summary": item.get("description") or item.get("name") or "",
                "phase_item": _feature_section_label(target, labels),
                "effort_days": _hours_to_days(hours) if hours > 0 else None,
                "remarks": labels["dash"],
            }
        )

    buffer_days = None
    if contingency_jpy > 0 and labor_jpy > 0 and total_effort_days > 0:
        buffer_days = round(contingency_jpy / (labor_jpy / total_effort_days), 2)

    sections: list[dict[str, Any]] = []
    for label_key, section_key, _ in FEATURE_SECTIONS:
        if section_key == "system_dev":
            sections.append({"type": "header", "label": _feature_section_label("system_dev", labels)})
            continue
        if section_key == "pm_section":
            sections.append({"type": "header", "label": _feature_section_label("pm", labels)})
            continue
        if section_key == "buffer":
            sections.append(
                {
                    "type": "subheader",
                    "label": _feature_section_label("buffer", labels),
                }
            )
            if buffer_days:
                sections.append(
                    {
                        "type": "row",
                        "no": None,
                        "name": _feature_section_label("buffer", labels),
                        "summary": "",
                        "phase_item": _feature_section_label("buffer", labels),
                        "effort_days": buffer_days,
                        "remarks": labels["dash"],
                    }
                )
            continue

        sections.append({"type": "subheader", "label": _feature_section_label(section_key, labels)})
        rows = grouped.get(section_key, [])
        if rows:
            sections.extend({"type": "row", **row} for row in rows)

    return sections


def build_preliminary_context(
    estimate: Estimate,
    locale: str,
    *,
    generated_at: datetime,
    rate_card_name: str | None,
    rate_card_version_number: int | None,
    rate_card_effective_date: datetime | None,
    export_revision: int,
    tax_rate: float | None = None,
) -> dict[str, Any]:
    if locale not in ("ja", "en"):
        raise ValueError(f"Unsupported locale: {locale}")

    report = build_report_context(
        estimate,
        locale,
        generated_at=generated_at,
        rate_card_name=rate_card_name,
        rate_card_version_number=rate_card_version_number,
        rate_card_effective_date=rate_card_effective_date,
        export_revision=export_revision,
    )

    labels = PRELIMINARY_LABELS[locale]
    resolved_tax_rate = tax_rate if tax_rate is not None else DEFAULT_TAX_RATE
    calculation = report["calculation"]
    nrc = calculation.get("nrc") or {}
    subtotal_jpy = int(nrc.get("total_jpy") or 0)
    tax_jpy = int(round(subtotal_jpy * resolved_tax_rate))
    grand_total_jpy = subtotal_jpy + tax_jpy

    estimated_duration_days = float(
        calculation.get("estimated_duration_days")
        or calculation.get("total_effort_days")
        or 0
    )
    role_breakdown = calculation.get("role_breakdown") or []
    phase_breakdown = calculation.get("phase_breakdown") or []
    feature_items = report.get("feature_items") or []

    role_summary, role_subtotal = _build_role_summary(
        role_breakdown,
        estimated_duration_days,
        labels,
    )
    phase_rows, total_effort_days, total_effort_months = _build_phase_effort_rows(
        phase_breakdown,
        role_breakdown,
        labels,
    )
    feature_sections = _build_feature_effort_sections(
        feature_items,
        int(nrc.get("contingency_jpy") or 0),
        int(nrc.get("labor_jpy") or 0),
        float(calculation.get("total_effort_days") or 0),
        labels,
    )

    client_name = report["project_summary"]["client_name"]
    if locale == "ja" and labels["recipient_suffix"]:
        client_display = f"{client_name}　{labels['recipient_suffix']}"
    else:
        client_display = client_name

    return {
        "labels": labels,
        "locale": locale,
        "issue_date": format_date(generated_at, locale),
        "client_name": client_display,
        "intro": labels["intro"],
        "company": {
            "name": settings.quotation_company_name,
            "address": settings.quotation_company_address,
            "contact_person": labels["blank"],
        },
        "project_name": report["project_summary"]["project_name"],
        "subtotal_jpy": subtotal_jpy,
        "tax_jpy": tax_jpy,
        "grand_total_jpy": grand_total_jpy,
        "tax_rate": resolved_tax_rate,
        "role_summary": role_summary,
        "role_subtotal_jpy": role_subtotal,
        "phase_rows": phase_rows,
        "total_effort_days": total_effort_days,
        "total_effort_months": total_effort_months,
        "feature_sections": feature_sections,
        "assumptions": [
            {"number": f"3.{index}", "text": text}
            for index, text in enumerate(labels["assumptions"], start=1)
        ],
        "approval": {
            "company": labels["blank"],
            "approver": labels["blank"],
            "approval_date": labels["blank"],
            "signature": labels["blank"],
        },
        "estimate_id": report["project_summary"]["estimate_id"],
        "export_revision": export_revision,
        "questionnaire_sections": report.get("questionnaire_sections") or [],
        "questionnaire_appendix_title": report["labels"]["questionnaire_appendix"],
    }
