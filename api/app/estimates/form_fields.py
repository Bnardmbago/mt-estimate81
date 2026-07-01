import copy
import re
from typing import Any, Literal

Locale = Literal["en", "ja"]

FIELD_SECTIONS = ("header", "specification")

HEADER_FIELD_KEYS = [
    "desired_system",
    "problem_to_solve",
    "target_users",
    "usage_platform",
    "admin_screen_needed",
    "required_features",
    "payment_needed",
    "expected_user_count",
    "concurrent_users",
    "delivery_schedule",
    "client_budget",
]

SPEC_FIELD_KEYS = [
    "nature_of_work",
    "scope_boundaries",
    "business_domain",
    "non_functional_needs",
    "integrations",
    "data_complexity",
    "ui_complexity",
    "technology_preferences",
    "development_approach",
    "rules_and_standards",
    "team_and_resources",
    "development_location",
    "maintenance_support",
    "risks_unknowns",
]

# Legacy keys kept for backward compatibility with old snapshots and tests.
FORM_FIELD_KEYS = [
    "nature_of_work",
    "scope_boundaries",
    "project_overview",
    "system_type",
    "business_domain",
    "main_functional_needs",
    "non_functional_needs",
    "users_and_load",
    "integrations",
    "data_complexity",
    "ui_complexity",
    "technology_preferences",
    "development_approach",
    "rules_and_standards",
    "team_and_resources",
    "development_location",
    "delivery_timing",
    "maintenance_support",
    "risks_unknowns",
    "budget",
]

SELECT_OPTIONS: dict[str, tuple[str, ...]] = {
    "usage_platform": (
        "web_browser",
        "iphone_app",
        "android_app",
        "both_mobile",
        "undecided",
    ),
    "admin_screen_needed": ("yes", "no", "undecided"),
    "data_complexity": ("low", "medium", "high"),
    "ui_complexity": ("low", "medium", "high"),
    "development_location": ("japan", "offshore", "hybrid"),
}

TEXT_FIELD_KEYS = {
    "expected_user_count",
    "concurrent_users",
    "client_budget",
    "business_domain",
    "development_approach",
    "system_type",
    "budget",
}
OPTIONAL_FIELD_KEYS = {"technology_preferences", "budget", "client_budget"}

RESERVED_FIELD_KEYS = {"project_name", "id", "status", "locale"}

FIELD_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,49}$")

HEADER_FIELD_LABELS: dict[str, dict[str, str]] = {
    "desired_system": {
        "en": "What kind of system do you want to build?",
        "ja": "どのようなシステムを作りたいですか？",
    },
    "problem_to_solve": {
        "en": "What problem should this system solve?",
        "ja": "このシステムで解決したい課題は何ですか？",
    },
    "target_users": {
        "en": "Who will use this system?",
        "ja": "利用者は誰ですか？",
    },
    "usage_platform": {
        "en": "Where will it be used?",
        "ja": "どこで利用しますか？",
    },
    "admin_screen_needed": {
        "en": "Is an admin screen required?",
        "ja": "管理画面は必要ですか？",
    },
    "required_features": {
        "en": "What features are required?",
        "ja": "必要な機能は何ですか？",
    },
    "payment_needed": {
        "en": "Are bank transfer or credit card payments required?",
        "ja": "銀行振込やクレジットカード決済は必要ですか？",
    },
    "expected_user_count": {
        "en": "How many users do you expect?",
        "ja": "想定する利用者数は何名くらいですか？",
    },
    "concurrent_users": {
        "en": "How many concurrent users do you expect?",
        "ja": "想定する同時利用者数は何名くらいですか？",
    },
    "delivery_schedule": {
        "en": "What is your desired delivery schedule?",
        "ja": "希望の納期・スケジュールはいつですか？",
    },
    "client_budget": {
        "en": "What is your budget?",
        "ja": "予算を教えてください。",
    },
}

FORM_FIELD_LABELS: dict[str, dict[str, str]] = {
    **HEADER_FIELD_LABELS,
    "nature_of_work": {"en": "Nature of work", "ja": "作業の性質"},
    "scope_boundaries": {"en": "Scope boundaries", "ja": "スコープ境界"},
    "project_overview": {"en": "Project overview", "ja": "プロジェクト概要"},
    "system_type": {"en": "Type of system", "ja": "システム種別"},
    "business_domain": {"en": "Business domain", "ja": "業界・ドメイン"},
    "main_functional_needs": {"en": "Main functional needs", "ja": "主要機能要件"},
    "non_functional_needs": {"en": "Non-functional needs", "ja": "非機能要件"},
    "users_and_load": {"en": "Users and load", "ja": "ユーザー数・負荷"},
    "integrations": {"en": "Connections to other systems", "ja": "他システム連携"},
    "data_complexity": {"en": "Data complexity", "ja": "データ複雑度"},
    "ui_complexity": {"en": "User interface complexity", "ja": "UI複雑度"},
    "technology_preferences": {"en": "Technology preferences", "ja": "技術的偏好"},
    "development_approach": {"en": "Development approach", "ja": "開発アプローチ"},
    "rules_and_standards": {"en": "Rules and standards to follow", "ja": "遵守ルール・標準"},
    "team_and_resources": {"en": "Team and resources", "ja": "チーム・リソース"},
    "development_location": {"en": "Where development happens", "ja": "開発拠点"},
    "delivery_timing": {"en": "Delivery timing", "ja": "納期・スケジュール"},
    "maintenance_support": {"en": "Maintenance and support", "ja": "保守・サポート"},
    "risks_unknowns": {"en": "Risks and unknowns", "ja": "リスク・不明点"},
    "budget": {"en": "Budget", "ja": "予算"},
}

OPTION_LABELS: dict[str, dict[str, str]] = {
    "web_browser": {"en": "Web browser", "ja": "Webブラウザ"},
    "iphone_app": {"en": "iPhone app", "ja": "iPhoneアプリ"},
    "android_app": {"en": "Android app", "ja": "Androidアプリ"},
    "both_mobile": {"en": "iPhone and Android", "ja": "iPhone・Android両方"},
    "undecided": {"en": "Undecided", "ja": "未定"},
    "yes": {"en": "Yes", "ja": "はい"},
    "no": {"en": "No", "ja": "いいえ"},
    "low": {"en": "Low / Simple", "ja": "低 / シンプル"},
    "medium": {"en": "Medium", "ja": "中"},
    "high": {"en": "High", "ja": "高"},
    "japan": {"en": "Mainly in Japan", "ja": "主に国内"},
    "offshore": {"en": "Mainly offshore", "ja": "主にオフショア"},
    "hybrid": {"en": "Mix of Japan and offshore", "ja": "国内とオフショアの混合"},
}

HEADER_FIELD_DESCRIPTIONS: dict[str, str] = {
    "desired_system": "Client-facing: what system they want to build",
    "problem_to_solve": "Client-facing: business problem to solve",
    "target_users": "Client-facing: who will use the system",
    "usage_platform": "Client-facing: delivery platform (web, mobile, etc.)",
    "admin_screen_needed": "Client-facing: whether an admin UI is needed",
    "required_features": "Client-facing: required features in plain language",
    "payment_needed": "Client-facing: payment methods needed",
    "expected_user_count": "Client-facing: total expected users",
    "concurrent_users": "Client-facing: expected concurrent users",
    "delivery_schedule": "Client-facing: desired timeline",
    "client_budget": "Client-facing: budget range",
}

FORM_FIELD_DESCRIPTIONS: dict[str, str] = {
    **HEADER_FIELD_DESCRIPTIONS,
    "nature_of_work": (
        "Whether this is a new build, major enhancement, replacement, migration, or a mix"
    ),
    "scope_boundaries": "What is clearly in scope and what is out of scope or deferred",
    "project_overview": "What the project is for, the problem it solves, and what done looks like",
    "system_type": (
        "What you are building (e.g. website, mobile app, enterprise system, APIs)"
    ),
    "business_domain": "Industry or area the system serves (e.g. finance, healthcare, retail)",
    "main_functional_needs": "What the system should do for users and the business",
    "non_functional_needs": "Performance, security, availability, load, and similar constraints",
    "users_and_load": "How many people will use it, busy periods, and expected growth",
    "integrations": "Other systems or data sources this must work with",
    "data_complexity": "How complex the data is: low (simple), medium, or high",
    "ui_complexity": "How rich the screens and workflows are: low (simple), medium, or high",
    "technology_preferences": "Languages, platforms, or tools to use (optional)",
    "development_approach": "How work is run (e.g. agile, waterfall, mixed)",
    "rules_and_standards": "Laws, standards, or organizational rules the system must meet",
    "team_and_resources": "Team size, skills needed, or limits on who does the work",
    "development_location": "Where development happens: japan, offshore, or hybrid",
    "delivery_timing": "When delivery is needed, key dates, or fixed windows",
    "maintenance_support": "Expectations after go-live (support, operations, warranty)",
    "risks_unknowns": "Dependencies, open questions, or assumptions that may change the estimate",
    "budget": "Rough budget or range in yen (optional)",
}


def _normalize_section(value: Any) -> str:
    section = str(value or "specification").strip()
    if section not in FIELD_SECTIONS:
        return "specification"
    return section


def _field_type_for_key(key: str) -> str:
    if key in SELECT_OPTIONS:
        return "select"
    if key in TEXT_FIELD_KEYS:
        return "text"
    return "textarea"


def _build_select_options(key: str) -> list[dict[str, Any]]:
    return [
        {
            "value": option,
            "label": OPTION_LABELS.get(option, {"en": option, "ja": option}),
        }
        for option in SELECT_OPTIONS[key]
    ]


def _build_field(
    key: str,
    *,
    section: str,
    sort_order: int,
    required: bool = False,
) -> dict[str, Any]:
    labels = FORM_FIELD_LABELS.get(key) or HEADER_FIELD_LABELS.get(key) or {
        "en": key,
        "ja": key,
    }
    description = FORM_FIELD_DESCRIPTIONS.get(key, "")
    field: dict[str, Any] = {
        "key": key,
        "type": _field_type_for_key(key),
        "required": required,
        "sort_order": sort_order,
        "section": section,
        "label": labels,
        "description": {"en": description, "ja": description},
        "placeholder": {"en": "", "ja": ""},
    }
    if key in SELECT_OPTIONS:
        field["options"] = _build_select_options(key)
    return field


def build_default_template_fields() -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    for index, key in enumerate(HEADER_FIELD_KEYS):
        fields.append(
            _build_field(key, section="header", sort_order=index * 10, required=False)
        )
    for index, key in enumerate(SPEC_FIELD_KEYS):
        fields.append(
            _build_field(
                key,
                section="specification",
                sort_order=200 + index * 10,
                required=False,
            )
        )
    return fields


DEFAULT_TEMPLATE_FIELDS = build_default_template_fields()


def validate_field_key(key: str) -> None:
    if not FIELD_KEY_PATTERN.match(key):
        raise ValueError("Field key must be a lowercase slug (letters, numbers, underscores)")
    if key in RESERVED_FIELD_KEYS:
        raise ValueError(f"Field key '{key}' is reserved")


def validate_template_fields(fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not fields:
        raise ValueError("At least one field is required")

    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []

    for raw in fields:
        key = str(raw.get("key", "")).strip()
        validate_field_key(key)
        if key in seen:
            raise ValueError(f"Duplicate field key: {key}")
        seen.add(key)

        field_type = str(raw.get("type", "")).strip()
        if field_type not in {"text", "textarea", "select"}:
            raise ValueError(f"Invalid field type for '{key}'")

        label = raw.get("label") or {}
        if not isinstance(label, dict) or not str(label.get("en", "")).strip():
            raise ValueError(f"English label is required for '{key}'")

        entry: dict[str, Any] = {
            "key": key,
            "type": field_type,
            "required": bool(raw.get("required", True)),
            "sort_order": int(raw.get("sort_order", 0)),
            "section": _normalize_section(raw.get("section")),
            "label": {
                "en": str(label.get("en", "")).strip(),
                "ja": str(label.get("ja", label.get("en", ""))).strip(),
            },
            "description": _localized_text(raw.get("description")),
            "placeholder": _localized_text(raw.get("placeholder")),
        }

        if field_type == "select":
            options = raw.get("options") or []
            if not isinstance(options, list) or not options:
                raise ValueError(f"Select field '{key}' requires options")
            parsed_options: list[dict[str, Any]] = []
            option_values: set[str] = set()
            for option in options:
                value = str(option.get("value", "")).strip()
                if not value or value in option_values:
                    raise ValueError(f"Invalid select option for '{key}'")
                option_values.add(value)
                option_label = option.get("label") or {}
                parsed_options.append(
                    {
                        "value": value,
                        "label": {
                            "en": str(option_label.get("en", value)).strip(),
                            "ja": str(option_label.get("ja", option_label.get("en", value))).strip(),
                        },
                    }
                )
            entry["options"] = parsed_options
        else:
            entry["options"] = []

        normalized.append(entry)

    normalized.sort(key=lambda item: item["sort_order"])
    return normalized


def _localized_text(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {"en": "", "ja": ""}
    return {
        "en": str(value.get("en", "")).strip(),
        "ja": str(value.get("ja", value.get("en", ""))).strip(),
    }


def snapshot_fields(schema: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not schema:
        return copy.deepcopy(DEFAULT_TEMPLATE_FIELDS)
    return copy.deepcopy(validate_template_fields(schema))


def header_schema(schema: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [field for field in snapshot_fields(schema) if field.get("section") == "header"]


def specification_schema(schema: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        field
        for field in snapshot_fields(schema)
        if field.get("section") != "header"
    ]


def schema_field_keys(schema: list[dict[str, Any]]) -> list[str]:
    return [field["key"] for field in snapshot_fields(schema)]


def specification_field_keys(schema: list[dict[str, Any]]) -> list[str]:
    return [field["key"] for field in specification_schema(schema)]


def field_metadata_for_prompt(schema: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for field in specification_schema(schema):
        entry: dict[str, Any] = {
            "key": field["key"],
            "description": field.get("description", {}).get("en", ""),
            "type": field["type"],
        }
        if field["type"] == "select":
            entry["options"] = [option["value"] for option in field.get("options", [])]
        rows.append(entry)
    return rows


COMPLEXITY_FIELD_KEYS = frozenset({"data_complexity", "ui_complexity"})
COMPLEXITY_VALUE_ALIASES = {
    "simple": "low",
    "basic": "low",
    "moderate": "medium",
    "normal": "medium",
    "complex": "high",
    "advanced": "high",
}


def normalize_form_data(schema: list[dict[str, Any]], raw: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    fields = snapshot_fields(schema)
    select_map = {
        field["key"]: {option["value"] for option in field.get("options", [])}
        for field in fields
        if field["type"] == "select"
    }

    for field in fields:
        key = field["key"]
        value = raw.get(key, "")
        if value is None:
            value = ""
        text = str(value).strip()
        if key in select_map:
            lowered = text.casefold()
            if key in COMPLEXITY_FIELD_KEYS:
                lowered = COMPLEXITY_VALUE_ALIASES.get(lowered, lowered)
            matched = next(
                (option for option in select_map[key] if option.casefold() == lowered),
                None,
            )
            normalized[key] = matched or ""
        else:
            normalized[key] = text
    return normalized


def normalize_suggested_form_data(
    raw: dict[str, Any],
    schema: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    resolved_schema = schema or DEFAULT_TEMPLATE_FIELDS
    normalized = normalize_form_data(resolved_schema, raw)
    spec_keys = set(specification_field_keys(resolved_schema))
    return {key: value for key, value in normalized.items() if key in spec_keys}


def prune_form_data_to_schema(
    schema: list[dict[str, Any]],
    form_data: dict[str, Any] | None,
) -> dict[str, str]:
    raw = form_data if isinstance(form_data, dict) else {}
    return normalize_form_data(schema, raw)


def empty_form_data_for_schema(schema: list[dict[str, Any]]) -> dict[str, str]:
    return {key: "" for key in schema_field_keys(schema)}


# Backward-compatible helpers
def form_field_metadata_for_prompt() -> list[dict[str, Any]]:
    return field_metadata_for_prompt(DEFAULT_TEMPLATE_FIELDS)


FORM_FIELD_METADATA_PROMPT = form_field_metadata_for_prompt()


def empty_form_data() -> dict[str, str]:
    return empty_form_data_for_schema(DEFAULT_TEMPLATE_FIELDS)
