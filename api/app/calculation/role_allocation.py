"""Reallocate feature hours across roles to match rate-card phase percentages."""

from collections import defaultdict

from app.calculation.schemas import FeatureItemInput, RateCardSettings

# Phases that should drive role hours when feature items omit that role.
PHASE_DEFAULT_ROLE_HINTS: dict[str, tuple[str, ...]] = {
    "requirement": ("pm", "project manager", "project_manager"),
    "testing": ("qa", "qa engineer", "tester"),
}

# Fallback hints when mapping AI/free-text roles onto rate-card role names.
PHASE_ROLE_RESOLUTION_HINTS: dict[str, tuple[str, ...]] = {
    "requirement": ("pm", "project manager", "project_manager"),
    "design": ("designer", "developer", "ui", "ux"),
    "development": ("developer", "dev", "engineer"),
    "testing": ("qa", "qa engineer", "tester"),
    "deployment": ("devops", "developer", "pm"),
}


def _normalize_key(value: str) -> str:
    return value.strip().lower().replace("_", " ")


def _phase_key(phase: str) -> str:
    normalized = _normalize_key(phase)
    aliases = {
        "requirements": "requirement",
        "analysis": "requirement",
        "implementation": "development",
        "dev": "development",
        "test": "testing",
        "qa": "testing",
        "deploy": "deployment",
        "devops": "deployment",
    }
    return aliases.get(normalized, normalized)


def _role_matches_hint(role_name: str, hints: tuple[str, ...]) -> bool:
    normalized = _normalize_key(role_name)
    if normalized in hints:
        return True
    return any(hint in normalized for hint in hints)


ROLE_ALIAS_TERMS: tuple[str, ...] = (
    "designer",
    "design",
    "ui",
    "ux",
    "dev",
    "developer",
    "engineer",
    "pm",
    "project manager",
    "qa",
    "test",
    "tester",
    "devops",
    "analyst",
    "architect",
)


def _looks_like_role_alias(role: str) -> bool:
    normalized = _normalize_key(role)
    return any(term in normalized for term in ROLE_ALIAS_TERMS)


def resolve_rate_card_role(role_rates: dict[str, int], hints: tuple[str, ...]) -> str | None:
    for role_name in role_rates:
        if _role_matches_hint(role_name, hints):
            return role_name
    return None


def resolve_support_role_hourly_rate(
    role_rates: dict[str, int],
    support_role_hint: str | None = None,
) -> tuple[str | None, int]:
    """Resolve maintenance support role to an exact rate-card role name and hourly rate."""
    hint = _normalize_key(str(support_role_hint or "developer"))
    normalized_map = {_normalize_key(name): name for name in role_rates}

    if hint in normalized_map:
        role_name = normalized_map[hint]
        return role_name, role_rates[role_name]

    resolved = resolve_rate_card_role(role_rates, (hint,))
    if resolved is not None:
        return resolved, role_rates[resolved]

    for fallback in ("developer", "dev", "engineer", "pm", "project manager"):
        resolved = resolve_rate_card_role(role_rates, (fallback,))
        if resolved is not None:
            return resolved, role_rates[resolved]

    return None, 0


def resolve_feature_item_role(
    role: str,
    role_rates: dict[str, int],
    *,
    phase: str = "",
) -> str | None:
    """Map a feature-item role label to an exact rate-card role name."""
    if not role.strip():
        return None

    normalized_roles = {_normalize_key(name): name for name in role_rates}

    normalized_role = _normalize_key(role)
    if normalized_role in normalized_roles:
        return normalized_roles[normalized_role]

    for token in [part.strip() for part in role.replace(",", "/").split("/") if part.strip()]:
        token_key = _normalize_key(token)
        if token_key in normalized_roles:
            return normalized_roles[token_key]
        resolved = resolve_rate_card_role(role_rates, (token_key,))
        if resolved:
            return resolved
        for rate_card_role in role_rates:
            rate_card_key = _normalize_key(rate_card_role)
            if rate_card_key in token_key.split() or token_key == rate_card_key:
                return rate_card_role

    resolved = resolve_rate_card_role(role_rates, (normalized_role,))
    if resolved:
        return resolved

    from app.rate_cards.regional_profiles import role_canonical_keys

    feature_keys = role_canonical_keys(role)
    if feature_keys:
        for rate_card_role in role_rates:
            if feature_keys & role_canonical_keys(rate_card_role):
                return rate_card_role

    phase_hints = PHASE_ROLE_RESOLUTION_HINTS.get(_phase_key(phase))
    if phase_hints and _looks_like_role_alias(role):
        return resolve_rate_card_role(role_rates, phase_hints)

    return None


def _donor_role(role_hours: dict[str, float], *, exclude: str) -> str | None:
    candidates = [
        (role, hours)
        for role, hours in role_hours.items()
        if role != exclude and hours > 0
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[1], reverse=True)
    return candidates[0][0]


def allocate_role_hours_from_phases(
    feature_items: list[FeatureItemInput],
    rate_card: RateCardSettings,
    role_hours: dict[str, float],
    total_hours: float,
    effort_multiplier: float,
) -> dict[str, float]:
    """Shift hours between roles so each phase's default role covers its share."""
    if total_hours <= 0:
        return role_hours

    role_rates = {role.name: 1 for role in rate_card.roles}
    allocated = dict(role_hours)

    phase_role_hours: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for item in feature_items:
        adjusted = round(float(item.hours) * effort_multiplier, 2)
        phase_role_hours[_phase_key(item.phase)][_normalize_key(item.role)] += adjusted

    for phase in rate_card.phases:
        phase_key = _phase_key(phase.name)
        hints = PHASE_DEFAULT_ROLE_HINTS.get(phase_key)
        if not hints:
            continue

        target_role = resolve_rate_card_role(role_rates, hints)
        if not target_role:
            continue

        expected_hours = round(total_hours * phase.percentage, 2)
        if expected_hours <= 0:
            continue

        target_key = _normalize_key(target_role)
        assigned_to_target = phase_role_hours[phase_key].get(target_key, 0.0)
        shortfall = round(expected_hours - assigned_to_target, 2)
        if shortfall <= 0:
            continue

        donor = _donor_role(allocated, exclude=target_role)
        if donor is None:
            continue

        transfer = min(shortfall, allocated.get(donor, 0.0))
        if transfer <= 0:
            continue

        allocated[donor] = round(allocated[donor] - transfer, 2)
        allocated[target_role] = round(allocated.get(target_role, 0.0) + transfer, 2)

    return allocated
