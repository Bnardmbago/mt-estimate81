from typing import Any, Literal

from pydantic import BaseModel, Field

ComplexityLevel = Literal["low", "medium", "high"]

PHASE_GUIDANCE: dict[ComplexityLevel, dict[str, float]] = {
    "low": {
        "requirement": 0.08,
        "design": 0.12,
        "development": 0.50,
        "testing": 0.20,
        "deployment": 0.10,
    },
    "medium": {
        "requirement": 0.10,
        "design": 0.15,
        "development": 0.40,
        "testing": 0.25,
        "deployment": 0.10,
    },
    "high": {
        "requirement": 0.12,
        "design": 0.18,
        "development": 0.35,
        "testing": 0.27,
        "deployment": 0.08,
    },
}

NRC_RC_GUIDANCE: dict[ComplexityLevel, dict[str, Any]] = {
    "low": {
        "setup_categories": ["Infrastructure", "Tooling"],
        "monthly_categories": ["hosting"],
        "relative_scale": "minimal",
        "notes": "Basic environment setup and standard hosting only.",
    },
    "medium": {
        "setup_categories": [
            "Infrastructure",
            "Tooling",
            "Third-party integration",
            "Environment setup",
        ],
        "monthly_categories": ["hosting", "monitoring", "SaaS subscriptions"],
        "relative_scale": "moderate",
        "notes": "Include integration setup and operational tooling.",
    },
    "high": {
        "setup_categories": [
            "Infrastructure",
            "Tooling",
            "Third-party integration",
            "Security audit",
            "Data migration",
            "License fees",
        ],
        "monthly_categories": [
            "hosting",
            "monitoring",
            "support retainer",
            "SaaS subscriptions",
            "security operations",
        ],
        "relative_scale": "substantial",
        "notes": "Enterprise-grade setup, integrations, security, and ongoing operations.",
    },
}


class ProjectComplexityProfile(BaseModel):
    overall_score: float = Field(ge=0, le=100)
    level: ComplexityLevel
    feature_count: int = Field(ge=0)
    total_hours: float = Field(ge=0)
    integration_count: int = Field(ge=0)
    non_functional_count: int = Field(ge=0)
    module_count: int = Field(ge=0)
    risk_count: int = Field(ge=0)
    cost_driver_count: int = Field(ge=0)
    cost_driver_impact_jpy: int = Field(ge=0)
    form_signals: dict[str, str] = Field(default_factory=dict)
    drivers: list[str] = Field(default_factory=list)
    phase_guidance: dict[str, float] = Field(default_factory=dict)
    nrc_rc_guidance: dict[str, Any] = Field(default_factory=dict)


def _complexity_level(score: float) -> ComplexityLevel:
    if score < 35:
        return "low"
    if score <= 65:
        return "medium"
    return "high"


def _form_complexity_points(value: str | None) -> int:
    if not value:
        return 0
    normalized = value.strip().casefold()
    if normalized in ("low", "simple", "basic"):
        return 1
    if normalized in ("moderate", "medium", "normal"):
        return 3
    if normalized in ("high", "complex", "advanced"):
        return 5
    return 2


def _feature_count_points(count: int) -> int:
    if count <= 0:
        return 0
    if count <= 5:
        return 8
    if count <= 10:
        return 15
    if count <= 20:
        return 20
    return 25


def _hours_points(total_hours: float) -> int:
    if total_hours <= 0:
        return 0
    if total_hours <= 80:
        return 5
    if total_hours <= 200:
        return 10
    if total_hours <= 500:
        return 15
    return 20


def _integration_points(integration_count: int) -> int:
    if integration_count <= 0:
        return 0
    if integration_count == 1:
        return 8
    if integration_count <= 3:
        return 14
    if integration_count <= 5:
        return 18
    return 20


def _count_form_integrations(form_data: dict[str, Any]) -> int:
    integrations = form_data.get("integrations")
    count = 0
    if integrations:
        if isinstance(integrations, list):
            count = len([item for item in integrations if str(item).strip()])
        else:
            text = str(integrations).strip()
            if text and text.casefold() not in ("none", "n/a", "なし"):
                separators = [",", ";", "\n", "、", "・"]
                for separator in separators:
                    if separator in text:
                        count = len([part for part in text.split(separator) if part.strip()])
                        break
                else:
                    count = 1
    explicit = form_data.get("integration_count")
    if explicit is not None:
        digits = "".join(char for char in str(explicit) if char.isdigit())
        if digits:
            count = max(count, int(digits))
    return count


def score_project_complexity(
    *,
    feature_items: list[dict[str, Any]],
    extracted_data: dict[str, Any],
    form_data: dict[str, Any] | None = None,
) -> ProjectComplexityProfile:
    form_data = form_data or {}

    feature_count = len(feature_items)
    total_hours = sum(float(item.get("hours", 0) or 0) for item in feature_items)

    external_systems = extracted_data.get("external_systems") or []
    if not isinstance(external_systems, list):
        external_systems = []
    integration_count = len(external_systems) + _count_form_integrations(form_data)

    non_functional = extracted_data.get("non_functional_requirements") or []
    if not isinstance(non_functional, list):
        non_functional = []

    modules = extracted_data.get("modules") or []
    if not isinstance(modules, list):
        modules = []

    risks = extracted_data.get("risks") or []
    gaps = extracted_data.get("gaps") or []
    if not isinstance(risks, list):
        risks = []
    if not isinstance(gaps, list):
        gaps = []
    risk_count = len(risks) + len(gaps)

    cost_drivers = extracted_data.get("cost_drivers") or []
    if not isinstance(cost_drivers, list):
        cost_drivers = []
    cost_driver_impact = 0
    for driver in cost_drivers:
        if isinstance(driver, dict):
            impact = int(driver.get("impact_jpy", 0) or 0)
            # Signed impacts: positive = cost increase; ignore reductions for profile totals.
            if impact > 0:
                cost_driver_impact += impact

    data_complexity = str(form_data.get("data_complexity", "") or "")
    ui_complexity = str(form_data.get("ui_complexity", "") or "")
    auth_complexity = str(form_data.get("auth_complexity", "") or "")
    compliance_level = str(form_data.get("compliance_level", "") or "")
    data_migration = str(form_data.get("data_migration_needed", "") or "")
    form_signals = {
        key: value
        for key, value in {
            "data_complexity": data_complexity,
            "ui_complexity": ui_complexity,
            "auth_complexity": auth_complexity,
            "compliance_level": compliance_level,
            "data_migration_needed": data_migration,
        }.items()
        if value and value.casefold() not in {"undecided", "none", "no"}
    }
    form_points = _form_complexity_points(data_complexity) + _form_complexity_points(ui_complexity)
    if auth_complexity.casefold() in {"sso", "multi_tenant"}:
        form_points += 4
    elif auth_complexity.casefold() == "simple_login":
        form_points += 2
    if compliance_level.casefold() == "regulated":
        form_points += 5
    elif compliance_level.casefold() == "standard":
        form_points += 3
    if data_migration.casefold() == "yes_major":
        form_points += 4
    elif data_migration.casefold() == "yes_limited":
        form_points += 2

    module_points = min(len(modules), 5)
    risk_points = min(risk_count, 5)
    nfr_points = min(len(non_functional) * 3, 15)

    score = (
        _feature_count_points(feature_count)
        + _hours_points(total_hours)
        + _integration_points(integration_count)
        + nfr_points
        + form_points
        + module_points
        + risk_points
    )
    overall_score = float(min(score, 100))
    level = _complexity_level(overall_score)

    drivers: list[str] = []
    if feature_count:
        drivers.append(f"{feature_count} feature items ({total_hours:.0f}h total)")
    if integration_count:
        drivers.append(f"{integration_count} integration(s)")
    if non_functional:
        drivers.append(f"{len(non_functional)} non-functional requirement(s)")
    if modules:
        drivers.append(f"{len(modules)} module(s)")
    if risk_count:
        drivers.append(f"{risk_count} risk/gap item(s)")
    if form_signals:
        drivers.append(
            "form complexity: "
            + ", ".join(f"{key}={value}" for key, value in form_signals.items())
        )
    if cost_drivers:
        drivers.append(f"{len(cost_drivers)} cost driver(s)")

    return ProjectComplexityProfile(
        overall_score=overall_score,
        level=level,
        feature_count=feature_count,
        total_hours=round(total_hours, 2),
        integration_count=integration_count,
        non_functional_count=len(non_functional),
        module_count=len(modules),
        risk_count=risk_count,
        cost_driver_count=len(cost_drivers),
        cost_driver_impact_jpy=cost_driver_impact,
        form_signals=form_signals,
        drivers=drivers,
        phase_guidance=dict(PHASE_GUIDANCE[level]),
        nrc_rc_guidance=dict(NRC_RC_GUIDANCE[level]),
    )
