"""Bilingual translation and validation for presentation preset payloads."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.adapter_instructions import AI_TIMEOUT_SECONDS
from app.ai.factory import get_ai_provider
from app.i18n.localized_content import (
    has_localized_locale,
    normalize_locale,
    resolve_localized_dict,
    store_localized_dict,
)

_LOCALES = ("en", "ja")


class PresentationTranslationError(ValueError):
    """Raised when a preset cannot be made safely bilingual."""


async def ensure_preset_bilingual(
    db: AsyncSession,
    payload: dict[str, Any],
    *,
    content_locale: str,
) -> dict[str, Any]:
    """Return a copy with explicit EN/JA metadata and cover-field content."""
    source_locale = normalize_locale(content_locale)
    target_locale = "ja" if source_locale == "en" else "en"
    result = deepcopy(payload)

    metadata = _prepare_metadata(result, source_locale)
    fields = _cover_fields(result)
    for field in fields:
        _prepare_cover_content(field, source_locale)

    source_errors = _source_locale_errors(
        metadata=metadata,
        fields=fields,
        source_locale=source_locale,
    )
    if source_errors:
        raise PresentationTranslationError(
            "Bilingual activation blocked: " + "; ".join(source_errors)
        )

    missing = _missing_translations(
        metadata=metadata,
        fields=fields,
        source_locale=source_locale,
        target_locale=target_locale,
    )
    translated: dict[str, str] = {}
    text_to_translate = {key: value for key, value in missing.items() if value}
    if text_to_translate:
        try:
            provider = await get_ai_provider(db)
            response = await asyncio.wait_for(
                provider.translate_export_narrative(
                    source_locale=source_locale,
                    target_locale=target_locale,
                    payload={"form_fields": text_to_translate},
                ),
                timeout=AI_TIMEOUT_SECONDS + 30,
            )
        except Exception as exc:
            raise PresentationTranslationError(
                f"Bilingual translation failed ({source_locale}→{target_locale}): {exc}"
            ) from exc
        translated = {
            item.key: item.value
            for item in response.form_fields
            if item.key in text_to_translate
        }
        omitted = [
            key
            for key, source_value in text_to_translate.items()
            if not str(translated.get(key) or "").strip() and str(source_value).strip()
        ]
        if omitted:
            raise PresentationTranslationError(
                "Bilingual translation failed: provider omitted "
                + ", ".join(sorted(omitted))
            )

    target_metadata = resolve_localized_dict(metadata, target_locale, source_locale)
    target_metadata.update(
        {
            key: translated.get(key, "")
            for key in ("name", "description")
            if key in missing
        }
    )
    result["content"] = store_localized_dict(metadata, target_locale, target_metadata)

    for field in fields:
        key = str(field.get("key") or "")
        content = field["content"]
        target_content = resolve_localized_dict(content, target_locale, source_locale)
        for content_key in ("label", "default_text"):
            path = f"cover_fields.{key}.{content_key}"
            if path in missing:
                target_content[content_key] = translated.get(path, "")
        field["content"] = store_localized_dict(content, target_locale, target_content)

    errors = bilingual_validation_errors(result)
    if errors:
        raise PresentationTranslationError(
            "Bilingual translation failed: " + "; ".join(errors)
        )
    return result


def bilingual_validation_errors(payload: dict[str, Any]) -> list[str]:
    """List missing bilingual fields that must block activation."""
    errors: list[str] = []
    metadata = payload.get("content")
    if not isinstance(metadata, dict):
        return ["preset name/description localization is missing"]

    for locale in _LOCALES:
        if not has_localized_locale(metadata, locale):
            errors.append(f"preset content is missing locale '{locale}'")
            continue
        values = resolve_localized_dict(metadata, locale, locale)
        if not str(values.get("name") or "").strip():
            errors.append(f"preset name is missing for locale '{locale}'")
        if "description" not in values:
            errors.append(f"preset description is missing for locale '{locale}'")

    for field in _cover_fields(payload):
        key = str(field.get("key") or "<unknown>")
        content = field.get("content")
        if not isinstance(content, dict):
            errors.append(f"cover field '{key}' content is missing")
            continue
        locale_values = {
            locale: resolve_localized_dict(content, locale, locale)
            for locale in _LOCALES
        }
        default_required = any(
            "default_text" in values for values in locale_values.values()
        )
        for locale, values in locale_values.items():
            if not has_localized_locale(content, locale):
                errors.append(f"cover field '{key}' is missing locale '{locale}'")
                continue
            if not str(values.get("label") or "").strip():
                errors.append(
                    f"cover field '{key}' label is missing for locale '{locale}'"
                )
            if default_required and "default_text" not in values:
                errors.append(
                    f"cover field '{key}' default_text is missing for locale '{locale}'"
                )
    return errors


def _prepare_metadata(payload: dict[str, Any], source_locale: str) -> dict[str, Any]:
    existing = payload.get("content")
    content = existing if isinstance(existing, dict) else {}
    source = resolve_localized_dict(content, source_locale, source_locale)
    # Prefer non-empty localized values, then top-level payload fields.
    source["name"] = str(source.get("name") or payload.get("name") or "").strip()
    source["description"] = str(
        source.get("description")
        if source.get("description") is not None
        else (payload.get("description") or "")
    )
    localized = store_localized_dict(content, source_locale, source)
    payload["content"] = localized
    payload["name"] = source["name"]
    payload["description"] = source["description"]
    return localized


def _cover_fields(payload: dict[str, Any]) -> list[dict[str, Any]]:
    config = payload.get("config")
    if not isinstance(config, dict):
        return []
    fields = config.get("cover_fields")
    if not isinstance(fields, list):
        return []
    return [field for field in fields if isinstance(field, dict)]


def _prepare_cover_content(field: dict[str, Any], source_locale: str) -> None:
    existing = field.get("content")
    content = existing if isinstance(existing, dict) else {}
    source = resolve_localized_dict(content, source_locale, source_locale)
    for key in ("label", "default_text"):
        if key not in source and key in field:
            source[key] = field[key]
    field["content"] = store_localized_dict(content, source_locale, source)


def _source_locale_errors(
    *,
    metadata: dict[str, Any],
    fields: list[dict[str, Any]],
    source_locale: str,
) -> list[str]:
    """Validate source-locale content that translation cannot invent."""
    errors: list[str] = []
    source_metadata = resolve_localized_dict(metadata, source_locale, source_locale)
    if not str(source_metadata.get("name") or "").strip():
        errors.append(f"preset name is required for locale '{source_locale}'")

    for field in fields:
        key = str(field.get("key") or "<unknown>")
        content = field.get("content")
        if not isinstance(content, dict):
            errors.append(f"cover field '{key}' content is missing")
            continue
        source = resolve_localized_dict(content, source_locale, source_locale)
        if not str(source.get("label") or "").strip():
            errors.append(
                f"cover field '{key}' label is required for locale '{source_locale}'"
            )
    return errors


def _missing_translations(
    *,
    metadata: dict[str, Any],
    fields: list[dict[str, Any]],
    source_locale: str,
    target_locale: str,
) -> dict[str, str]:
    missing: dict[str, str] = {}
    source_metadata = resolve_localized_dict(metadata, source_locale, source_locale)
    target_metadata = (
        resolve_localized_dict(metadata, target_locale, target_locale)
        if has_localized_locale(metadata, target_locale)
        else {}
    )
    for key in ("name", "description"):
        if key not in target_metadata:
            missing[key] = str(source_metadata.get(key) or "")

    for field in fields:
        key = str(field.get("key") or "")
        content = field["content"]
        source = resolve_localized_dict(content, source_locale, source_locale)
        target = (
            resolve_localized_dict(content, target_locale, target_locale)
            if has_localized_locale(content, target_locale)
            else {}
        )
        required_keys = ["label"]
        if "default_text" in source or "default_text" in target:
            required_keys.append("default_text")
        for content_key in required_keys:
            if content_key not in target:
                missing[f"cover_fields.{key}.{content_key}"] = str(
                    source.get(content_key) or ""
                )
    return missing
