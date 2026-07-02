from typing import Any

from app.estimates.form_fields import (
    OPTION_LABELS,
    header_schema,
    option_label_for_field,
    specification_schema,
    snapshot_fields,
)
from app.exports.markdown import LABELS
from app.i18n.localized_content import resolve_localized_dict
from app.models.estimate import Estimate


def resolve_export_form_data(estimate: Estimate, locale: str) -> dict[str, Any]:
    fallback = getattr(estimate, "locale", None) or "ja"
    return resolve_localized_dict(estimate.form_data, locale, fallback)


def resolve_export_extracted(estimate: Estimate, locale: str) -> dict[str, Any]:
    fallback = getattr(estimate, "locale", None) or "ja"
    return resolve_localized_dict(estimate.extracted_data, locale, fallback)


def format_field_value(field_schema: dict[str, Any], raw_value: Any, locale: str) -> str:
    if raw_value is None or raw_value == "":
        return ""
    if field_schema.get("type") == "select":
        value_str = str(raw_value)
        field_key = str(field_schema.get("key", ""))
        for option in field_schema.get("options") or []:
            if option.get("value") == value_str:
                label_map = option.get("label") or {}
                return label_map.get(locale) or label_map.get("en") or value_str
        if field_key:
            return option_label_for_field(field_key, value_str, locale)
        fallback = OPTION_LABELS.get(value_str)
        if fallback:
            return fallback.get(locale) or fallback.get("en") or value_str
        return value_str
    return str(raw_value)


def _build_section_fields(
    fields: list[dict[str, Any]],
    form_data: dict[str, Any],
    locale: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for field in sorted(fields, key=lambda item: item.get("sort_order", 0)):
        key = field["key"]
        raw_value = form_data.get(key)
        if raw_value is None or raw_value == "":
            continue
        label_map = field.get("label") or {}
        label = label_map.get(locale) or label_map.get("en") or key
        rows.append(
            {
                "label": label,
                "value": format_field_value(field, raw_value, locale),
            }
        )
    return rows


def build_questionnaire_sections(
    form_data: dict[str, Any],
    schema: list[dict[str, Any]] | None,
    locale: str,
) -> list[dict[str, Any]]:
    labels = LABELS[locale]
    resolved_schema = schema if schema is not None else []
    sections = [
        {
            "id": "header",
            "title": labels["questionnaire_header"],
            "fields": _build_section_fields(
                header_schema(resolved_schema),
                form_data,
                locale,
            ),
        },
        {
            "id": "specification",
            "title": labels["questionnaire_specification"],
            "fields": _build_section_fields(
                specification_schema(resolved_schema),
                form_data,
                locale,
            ),
        },
    ]
    return [section for section in sections if section["fields"]]


def build_flat_form_fields(
    form_data: dict[str, Any],
    schema: list[dict[str, Any]] | None,
    locale: str,
) -> list[dict[str, str]]:
    fields: list[dict[str, str]] = []
    for field in sorted(
        snapshot_fields(schema),
        key=lambda item: item.get("sort_order", 0),
    ):
        key = field["key"]
        raw_value = form_data.get(key)
        if raw_value is None or raw_value == "":
            continue
        label_map = field.get("label") or {}
        label = label_map.get(locale) or label_map.get("en") or key
        fields.append(
            {
                "label": label,
                "value": format_field_value(field, raw_value, locale),
            }
        )
    return fields


def questionnaire_has_content(sections: list[dict[str, Any]]) -> bool:
    return any(section.get("fields") for section in sections)
