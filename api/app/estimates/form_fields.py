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
    "mvp_scope",
    "business_domain",
    "non_functional_needs",
    "integrations",
    "integration_count",
    "data_complexity",
    "ui_complexity",
    "auth_complexity",
    "data_migration_needed",
    "compliance_level",
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
    "desired_system": (
        "corporate_website",
        "web_application",
        "mobile_app",
        "api_backend",
        "admin_portal",
        "ecommerce",
        "saas",
        "internal_tool",
        "other",
        "undecided",
    ),
    "target_users": (
        "internal_staff",
        "external_customers",
        "both_internal_external",
        "partners",
        "general_public",
        "undecided",
    ),
    "usage_platform": (
        "web_browser",
        "iphone_app",
        "android_app",
        "both_mobile",
        "undecided",
    ),
    "admin_screen_needed": ("yes", "no", "undecided"),
    "payment_needed": (
        "none",
        "bank_transfer",
        "credit_card",
        "both",
        "undecided",
    ),
    "delivery_schedule": (
        "asap",
        "within_1_3_months",
        "within_3_6_months",
        "within_6_12_months",
        "over_12_months",
        "flexible",
    ),
    "nature_of_work": (
        "new_build",
        "enhancement",
        "replacement",
        "migration",
        "integration",
        "general",
    ),
    "business_domain": (
        "retail",
        "finance",
        "healthcare",
        "manufacturing",
        "logistics",
        "education",
        "government",
        "it_saas",
        "other",
        "undecided",
    ),
    "data_complexity": ("low", "medium", "high"),
    "ui_complexity": ("low", "medium", "high"),
    "development_approach": (
        "traditional",
        "ai_assisted",
        "hybrid",
        "low_code",
    ),
    "development_location": ("japan", "offshore", "hybrid"),
    "maintenance_support": (
        "none",
        "best_effort",
        "business_hours",
        "sla_24x7",
        "undecided",
    ),
    "mvp_scope": (
        "mvp",
        "full_release",
        "phased",
        "undecided",
    ),
    "auth_complexity": (
        "none",
        "simple_login",
        "sso",
        "multi_tenant",
        "undecided",
    ),
    "data_migration_needed": (
        "no",
        "yes_limited",
        "yes_major",
        "undecided",
    ),
    "compliance_level": (
        "none",
        "standard",
        "regulated",
        "undecided",
    ),
}

NUMBER_FIELD_KEYS = {"expected_user_count", "concurrent_users", "integration_count"}
CURRENCY_FIELD_KEYS = {"client_budget"}

TEXT_FIELD_KEYS = {
    "system_type",
    "budget",
}
OPTIONAL_FIELD_KEYS = {
    "technology_preferences",
    "budget",
    "client_budget",
    "integration_count",
}

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
    "mvp_scope": {"en": "Delivery scope", "ja": "リリース範囲"},
    "project_overview": {"en": "Project overview", "ja": "プロジェクト概要"},
    "system_type": {"en": "Type of system", "ja": "システム種別"},
    "business_domain": {"en": "Business domain", "ja": "業界・ドメイン"},
    "main_functional_needs": {"en": "Main functional needs", "ja": "主要機能要件"},
    "non_functional_needs": {"en": "Non-functional needs", "ja": "非機能要件"},
    "users_and_load": {"en": "Users and load", "ja": "ユーザー数・負荷"},
    "integrations": {"en": "Connections to other systems", "ja": "他システム連携"},
    "integration_count": {"en": "Number of integrations", "ja": "連携システム数"},
    "data_complexity": {"en": "Data complexity", "ja": "データ複雑度"},
    "ui_complexity": {"en": "User interface complexity", "ja": "UI複雑度"},
    "auth_complexity": {"en": "Authentication complexity", "ja": "認証の複雑度"},
    "data_migration_needed": {"en": "Data migration needed", "ja": "データ移行の要否"},
    "compliance_level": {"en": "Compliance requirements", "ja": "コンプライアンス要件"},
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
    "none": {"en": "Not needed", "ja": "不要"},
    "low": {"en": "Low / Simple", "ja": "低 / シンプル"},
    "medium": {"en": "Medium", "ja": "中"},
    "high": {"en": "High", "ja": "高"},
    "japan": {"en": "Mainly in Japan", "ja": "主に国内"},
    "offshore": {"en": "Mainly offshore", "ja": "主にオフショア"},
    "hybrid": {"en": "Mix of Japan and offshore", "ja": "国内とオフショアの混合"},
    "asap": {"en": "ASAP", "ja": "できるだけ早く"},
    "within_1_3_months": {"en": "Within 1–3 months", "ja": "1〜3か月以内"},
    "within_3_6_months": {"en": "Within 3–6 months", "ja": "3〜6か月以内"},
    "within_6_12_months": {"en": "Within 6–12 months", "ja": "6〜12か月以内"},
    "over_12_months": {"en": "Over 12 months", "ja": "12か月以上"},
    "flexible": {"en": "Flexible", "ja": "未定・相談したい"},
    "corporate_website": {"en": "Corporate website", "ja": "コーポレートサイト"},
    "web_application": {"en": "Web application", "ja": "Webアプリケーション"},
    "mobile_app": {"en": "Mobile app", "ja": "モバイルアプリ"},
    "api_backend": {"en": "API / backend service", "ja": "API / バックエンド"},
    "admin_portal": {"en": "Admin portal", "ja": "管理ポータル"},
    "ecommerce": {"en": "E-commerce", "ja": "ECサイト"},
    "saas": {"en": "SaaS product", "ja": "SaaSプロダクト"},
    "internal_tool": {"en": "Internal tool", "ja": "社内ツール"},
    "other": {"en": "Other", "ja": "その他"},
    "internal_staff": {"en": "Internal staff", "ja": "社内スタッフ"},
    "external_customers": {"en": "External customers", "ja": "外部顧客"},
    "both_internal_external": {
        "en": "Both internal and external users",
        "ja": "社内・外部の両方",
    },
    "partners": {"en": "Partners / vendors", "ja": "パートナー / 取引先"},
    "general_public": {"en": "General public", "ja": "一般公開"},
    "bank_transfer": {"en": "Bank transfer only", "ja": "銀行振込のみ"},
    "credit_card": {"en": "Credit card only", "ja": "クレジットカードのみ"},
    "both": {"en": "Bank transfer and credit card", "ja": "銀行振込とクレジットカード"},
    "new_build": {"en": "New build", "ja": "新規開発"},
    "enhancement": {"en": "Enhancement", "ja": "機能追加・改修"},
    "replacement": {"en": "Replacement", "ja": "リプレース"},
    "migration": {"en": "Migration", "ja": "移行"},
    "integration": {"en": "Integration", "ja": "システム連携"},
    "general": {"en": "General", "ja": "汎用"},
    "retail": {"en": "Retail", "ja": "小売"},
    "finance": {"en": "Finance", "ja": "金融"},
    "healthcare": {"en": "Healthcare", "ja": "医療・ヘルスケア"},
    "manufacturing": {"en": "Manufacturing", "ja": "製造"},
    "logistics": {"en": "Logistics", "ja": "物流"},
    "education": {"en": "Education", "ja": "教育"},
    "government": {"en": "Government", "ja": "公共・行政"},
    "it_saas": {"en": "IT / SaaS", "ja": "IT / SaaS"},
    "traditional": {"en": "Traditional", "ja": "従来型"},
    "ai_assisted": {"en": "AI-assisted", "ja": "AI支援"},
    "low_code": {"en": "Low-code", "ja": "ローコード"},
    "best_effort": {"en": "Best effort", "ja": "ベストエフォート"},
    "business_hours": {"en": "Business hours support", "ja": "営業時間内サポート"},
    "sla_24x7": {"en": "24/7 SLA support", "ja": "24時間365日SLA"},
    "mvp": {"en": "MVP only", "ja": "MVPのみ"},
    "full_release": {"en": "Full release", "ja": "フルリリース"},
    "phased": {"en": "Phased rollout", "ja": "段階的リリース"},
    "simple_login": {"en": "Simple login", "ja": "シンプルなログイン"},
    "sso": {"en": "SSO / enterprise auth", "ja": "SSO / エンタープライズ認証"},
    "multi_tenant": {"en": "Multi-tenant", "ja": "マルチテナント"},
    "yes_limited": {"en": "Yes, limited migration", "ja": "あり（限定的）"},
    "yes_major": {"en": "Yes, major migration", "ja": "あり（大規模）"},
    "standard": {"en": "Standard (e.g. privacy, audit logs)", "ja": "標準（プライバシー、監査ログ等）"},
    "regulated": {"en": "Regulated (e.g. HIPAA, PCI)", "ja": "規制対象（HIPAA、PCI等）"},
}

# Per-field overrides when the same option slug needs a different label (e.g. hybrid).
FIELD_OPTION_LABEL_OVERRIDES: dict[str, dict[str, dict[str, str]]] = {
    "development_approach": {
        "hybrid": {"en": "Hybrid", "ja": "ハイブリッド"},
    },
    "maintenance_support": {
        "none": {"en": "None", "ja": "なし"},
    },
}

# Maps legacy / AI free-text answers to select slugs (keys are casefolded).
SELECT_VALUE_ALIASES: dict[str, dict[str, str]] = {
    "desired_system": {
        "website": "corporate_website",
        "corporate website": "corporate_website",
        "web app": "web_application",
        "web application": "web_application",
        "mobile application": "mobile_app",
        "mobile app": "mobile_app",
        "e-commerce": "ecommerce",
        "e commerce": "ecommerce",
        "api": "api_backend",
        "backend": "api_backend",
        "customer portal": "web_application",
        "portal": "web_application",
    },
    "target_users": {
        "internal": "internal_staff",
        "internal users": "internal_staff",
        "internal staff": "internal_staff",
        "customers": "external_customers",
        "external users": "external_customers",
        "external customers": "external_customers",
        "public": "general_public",
        "general public": "general_public",
    },
    "payment_needed": {
        "yes": "both",
        "no": "none",
        "bank transfer": "bank_transfer",
        "credit card": "credit_card",
    },
    "nature_of_work": {
        "new build": "new_build",
        "new web application": "new_build",
        "new web application development": "new_build",
        "greenfield": "new_build",
        "greenfield web application": "new_build",
        "major enhancement": "enhancement",
        "feature enhancement": "enhancement",
        "system replacement": "replacement",
        "data migration": "migration",
        "system integration": "integration",
    },
    "business_domain": {
        "it": "it_saas",
        "saas": "it_saas",
        "it / saas": "it_saas",
    },
    "development_approach": {
        "ai assisted": "ai_assisted",
        "ai-assisted": "ai_assisted",
        "low code": "low_code",
        "low-code": "low_code",
        "waterfall": "traditional",
        "agile": "hybrid",
    },
    "mvp_scope": {
        "minimum viable product": "mvp",
        "minimum viable": "mvp",
        "full": "full_release",
        "phase": "phased",
        "phased rollout": "phased",
    },
    "auth_complexity": {
        "login": "simple_login",
        "basic auth": "simple_login",
        "single sign on": "sso",
        "single sign-on": "sso",
        "multi tenant": "multi_tenant",
        "multitenant": "multi_tenant",
    },
    "data_migration_needed": {
        "yes": "yes_limited",
        "limited": "yes_limited",
        "major": "yes_major",
    },
    "compliance_level": {
        "hipaa": "regulated",
        "pci": "regulated",
        "gdpr": "standard",
        "soc2": "standard",
        "soc 2": "standard",
    },
    "maintenance_support": {
        "no": "none",
        "not needed": "none",
        "24/7": "sla_24x7",
        "24x7": "sla_24x7",
    },
}

FIELD_PLACEHOLDERS: dict[str, dict[str, str]] = {
    "expected_user_count": {"en": "e.g. 1000", "ja": "例: 1000"},
    "concurrent_users": {"en": "e.g. 100", "ja": "例: 100"},
    "client_budget": {"en": "e.g. 5000000", "ja": "例: 5000000"},
    "problem_to_solve": {
        "en": "e.g. Reduce manual data entry and improve customer response time",
        "ja": "例: 手作業の入力作業を減らし、顧客対応時間を短縮したい",
    },
    "required_features": {
        "en": "One feature per line (e.g. login, search, reporting)",
        "ja": "1行に1機能（例: ログイン、検索、レポート）",
    },
    "scope_boundaries": {
        "en": "In scope: … / Out of scope: …",
        "ja": "対象: … / 対象外: …",
    },
    "non_functional_needs": {
        "en": "e.g. security, performance, availability, scalability",
        "ja": "例: セキュリティ、性能、可用性、拡張性",
    },
    "integrations": {
        "en": "One system per line or comma-separated",
        "ja": "1行1システム、またはカンマ区切り",
    },
    "integration_count": {
        "en": "e.g. 3",
        "ja": "例: 3",
    },
    "technology_preferences": {
        "en": "e.g. React, PostgreSQL, AWS (optional)",
        "ja": "例: React、PostgreSQL、AWS（任意）",
    },
    "rules_and_standards": {
        "en": "e.g. GDPR, internal security policy, accessibility standards",
        "ja": "例: GDPR、社内セキュリティポリシー、アクセシビリティ基準",
    },
    "team_and_resources": {
        "en": "e.g. 2 engineers, part-time designer, client-side PM",
        "ja": "例: エンジニア2名、パートタイムデザイナー、クライアント側PM",
    },
    "risks_unknowns": {
        "en": "e.g. legacy API docs missing, vendor timeline uncertain",
        "ja": "例: 既存API仕様書なし、ベンダー納期未定",
    },
    "delivery_timing": {
        "en": "Key milestones, fixed dates, dependencies",
        "ja": "主要マイルストーン、固定日、依存関係",
    },
}

KNOWN_FIELD_TYPE_PATCHES: dict[str, str] = {
    "desired_system": "select",
    "target_users": "select",
    "payment_needed": "select",
    "expected_user_count": "number",
    "concurrent_users": "number",
    "delivery_schedule": "select",
    "client_budget": "currency",
    "nature_of_work": "select",
    "business_domain": "select",
    "development_approach": "select",
    "maintenance_support": "select",
    "mvp_scope": "select",
    "auth_complexity": "select",
    "data_migration_needed": "select",
    "compliance_level": "select",
    "integration_count": "number",
    "data_complexity": "select",
    "ui_complexity": "select",
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
    "mvp_scope": "Whether the first delivery is MVP-only, full release, or phased",
    "project_overview": "What the project is for, the problem it solves, and what done looks like",
    "system_type": (
        "What you are building (e.g. website, mobile app, enterprise system, APIs)"
    ),
    "business_domain": "Industry or area the system serves (e.g. finance, healthcare, retail)",
    "main_functional_needs": "What the system should do for users and the business",
    "non_functional_needs": "Performance, security, availability, load, and similar constraints",
    "users_and_load": "How many people will use it, busy periods, and expected growth",
    "integrations": "Other systems or data sources this must work with",
    "integration_count": "Approximate count of external systems to integrate (optional)",
    "data_complexity": "How complex the data is: low (simple), medium, or high",
    "ui_complexity": "How rich the screens and workflows are: low (simple), medium, or high",
    "auth_complexity": "Authentication and access control complexity",
    "data_migration_needed": "Whether legacy data must be migrated and at what scale",
    "compliance_level": "Regulatory or organizational compliance requirements",
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
    if key in NUMBER_FIELD_KEYS:
        return "number"
    if key in CURRENCY_FIELD_KEYS:
        return "currency"
    if key in TEXT_FIELD_KEYS:
        return "text"
    return "textarea"


def _option_label(field_key: str, option: str) -> dict[str, str]:
    override = FIELD_OPTION_LABEL_OVERRIDES.get(field_key, {}).get(option)
    if override:
        return override
    return OPTION_LABELS.get(option, {"en": option, "ja": option})


def option_label_for_field(field_key: str, option: str, locale: str = "en") -> str:
    labels = _option_label(field_key, option)
    return labels.get(locale) or labels.get("en") or option


def _build_select_options(key: str) -> list[dict[str, Any]]:
    return [
        {
            "value": option,
            "label": _option_label(key, option),
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
        "placeholder": FIELD_PLACEHOLDERS.get(key, {"en": "", "ja": ""}),
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
        if field_type not in {"text", "textarea", "select", "number", "currency"}:
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


def patch_known_field_types(fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    patched = copy.deepcopy(fields)
    for field in patched:
        key = str(field.get("key", ""))
        target_type = KNOWN_FIELD_TYPE_PATCHES.get(key)
        if target_type:
            field["type"] = target_type
            if target_type == "select" and key in SELECT_OPTIONS:
                field["options"] = _build_select_options(key)
            elif target_type in {"number", "currency"}:
                field["options"] = []
        placeholders = FIELD_PLACEHOLDERS.get(key)
        if placeholders:
            field["placeholder"] = placeholders
    return patched


def snapshot_fields(schema: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not schema:
        return copy.deepcopy(DEFAULT_TEMPLATE_FIELDS)
    return copy.deepcopy(validate_template_fields(patch_known_field_types(schema)))


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
COMPLEXITY_CANONICAL_TO_LEGACY = {
    "low": "simple",
    "medium": "moderate",
    "high": "complex",
}


def _canonical_complexity(value: str) -> str:
    lowered = value.strip().casefold()
    return COMPLEXITY_VALUE_ALIASES.get(lowered, lowered)


def _normalize_numeric_value(text: str) -> str:
    return re.sub(r"[^\d]", "", text)


def _resolve_complexity_select_value(text: str, options: set[str]) -> str:
    if not text:
        return ""
    lowered = text.strip().casefold()
    matched = next((option for option in options if option.casefold() == lowered), None)
    if matched:
        return matched
    canonical = _canonical_complexity(lowered)
    matched = next((option for option in options if option.casefold() == canonical), None)
    if matched:
        return matched
    legacy = COMPLEXITY_CANONICAL_TO_LEGACY.get(canonical)
    if legacy:
        matched = next((option for option in options if option.casefold() == legacy), None)
        if matched:
            return matched
    return ""


def _resolve_select_value(key: str, text: str, options: set[str]) -> str:
    if not text:
        return ""
    if key in COMPLEXITY_FIELD_KEYS:
        return _resolve_complexity_select_value(text, options)
    lowered = text.casefold()
    field_aliases = SELECT_VALUE_ALIASES.get(key, {})
    lowered = field_aliases.get(lowered, lowered)
    matched = next((option for option in options if option.casefold() == lowered), None)
    if matched:
        return matched
    slug = re.sub(r"[\s\-]+", "_", lowered.strip())
    if slug:
        matched = next((option for option in options if option.casefold() == slug), None)
        if matched:
            return matched
    return ""


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
            normalized[key] = _resolve_select_value(key, text, select_map[key])
        elif field["type"] in {"number", "currency"} or key in NUMBER_FIELD_KEYS or key in CURRENCY_FIELD_KEYS:
            normalized[key] = _normalize_numeric_value(text)
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


def fill_complexity_from_profile(
    form_data: dict[str, Any],
    complexity_level: str,
    schema: list[dict[str, Any]] | None,
) -> dict[str, str]:
    """Fill empty complexity questionnaire fields from an extraction profile level."""
    fields = snapshot_fields(schema)
    select_map = {
        field["key"]: {option["value"] for option in field.get("options", [])}
        for field in fields
        if field["type"] == "select"
    }
    merged = normalize_form_data(schema, form_data if isinstance(form_data, dict) else {})
    level = complexity_level.strip().casefold()
    if level not in {"low", "medium", "high"}:
        return merged
    for key in COMPLEXITY_FIELD_KEYS:
        if str(merged.get(key, "")).strip():
            continue
        if key not in select_map:
            continue
        resolved = _resolve_complexity_select_value(level, select_map[key])
        if resolved:
            merged[key] = resolved
    return merged


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
