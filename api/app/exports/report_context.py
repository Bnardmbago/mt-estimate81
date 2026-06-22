from datetime import datetime
from typing import Any

from app.ai.schemas import accuracy_level_from_score
from app.calculation.engine import HOURS_PER_EFFORT_DAY, role_personnel_count
from app.config import settings
from app.exports.markdown import (
    LABELS,
    _build_feature_rows,
    format_date,
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


def _accuracy_label(level: str, locale: str) -> str:
    labels = LABELS[locale]
    return labels.get(f"accuracy_{level}", level)


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
    cost_drivers = calculation.get("cost_drivers") or extracted.get("cost_drivers") or []
    total_days = float(calculation.get("total_effort_days") or 0)
    estimated_duration_days = float(
        calculation.get("estimated_duration_days") or total_days or 0
    )
    role_breakdown = _enrich_role_breakdown(
        calculation.get("role_breakdown") or [],
        estimated_duration_days=estimated_duration_days,
        total_days=total_days,
    )

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
        },
        "executive_summary": {
            "nrc_total_jpy": int(nrc.get("total_jpy") or 0),
            "monthly_rc_jpy": int(rc.get("monthly_total_jpy") or 0),
            "annual_rc_jpy": int(rc.get("annual_total_jpy") or 0),
            "first_year_total_jpy": int(calculation.get("first_year_total_jpy") or 0),
            "confidence_score": extracted["confidence_score"],
            "accuracy_level": extracted["accuracy_level"],
            "accuracy_label": _accuracy_label(extracted["accuracy_level"], locale),
        },
        "questionnaire_sections": questionnaire_sections,
        "form_fields": build_flat_form_fields(
            form_data,
            estimate.form_schema_snapshot,
            locale,
        ),
        "extracted": extracted,
        "feature_items": _build_feature_rows(estimate),
        "effort_summary": {
            "total_hours": calculation.get("total_effort_hours", 0),
            "total_days": calculation.get("total_effort_days", 0),
            "estimated_duration_days": calculation.get(
                "estimated_duration_days", calculation.get("total_effort_days", 0)
            ),
            "recommended_team_size": calculation.get("recommended_team_size", 1),
        },
        "calculation": {
            **calculation,
            "phase_breakdown": calculation.get("phase_breakdown") or [],
            "role_breakdown": role_breakdown,
            "nrc_line_items": calculation.get("nrc_line_items") or [],
            "rc_line_items": calculation.get("rc_line_items") or [],
            "role_labor_subtotal_jpy": int(nrc.get("labor_jpy") or 0),
        },
        "cost_drivers": cost_drivers,
        "rate_card_reference": {
            "name": rate_card_name or labels["none"],
            "version_number": rate_card_version_number,
            "effective_date": format_date(rate_card_effective_date, locale)
            if rate_card_effective_date
            else labels["none"],
            "policy_version": settings.calculation_policy_version,
            "rate_card_currency": calculation.get("source_currency"),
            "rate_card_region": calculation.get("source_region"),
            "fx_snapshot": calculation.get("fx_snapshot"),
        },
        "gantt": calculation.get("gantt") or {},
        "gantt_chart_svg": build_gantt_svg(calculation.get("gantt") or {}),
    }
