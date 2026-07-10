from __future__ import annotations

from typing import Literal

InstructionLocale = Literal["en", "ja"]

DEFAULT_SYSTEM_PROMPT: dict[InstructionLocale, str] = {
    "en": (
        "When Client Constraints are provided in the user message, estimate the full documented "
        "scope at natural hours. Treat the client's budget and delivery schedule as context for "
        "estimation_warnings and estimate_exclusions — not as hard pre-shrink targets during "
        "extraction. Document scope that may not fit within stated limits in "
        "estimation_warnings and estimate_exclusions."
    ),
    "ja": (
        "ユーザーメッセージにクライアント制約がある場合、文書に記載されたスコープを自然な工数で"
        "見積もってください。クライアントの予算と納期は、抽出時に工数を事前に縮小するための"
        "厳しい上限ではなく、estimation_warnings と estimate_exclusions の文脈として扱ってください。"
        "制約内に収まらない可能性のあるスコープは estimation_warnings と estimate_exclusions "
        "に記載してください。"
    ),
}

DEFAULT_USER_PROMPT_TEMPLATE: dict[InstructionLocale, str] = {
    "en": (
        "The client provided the following budget and delivery expectations. "
        "Use them as context when writing estimation_warnings and estimate_exclusions. "
        "Estimate the full documented scope at natural hours.\n\n"
        "{budget_section}"
        "{schedule_section}"
        "- Binding cap: {max_hours} hours ({binding_constraint_label} is tighter)\n"
        "Document any scope that cannot fit within these limits in estimation_warnings "
        "and estimate_exclusions."
    ),
    "ja": (
        "クライアントが以下の予算と納期を指定しています。"
        "estimation_warnings と estimate_exclusions を記載する際の文脈として使用してください。"
        "文書に記載されたスコープを自然な工数で見積もってください。\n\n"
        "{budget_section}"
        "{schedule_section}"
        "- 拘束する上限: {max_hours} 時間（{binding_constraint_label}が厳しい）\n"
        "これらの制限内に収まらないスコープは estimation_warnings と estimate_exclusions "
        "に記載してください。"
    ),
}

DEFAULT_NEGATIVE_PROMPT: dict[InstructionLocale, str] = {
    "en": (
        "Do not silently shrink scope or feature hours below what the documents require solely "
        "to fit budget or delivery caps."
    ),
    "ja": (
        "予算や納期の上限に合わせるために、文書が要求するスコープや機能工数を"
        "黙って縮小しないでください。"
    ),
}


def get_default_constraint_system_prompt(locale: InstructionLocale) -> str:
    return DEFAULT_SYSTEM_PROMPT[locale]


def get_default_constraint_user_prompt_template(locale: InstructionLocale) -> str:
    return DEFAULT_USER_PROMPT_TEMPLATE[locale]


def get_default_constraint_negative_prompt(locale: InstructionLocale) -> str:
    return DEFAULT_NEGATIVE_PROMPT[locale]
