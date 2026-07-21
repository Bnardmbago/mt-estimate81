"""Translate export narrative text via AI without changing costs or timeline."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.adapter_instructions import AI_TIMEOUT_SECONDS
from app.ai.factory import get_ai_provider
from app.ai.schemas import ExportNarrativeTranslation
from app.estimates.form_fields import TEXT_FIELD_KEYS
from app.i18n.localized_content import (
    has_localized_locale,
    normalize_locale,
    resolve_localized_dict,
    store_feature_item_localization,
    store_localized_dict,
)
from app.models.estimate import Estimate

logger = logging.getLogger(__name__)

FREE_TEXT_FIELD_TYPES = frozenset({"text", "textarea"})

# Spec/header free-text keys when schema snapshots omit type metadata.
KNOWN_FREE_TEXT_KEYS = frozenset(TEXT_FIELD_KEYS) | {
    "problem_to_solve",
    "required_features",
    "scope_boundaries",
    "non_functional_needs",
    "integrations",
    "technology_preferences",
    "rules_and_standards",
    "team_and_resources",
    "risks_unknowns",
    "project_overview",
    "main_functional_needs",
}

EXTRACTED_TEXT_LIST_KEYS = (
    "functional_requirements",
    "non_functional_requirements",
    "user_roles",
    "modules",
    "external_systems",
    "estimate_exclusions",
)


class _TranslateProvider(Protocol):
    async def translate_export_narrative(
        self,
        *,
        source_locale: Literal["ja", "en"],
        target_locale: Literal["ja", "en"],
        payload: dict[str, Any],
    ) -> ExportNarrativeTranslation: ...


def free_text_form_keys(schema: list[dict[str, Any]] | None) -> list[str]:
    """Return free-text questionnaire keys without full schema validation."""
    keys: list[str] = []
    seen: set[str] = set()
    for field in schema or []:
        key = str(field.get("key") or "").strip()
        if not key or key in seen:
            continue
        field_type = str(field.get("type") or "").strip()
        if field_type in FREE_TEXT_FIELD_TYPES or (
            not field_type and key in KNOWN_FREE_TEXT_KEYS
        ):
            keys.append(key)
            seen.add(key)
    if keys:
        return keys
    return sorted(KNOWN_FREE_TEXT_KEYS)


def features_missing_locale(estimate: Estimate, target_locale: str) -> list[Any]:
    target_locale = normalize_locale(target_locale)
    missing: list[Any] = []
    for item in estimate.feature_items or []:
        locs = getattr(item, "localizations", None) or {}
        if not isinstance(locs, dict) or target_locale not in locs:
            missing.append(item)
    return missing


def needs_export_narrative_translation(estimate: Estimate, target_locale: str) -> bool:
    target_locale = normalize_locale(target_locale, getattr(estimate, "locale", None) or "ja")
    source_locale = normalize_locale(getattr(estimate, "locale", None) or "ja")

    form_missing = not has_localized_locale(estimate.form_data, target_locale)
    extracted_missing = not has_localized_locale(estimate.extracted_data, target_locale)
    features_missing = features_missing_locale(estimate, target_locale)

    if not form_missing and not extracted_missing and not features_missing:
        return False

    source_form = resolve_localized_dict(estimate.form_data, source_locale, source_locale)
    source_extracted = resolve_localized_dict(
        estimate.extracted_data, source_locale, source_locale
    )

    if form_missing:
        for key in free_text_form_keys(getattr(estimate, "form_schema_snapshot", None)):
            value = source_form.get(key)
            if value is not None and str(value).strip():
                return True

    if extracted_missing:
        if any(source_extracted.get(key) for key in EXTRACTED_TEXT_LIST_KEYS):
            return True
        if str(source_extracted.get("estimate_type") or "").strip():
            return True

    if features_missing:
        return True

    return False


def build_export_translation_request(
    estimate: Estimate,
    target_locale: str,
) -> dict[str, Any] | None:
    target_locale = normalize_locale(target_locale)
    source_locale = normalize_locale(getattr(estimate, "locale", None) or "ja")
    if not needs_export_narrative_translation(estimate, target_locale):
        return None

    source_form = resolve_localized_dict(estimate.form_data, source_locale, source_locale)
    source_extracted = resolve_localized_dict(
        estimate.extracted_data, source_locale, source_locale
    )

    translate_form = not has_localized_locale(estimate.form_data, target_locale)
    translate_extracted = not has_localized_locale(estimate.extracted_data, target_locale)
    missing_features = features_missing_locale(estimate, target_locale)

    form_fields: dict[str, str] = {}
    if translate_form:
        for key in free_text_form_keys(getattr(estimate, "form_schema_snapshot", None)):
            value = source_form.get(key)
            if value is None or value == "":
                continue
            form_fields[key] = str(value)

    features_payload: list[dict[str, str]] = [
        {
            "id": str(item.id),
            "name": str(item.name or ""),
            "description": str(item.description or ""),
        }
        for item in missing_features
    ]

    extracted_lists: dict[str, list[str]] = {key: [] for key in EXTRACTED_TEXT_LIST_KEYS}
    estimate_type = ""
    if translate_extracted:
        for key in EXTRACTED_TEXT_LIST_KEYS:
            values = source_extracted.get(key) or []
            if isinstance(values, list):
                extracted_lists[key] = [str(v) for v in values]
        estimate_type = str(source_extracted.get("estimate_type") or "")

    if not form_fields and not features_payload and not translate_extracted:
        return None
    if translate_extracted and not any(extracted_lists.values()) and not estimate_type and not form_fields and not features_payload:
        return None

    return {
        "source_locale": source_locale,
        "target_locale": target_locale,
        "form_fields": form_fields,
        "features": features_payload,
        **extracted_lists,
        "estimate_type": estimate_type,
        "translate_form": translate_form and bool(form_fields),
        "translate_extracted": translate_extracted,
        "translate_features": bool(features_payload),
    }


def apply_export_narrative_translation(
    estimate: Estimate,
    target_locale: str,
    translation: ExportNarrativeTranslation,
    *,
    translate_form: bool = True,
    translate_extracted: bool = True,
    translate_features: bool = True,
) -> None:
    target_locale = normalize_locale(target_locale)
    source_locale = normalize_locale(getattr(estimate, "locale", None) or "ja")

    if translate_form and translation.form_fields:
        source_form = resolve_localized_dict(estimate.form_data, source_locale, source_locale)
        merged = dict(source_form)
        for field in translation.form_fields:
            if field.key:
                merged[field.key] = field.value
        estimate.form_data = store_localized_dict(estimate.form_data, target_locale, merged)

    if translate_extracted:
        source_extracted = resolve_localized_dict(
            estimate.extracted_data, source_locale, source_locale
        )
        merged_extracted = dict(source_extracted)
        merged_extracted["functional_requirements"] = list(translation.functional_requirements)
        merged_extracted["non_functional_requirements"] = list(
            translation.non_functional_requirements
        )
        merged_extracted["user_roles"] = list(translation.user_roles)
        merged_extracted["modules"] = list(translation.modules)
        merged_extracted["external_systems"] = list(translation.external_systems)
        merged_extracted["estimate_exclusions"] = list(translation.estimate_exclusions)
        if translation.estimate_type:
            merged_extracted["estimate_type"] = translation.estimate_type
        estimate.extracted_data = store_localized_dict(
            estimate.extracted_data, target_locale, merged_extracted
        )

    if translate_features and translation.features:
        by_id = {str(item.id): item for item in estimate.feature_items or []}
        for translated in translation.features:
            item = by_id.get(translated.id)
            if item is None:
                continue
            item.localizations = store_feature_item_localization(
                getattr(item, "localizations", None),
                target_locale,
                name=translated.name,
                description=translated.description,
                phase=str(item.phase or ""),
                role=str(item.role or ""),
            )


async def ensure_export_narrative_locale(
    db: AsyncSession,
    estimate: Estimate,
    target_locale: str,
    *,
    provider: _TranslateProvider | None = None,
) -> bool:
    """Translate and persist missing narrative locale. Returns True if AI ran successfully."""
    target_locale = normalize_locale(target_locale)
    request = build_export_translation_request(estimate, target_locale)
    if request is None:
        return False

    source_locale: Literal["ja", "en"] = request["source_locale"]  # type: ignore[assignment]
    target: Literal["ja", "en"] = request["target_locale"]  # type: ignore[assignment]

    ai = provider or await get_ai_provider(db)
    try:
        translation = await asyncio.wait_for(
            ai.translate_export_narrative(
                source_locale=source_locale,
                target_locale=target,
                payload=request,
            ),
            timeout=AI_TIMEOUT_SECONDS + 30,
        )
    except Exception:
        logger.exception(
            "Export narrative translation failed for estimate %s (%s→%s); using source locale",
            getattr(estimate, "id", None),
            source_locale,
            target,
        )
        return False

    apply_export_narrative_translation(
        estimate,
        target,
        translation,
        translate_form=bool(request.get("translate_form")),
        translate_extracted=bool(request.get("translate_extracted")),
        translate_features=bool(request.get("translate_features")),
    )
    return True
