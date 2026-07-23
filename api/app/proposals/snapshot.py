"""Build point-in-time estimate snapshots for proposals."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from app.i18n.localized_content import resolve_feature_item_fields
from app.models.estimate import Estimate, FeatureItem


ELIGIBLE_STATUSES = frozenset({"calculated", "exported", "completed"})


def compute_source_fingerprint(estimate: Estimate) -> str:
    calc = estimate.calculation_result or {}
    payload = {
        "updated_at": estimate.updated_at.isoformat() if estimate.updated_at else "",
        "status": estimate.status,
        "rate_card_version_id": str(estimate.rate_card_version_id or ""),
        "first_year_total_jpy": calc.get("first_year_total_jpy"),
        "total_effort_hours": calc.get("total_effort_hours"),
        "nrc_total": (calc.get("nrc") or {}).get("total_jpy"),
        "rc_monthly": (calc.get("rc") or {}).get("monthly_total_jpy"),
        "feature_count": len(estimate.feature_items or []),
        "feature_hours": sorted(
            [
                (str(item.id), float(item.hours), item.name)
                for item in (estimate.feature_items or [])
            ]
        ),
    }
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _feature_dict(item: FeatureItem) -> dict[str, Any]:
    localizations = item.localizations if isinstance(item.localizations, dict) else {}
    en = resolve_feature_item_fields(
        name=item.name,
        description=item.description or "",
        phase=item.phase,
        role=item.role,
        localizations=localizations,
        display_locale="en",
        fallback_locale="en",
    )
    ja = resolve_feature_item_fields(
        name=item.name,
        description=item.description or "",
        phase=item.phase,
        role=item.role,
        localizations=localizations,
        display_locale="ja",
        fallback_locale="en",
    )
    return {
        "id": str(item.id),
        "name": item.name,
        "description": item.description or "",
        "hours": float(item.hours),
        "phase": item.phase,
        "role": item.role,
        "localizations": localizations,
        "name_en": en["name"],
        "name_ja": ja["name"],
    }


def feature_label(feature: dict[str, Any], locale: str) -> str:
    if locale == "ja":
        return str(feature.get("name_ja") or feature.get("name") or "")
    return str(feature.get("name_en") or feature.get("name") or "")



def build_source_snapshot(estimate: Estimate) -> dict[str, Any]:
    calc = estimate.calculation_result or {}
    extracted = estimate.extracted_data or {}
    nrc = calc.get("nrc") or {}
    rc = calc.get("rc") or {}

    return {
        "estimate_id": str(estimate.id),
        "project_name": estimate.project_name,
        "client_name": estimate.client_name,
        "status": estimate.status,
        "locale": estimate.locale,
        "project_start_date": (
            estimate.project_start_date.isoformat() if estimate.project_start_date else None
        ),
        "captured_at": datetime.utcnow().isoformat() + "Z",
        "modules": extracted.get("modules") or [],
        "functional_requirements": extracted.get("functional_requirements") or [],
        "non_functional_requirements": extracted.get("non_functional_requirements") or [],
        "user_roles": extracted.get("user_roles") or [],
        "risks": extracted.get("risks") or [],
        "gaps": extracted.get("gaps") or [],
        "assumptions": extracted.get("estimate_exclusions") or [],
        "confidence_notes": extracted.get("confidence_notes") or "",
        "features": [_feature_dict(item) for item in (estimate.feature_items or [])],
        "costs": {
            "one_time_project_cost_jpy": nrc.get("total_jpy"),
            "monthly_recurring_cost_jpy": rc.get("monthly_total_jpy"),
            "annual_recurring_cost_jpy": rc.get("annual_total_jpy"),
            "first_year_total_jpy": calc.get("first_year_total_jpy"),
            "total_effort_hours": calc.get("total_effort_hours"),
            "total_effort_days": calc.get("total_effort_days"),
            "phase_breakdown": calc.get("phase_breakdown") or [],
            "role_breakdown": calc.get("role_breakdown") or [],
        },
        "gantt": calc.get("gantt") or {},
        "rate_card_version_id": str(estimate.rate_card_version_id or ""),
    }
