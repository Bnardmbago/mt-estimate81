from typing import Literal

Locale = Literal["en", "ja"]

NATURE_OF_WORK_CATEGORIES = (
    "new_build",
    "enhancement",
    "replacement",
    "migration",
    "integration",
    "general",
)

TEMPLATE_LANGUAGES = ("en", "ja", "both")

NATURE_OF_WORK_LABELS: dict[str, dict[str, str]] = {
    "new_build": {"en": "New build", "ja": "新規開発"},
    "enhancement": {"en": "Enhancement", "ja": "機能追加・改修"},
    "replacement": {"en": "Replacement", "ja": "リプレース"},
    "migration": {"en": "Migration", "ja": "移行"},
    "integration": {"en": "Integration", "ja": "システム連携"},
    "general": {"en": "General", "ja": "汎用"},
}

TEMPLATE_LANGUAGE_LABELS: dict[str, dict[str, str]] = {
    "en": {"en": "English", "ja": "英語"},
    "ja": {"en": "Japanese", "ja": "日本語"},
    "both": {"en": "Bilingual", "ja": "バイリンガル"},
}

DEFAULT_NATURE_OF_WORK_CATEGORY = "general"
DEFAULT_TEMPLATE_LANGUAGE = "both"


def validate_nature_of_work_category(value: str) -> str:
    slug = value.strip()
    if slug not in NATURE_OF_WORK_CATEGORIES:
        raise ValueError(f"Invalid nature of work category: {value}")
    return slug


def validate_template_language(value: str) -> str:
    slug = value.strip()
    if slug not in TEMPLATE_LANGUAGES:
        raise ValueError(f"Invalid template language: {value}")
    return slug


def normalize_locale(locale: str | None) -> Locale | None:
    if locale in ("en", "ja"):
        return locale
    return None


def languages_for_locale(locale: str | None) -> tuple[str, ...]:
    normalized = normalize_locale(locale)
    if normalized == "en":
        return ("en", "both")
    if normalized == "ja":
        return ("ja", "both")
    return TEMPLATE_LANGUAGES


def category_sort_key(category: str) -> int:
    try:
        return NATURE_OF_WORK_CATEGORIES.index(category)
    except ValueError:
        return len(NATURE_OF_WORK_CATEGORIES)
