from datetime import datetime
from typing import Any

from app.ai.schemas import accuracy_level_from_score
from app.calculation.engine import (
    HOURS_PER_EFFORT_DAY,
    filter_active_role_breakdown,
    role_personnel_count,
)
from app.exports.markdown import (
    LABELS,
    _build_feature_rows,
    format_currency,
    format_date,
    format_person_days,
)
from app.exports.export_i18n import (
    localize_calculation_for_export,
    localize_feature_rows,
    localize_gantt,
)
from app.exports.gantt_svg import build_gantt_svg
from app.exports.questionnaire import (
    build_flat_form_fields,
    build_questionnaire_sections,
    resolve_export_extracted,
    resolve_export_form_data,
)
from app.models.estimate import Estimate


def _normalize_extracted(extracted: dict[str, Any]) -> dict[str, Any]:
    score = extracted.get("confidence_score")
    if score is None:
        gaps = extracted.get("gaps") or []
        score = max(30.0, 80.0 - len(gaps) * 10)
    accuracy = extracted.get("accuracy_level")
    if accuracy not in {"high", "medium", "low"}:
        accuracy = accuracy_level_from_score(float(score))

    return {
        "functional_requirements": extracted.get("functional_requirements") or [],
        "non_functional_requirements": extracted.get("non_functional_requirements") or [],
        "user_roles": extracted.get("user_roles") or [],
        "modules": extracted.get("modules") or [],
        "external_systems": extracted.get("external_systems") or [],
        "risks": extracted.get("risks") or [],
        "gaps": extracted.get("gaps") or [],
        "confidence_notes": extracted.get("confidence_notes") or "",
        "confidence_score": float(score),
        "accuracy_level": accuracy,
        "confidence_factors": extracted.get("confidence_factors") or [],
        "missing_inputs": extracted.get("missing_inputs") or [],
        "recommendations": extracted.get("recommendations") or [],
        "estimation_warnings": extracted.get("estimation_warnings") or [],
        "assumption_risks": extracted.get("assumption_risks") or [],
        "estimate_exclusions": extracted.get("estimate_exclusions") or [],
        "estimate_type": extracted.get("estimate_type") or "",
        "cost_drivers": extracted.get("cost_drivers") or [],
    }


def _resolve_estimate_type(extracted: dict[str, Any], form_data: dict[str, Any]) -> str:
    if extracted.get("estimate_type"):
        return str(extracted["estimate_type"])
    for key in (
        "system_type",
        "desired_system",
        "nature_of_work",
        "project_overview",
        "problem_to_solve",
    ):
        value = form_data.get(key)
        if value:
            return str(value)
    return ""


def _enrich_role_breakdown(
    role_breakdown: list[dict[str, Any]],
    *,
    estimated_duration_days: float,
    total_days: float,
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for row in role_breakdown:
        hours = float(row.get("hours") or 0)
        personnel_count = row.get("personnel_count")
        if personnel_count is None:
            personnel_count = role_personnel_count(
                hours,
                estimated_duration_days=estimated_duration_days,
                total_days=total_days,
            )
        enriched.append({**row, "personnel_count": int(personnel_count)})
    return enriched


def build_report_context(
    estimate: Estimate,
    locale: str,
    *,
    generated_at: datetime,
    rate_card_name: str | None,
    rate_card_version_number: int | None,
    rate_card_effective_date: datetime | None,
    export_revision: int,
    export_user_display_name: str | None = None,
) -> dict[str, Any]:
    if locale not in ("ja", "en"):
        raise ValueError(f"Unsupported locale: {locale}")

    labels = LABELS[locale]
    calculation = estimate.calculation_result or {}
    form_data = resolve_export_form_data(estimate, locale)
    extracted = _normalize_extracted(resolve_export_extracted(estimate, locale))
    questionnaire_sections = build_questionnaire_sections(
        form_data,
        estimate.form_schema_snapshot,
        locale,
    )
    nrc = calculation.get("nrc") or {}
    rc = calculation.get("rc") or {}

    estimate_type = _resolve_estimate_type(extracted, form_data)
    total_days = float(calculation.get("total_effort_days") or 0)
    estimated_duration_days = float(
        calculation.get("estimated_duration_days") or total_days or 0
    )
    role_breakdown = filter_active_role_breakdown(
        _enrich_role_breakdown(
            calculation.get("role_breakdown") or [],
            estimated_duration_days=estimated_duration_days,
            total_days=total_days,
        ),
        estimated_duration_days=estimated_duration_days,
        total_days=total_days,
    )
    calculation_payload = {
        **calculation,
        "phase_breakdown": calculation.get("phase_breakdown") or [],
        "role_breakdown": role_breakdown,
        "nrc_line_items": calculation.get("nrc_line_items") or [],
        "rc_line_items": calculation.get("rc_line_items") or [],
        "role_labor_subtotal_jpy": int(round(float(nrc.get("labor_jpy") or 0))),
    }
    calculation_payload = localize_calculation_for_export(calculation_payload, locale)
    feature_items = localize_feature_rows(_build_feature_rows(estimate), locale)
    gantt = localize_gantt(calculation.get("gantt") or {}, locale)

    nrc_total_jpy = int(round(float(nrc.get("total_jpy") or 0)))
    monthly_rc_jpy = int(round(float(rc.get("monthly_total_jpy") or 0)))
    annual_rc_jpy = int(round(float(rc.get("annual_total_jpy") or 0)))
    duration_days = float(
        calculation.get("estimated_duration_days") or calculation.get("total_effort_days") or 0
    )
    creator_display = (export_user_display_name or "").strip() or "—"
    executive_display = {
        "development_cost_jpy": nrc_total_jpy,
        "maintenance_cost_display": (
            f"{format_currency(monthly_rc_jpy)} / {format_currency(annual_rc_jpy)}"
        ),
        "development_period_display": f"{format_person_days(duration_days)} {labels['days']}",
    }

    return {
        "labels": labels,
        "locale": locale,
        "generated_date": format_date(generated_at, locale),
        "project_summary": {
            "project_name": estimate.project_name,
            "client_name": estimate.client_name,
            "estimate_id": str(estimate.id),
            "export_revision": export_revision,
            "estimate_type": estimate_type or labels["none"],
            "generated_date": format_date(generated_at, locale),
            "estimate_creator": creator_display,
        },
        "executive_summary": {
            "nrc_total_jpy": nrc_total_jpy,
            "monthly_rc_jpy": monthly_rc_jpy,
            "annual_rc_jpy": annual_rc_jpy,
            "first_year_total_jpy": int(round(float(calculation.get("first_year_total_jpy") or 0))),
        },
        "executive_display": executive_display,
        "questionnaire_sections": questionnaire_sections,
        "form_fields": build_flat_form_fields(
            form_data,
            estimate.form_schema_snapshot,
            locale,
        ),
        "extracted": extracted,
        "feature_items": feature_items,
        "effort_summary": {
            "total_hours": calculation.get("total_effort_hours", 0),
            "total_days": calculation.get("total_effort_days", 0),
            "estimated_duration_days": calculation.get(
                "estimated_duration_days", calculation.get("total_effort_days", 0)
            ),
            "recommended_team_size": calculation.get("recommended_team_size", 1),
        },
        "calculation": calculation_payload,
        "gantt": gantt,
        "gantt_chart_svg": build_gantt_svg(gantt),
    }
