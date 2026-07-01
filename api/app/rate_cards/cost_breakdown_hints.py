from __future__ import annotations

import re
from typing import Any


def _non_empty(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _split_integrations(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    parts = re.split(r"[,;\n]+", text)
    return [part.strip() for part in parts if part.strip()]


def _append_unique(target: list[str], values: list[str]) -> None:
    seen = {item.casefold() for item in target}
    for value in values:
        key = value.casefold()
        if key not in seen:
            target.append(value)
            seen.add(key)


def build_cost_breakdown_hints(
    form_data: dict[str, Any],
    extracted_data: dict[str, Any] | None,
    complexity_profile: dict[str, Any] | None,
) -> dict[str, Any]:
    setup_suggestions: list[str] = []
    monthly_suggestions: list[str] = []
    signals: dict[str, Any] = {}

    integrations = _split_integrations(form_data.get("integrations"))
    if extracted_data:
        external_systems = [
            str(item).strip()
            for item in (extracted_data.get("external_systems") or [])
            if str(item).strip()
        ]
        _append_unique(integrations, external_systems)
    if integrations:
        signals["integrations"] = integrations
        setup_suggestions.append(
            f"Third-party integration setup ({len(integrations)} system(s)): "
            + ", ".join(integrations[:6])
        )
        monthly_suggestions.append("Integration middleware / API usage fees")

    maintenance = _non_empty(form_data.get("maintenance_support"))
    if maintenance:
        signals["maintenance_support"] = maintenance
        monthly_suggestions.append(f"Maintenance and support aligned with: {maintenance}")

    payment = _non_empty(form_data.get("payment_needed"))
    if payment and payment.casefold() not in {"no", "none", "undecided"}:
        signals["payment_needed"] = payment
        setup_suggestions.append("Payment gateway / PCI compliance setup")
        monthly_suggestions.append("Payment processing fees / gateway subscription")

    user_count = _non_empty(form_data.get("expected_user_count"))
    if user_count:
        signals["expected_user_count"] = user_count
        monthly_suggestions.append(
            f"Cloud infrastructure scaled for expected users ({user_count})"
        )

    non_functional = _non_empty(form_data.get("non_functional_needs"))
    if non_functional:
        signals["non_functional_needs"] = non_functional
        lowered = non_functional.casefold()
        if any(token in lowered for token in ("security", "compliance", "audit", "encryption")):
            setup_suggestions.append("Security hardening and compliance setup")
            monthly_suggestions.append("Security monitoring and vulnerability management")
        if any(token in lowered for token in ("availability", "uptime", "sla", "monitor")):
            monthly_suggestions.append("24/7 system monitoring and incident response")
        if any(token in lowered for token in ("backup", "disaster", "recovery", "dr")):
            monthly_suggestions.append("Backup and disaster recovery")

    technology = _non_empty(form_data.get("technology_preferences"))
    if technology:
        signals["technology_preferences"] = technology
        setup_suggestions.append(f"Environment and tooling for {technology}")
        lowered = technology.casefold()
        if any(token in lowered for token in ("aws", "gcp", "azure", "cloud")):
            monthly_suggestions.append("Cloud infrastructure hosting")
        if any(token in lowered for token in ("saas", "subscription", "license")):
            monthly_suggestions.append("SaaS / license subscriptions")

    if complexity_profile:
        guidance = complexity_profile.get("nrc_rc_guidance")
        if isinstance(guidance, dict) and guidance:
            signals["nrc_rc_guidance"] = guidance
            for category in guidance.get("setup_categories") or []:
                text = str(category).strip()
                if text:
                    setup_suggestions.append(text)
            for category in guidance.get("monthly_categories") or []:
                text = str(category).strip()
                if text:
                    monthly_suggestions.append(text)
            notes = _non_empty(guidance.get("notes"))
            if notes:
                signals["complexity_notes"] = notes

    deduped_setup: list[str] = []
    deduped_monthly: list[str] = []
    _append_unique(deduped_setup, setup_suggestions)
    _append_unique(deduped_monthly, monthly_suggestions)

    return {
        "setup_suggestions": deduped_setup,
        "monthly_suggestions": deduped_monthly,
        "signals": signals,
    }
