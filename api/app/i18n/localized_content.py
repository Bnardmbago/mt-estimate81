from __future__ import annotations

from copy import deepcopy
from typing import Any

I18N_KEY = "_i18n"
SUPPORTED_LOCALES = ("ja", "en")


def normalize_locale(locale: str | None, fallback: str = "ja") -> str:
    if locale in SUPPORTED_LOCALES:
        return locale
    return fallback if fallback in SUPPORTED_LOCALES else "ja"


def _split_localized_payload(data: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    if not data:
        return {}, {}

    i18n = data.get(I18N_KEY)
    if isinstance(i18n, dict):
        legacy = {key: value for key, value in data.items() if key != I18N_KEY}
        normalized_i18n = {
            locale: dict(values)
            for locale, values in i18n.items()
            if locale in SUPPORTED_LOCALES and isinstance(values, dict)
        }
        return legacy, normalized_i18n

    return dict(data), {}


def resolve_localized_dict(
    data: dict[str, Any] | None,
    display_locale: str,
    fallback_locale: str,
) -> dict[str, Any]:
    legacy, i18n = _split_localized_payload(data)
    display_locale = normalize_locale(display_locale, fallback_locale)
    fallback_locale = normalize_locale(fallback_locale, display_locale)

    for locale in (display_locale, fallback_locale):
        if locale in i18n:
            return dict(i18n[locale])

    if i18n:
        return dict(next(iter(i18n.values())))

    return legacy


def store_localized_dict(
    existing: dict[str, Any] | None,
    content_locale: str,
    content: dict[str, Any],
) -> dict[str, Any]:
    content_locale = normalize_locale(content_locale)
    _, i18n = _split_localized_payload(existing)
    updated_i18n = dict(i18n)
    updated_i18n[content_locale] = dict(content)
    return {I18N_KEY: updated_i18n}


def ensure_localized_dict(
    data: dict[str, Any] | None,
    source_locale: str,
) -> dict[str, Any]:
    legacy, i18n = _split_localized_payload(data)
    source_locale = normalize_locale(source_locale)
    if legacy and source_locale not in i18n:
        i18n = {**i18n, source_locale: legacy}
    if i18n:
        return {I18N_KEY: i18n}
    return {}


def resolve_feature_item_fields(
    *,
    name: str,
    description: str,
    phase: str,
    role: str,
    localizations: dict[str, Any] | None,
    display_locale: str,
    fallback_locale: str,
) -> dict[str, str]:
    display_locale = normalize_locale(display_locale, fallback_locale)
    fallback_locale = normalize_locale(fallback_locale, display_locale)
    locs = localizations if isinstance(localizations, dict) else {}

    for locale in (display_locale, fallback_locale):
        localized = locs.get(locale)
        if isinstance(localized, dict):
            return {
                "name": str(localized.get("name", name)),
                "description": str(localized.get("description", description)),
                "phase": str(localized.get("phase", phase)),
                "role": str(localized.get("role", role)),
            }

    return {
        "name": name,
        "description": description,
        "phase": phase,
        "role": role,
    }


def store_feature_item_localization(
    existing: dict[str, Any] | None,
    content_locale: str,
    *,
    name: str,
    description: str,
    phase: str,
    role: str,
) -> dict[str, Any]:
    content_locale = normalize_locale(content_locale)
    locs = dict(existing or {})
    locs[content_locale] = {
        "name": name,
        "description": description,
        "phase": phase,
        "role": role,
    }
    return locs


def localize_calculation_result(
    result: dict[str, Any] | None,
    display_locale: str,
    fallback_locale: str,
) -> dict[str, Any] | None:
    if not result:
        return None

    localized = deepcopy(result)
    display_locale = normalize_locale(display_locale, fallback_locale)
    fallback_locale = normalize_locale(fallback_locale, display_locale)

    gantt = localized.get("gantt")
    if isinstance(gantt, dict):
        localized["gantt"] = _localize_gantt_payload(gantt, display_locale, fallback_locale)

    return localized


def _localize_gantt_payload(
    gantt: dict[str, Any],
    display_locale: str,
    fallback_locale: str,
) -> dict[str, Any]:
    # Gantt task names/phases are resolved at read time on the frontend for display labels.
    return gantt
