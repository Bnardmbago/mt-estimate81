import re
from typing import Any

from app.exports.markdown import format_currency

PRICING_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "development_cost": "Development Cost",
        "limited_time_discount": "Limited-Time Discount",
        "discount_off": "{percent}% OFF (-{amount})",
        "special_price": "Special Price",
        "excluding_tax": "(excluding tax)",
        "campaign_terms_title": "Campaign Terms",
        "campaign_terms_body": (
            "If you place your order within one month from the date this quotation is issued "
            "({issue_date}), the special discounted price of {special_price} (excluding tax) will apply.\n"
            "After one month, the standard development price will apply."
        ),
    },
    "ja": {
        "development_cost": "開発費用",
        "limited_time_discount": "期間限定割引",
        "discount_off": "{percent}% OFF（-{amount}）",
        "special_price": "特別価格",
        "excluding_tax": "（税抜）",
        "campaign_terms_title": "キャンペーン条件",
        "campaign_terms_body": (
            "本見積書の発行日（{issue_date}）から1か月以内にご発注いただいた場合、"
            "特別割引価格 {special_price}（税抜）が適用されます。\n"
            "1か月を過ぎた場合は、通常の開発費用が適用されます。"
        ),
    },
}

DEFAULT_QUOTATION_SPECIAL_NOTES: dict[str, dict[str, str]] = {
    "ja": {
        "title": "特記事項",
        "body": (
            "本見積書発行日より1か月以内にご発注いただいた場合、"
            "{discount_percent}％OFFの特別価格 {special_price}を適用いたします。"
        ),
    },
    "en": {
        "title": "Special Notes",
        "body": (
            "If you place your order within one month from the date this quotation is issued, "
            "the special discounted price of {special_price} will apply ({discount_percent}% OFF)."
        ),
    },
}

DEFAULT_DEV_LINE_DESCRIPTION: dict[str, str] = {
    "ja": (
        "要件定義・設計、システム開発、外部サービス連携、\n"
        "インフラ構築、テスト・品質確認"
    ),
    "en": (
        "Requirements definition and design, system development, external service integration, "
        "infrastructure setup, testing and quality assurance"
    ),
}

_PLACEHOLDER_PATTERN = re.compile(r"\{([a-z_]+)\}")


def render_special_notes(template: str, variables: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return variables.get(key, match.group(0))

    return _PLACEHOLDER_PATTERN.sub(replace, template)


def build_campaign_terms(locale: str, special_price_jpy: int, issue_date: str) -> str:
    labels = PRICING_LABELS[locale]
    special_price = f"{format_currency(special_price_jpy)} {labels['excluding_tax']}"
    return labels["campaign_terms_body"].format(
        issue_date=issue_date,
        special_price=special_price,
    )


def build_special_notes_variables(
    pricing_summary: dict[str, Any],
    locale: str,
    issue_date: str,
    *,
    include_tax_label: bool = True,
) -> dict[str, str]:
    labels = PRICING_LABELS[locale]
    nrc_discounted = int(pricing_summary["nrc_discounted_total_jpy"])
    if include_tax_label:
        special_price = f"{format_currency(nrc_discounted)} {labels['excluding_tax']}"
    else:
        special_price = format_currency(nrc_discounted)
    original = int(pricing_summary.get("nrc_original_total_jpy") or nrc_discounted)
    amount = int(pricing_summary.get("discount_amount_jpy") or max(original - nrc_discounted, 0))
    percent = int(pricing_summary.get("discount_percent_display") or 0)

    return {
        "issue_date": issue_date,
        "special_price": special_price,
        "original_price": format_currency(original),
        "discount_percent": str(percent),
        "discount_amount": format_currency(amount),
    }


def apply_quotation_special_notes(
    pricing_summary: dict[str, Any],
    locale: str,
    issue_date: str,
    notes_config: Any,
) -> dict[str, Any]:
    if not pricing_summary.get("has_discount"):
        return pricing_summary

    title = notes_config.title_ja if locale == "ja" else notes_config.title_en
    body_template = notes_config.body_ja if locale == "ja" else notes_config.body_en
    variables = build_special_notes_variables(pricing_summary, locale, issue_date)
    body = render_special_notes(body_template, variables)

    updated = dict(pricing_summary)
    updated["campaign_terms_title"] = title
    updated["campaign_terms"] = body
    return updated


_BULLET_PREFIX_PATTERN = re.compile(r"^[\s・•\*\-–—]+")


def _strip_bullet_prefix(text: str) -> str:
    cleaned = text.strip()
    while cleaned:
        updated = _BULLET_PREFIX_PATTERN.sub("", cleaned).strip()
        if updated == cleaned:
            break
        cleaned = updated
    return cleaned


def _split_remark_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        cleaned = _strip_bullet_prefix(raw_line)
        if cleaned:
            lines.append(cleaned)
    return lines


def build_formal_campaign_bullet(
    pricing_summary: dict[str, Any],
    locale: str,
    issue_date: str,
    notes_config: Any | None,
) -> str | None:
    if not pricing_summary.get("has_discount"):
        return None

    if notes_config is not None:
        body_template = notes_config.body_ja if locale == "ja" else notes_config.body_en
    else:
        body_template = DEFAULT_QUOTATION_SPECIAL_NOTES[locale]["body"]

    variables = build_special_notes_variables(
        pricing_summary,
        locale,
        issue_date,
        include_tax_label=False,
    )
    return render_special_notes(body_template, variables)


def build_formal_remarks_items(
    pricing_summary: dict[str, Any],
    locale: str,
    issue_date: str,
    *,
    notes_config: Any | None = None,
    static_remarks: str | None = None,
) -> list[str]:
    """Return cleaned 【備考】 bullets from Admin Quotation Body text only."""
    bullets: list[str] = []
    campaign_bullet = build_formal_campaign_bullet(
        pricing_summary,
        locale,
        issue_date,
        notes_config,
    )
    if campaign_bullet:
        bullets.extend(_split_remark_lines(campaign_bullet))

    # Optional override for tests / callers; never fall back to hardcoded static bullets.
    if static_remarks and static_remarks.strip():
        bullets.extend(_split_remark_lines(static_remarks))

    unique: list[str] = []
    seen: set[str] = set()
    for bullet in bullets:
        cleaned = _strip_bullet_prefix(bullet)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        unique.append(cleaned)
    return unique


def build_formal_remarks(
    pricing_summary: dict[str, Any],
    locale: str,
    issue_date: str,
    *,
    notes_config: Any | None = None,
    static_remarks: str | None = None,
) -> str:
    bullets = build_formal_remarks_items(
        pricing_summary,
        locale,
        issue_date,
        notes_config=notes_config,
        static_remarks=static_remarks,
    )
    # Prefer Japanese middle-dot lists; never use ASCII '*'.
    prefix = "・" if locale == "ja" else "・"
    return "\n".join(f"{prefix}{bullet}" for bullet in bullets)


def build_pricing_summary(
    calculation: dict[str, Any],
    locale: str,
    *,
    issue_date: str,
) -> dict[str, Any]:
    if locale not in PRICING_LABELS:
        raise ValueError(f"Unsupported locale: {locale}")

    labels = PRICING_LABELS[locale]
    nrc = calculation.get("nrc") or {}
    nrc_discounted_total_jpy = int(round(float(nrc.get("total_jpy") or 0)))
    discount_rate = calculation.get("discount_rate_applied")
    nrc_original_total_jpy = calculation.get("nrc_original_total_jpy")
    discount_amount_jpy = calculation.get("discount_amount_jpy")

    has_discount = (
        discount_rate is not None
        and float(discount_rate) > 0
        and nrc_original_total_jpy is not None
        and int(nrc_original_total_jpy) > nrc_discounted_total_jpy
    )

    if not has_discount:
        return {
            "has_discount": False,
            "nrc_discounted_total_jpy": nrc_discounted_total_jpy,
            "labels": labels,
        }

    original = int(nrc_original_total_jpy)
    rate = float(discount_rate)
    amount = (
        int(discount_amount_jpy)
        if discount_amount_jpy is not None
        else original - nrc_discounted_total_jpy
    )
    percent = int(round(rate * 100))
    discount_display = labels["discount_off"].format(
        percent=percent,
        amount=format_currency(amount),
    )
    campaign_terms = build_campaign_terms(locale, nrc_discounted_total_jpy, issue_date)

    return {
        "has_discount": True,
        "nrc_original_total_jpy": original,
        "nrc_discounted_total_jpy": nrc_discounted_total_jpy,
        "discount_rate_applied": rate,
        "discount_amount_jpy": amount,
        "discount_percent_display": percent,
        "discount_display": discount_display,
        "campaign_terms": campaign_terms,
        "campaign_terms_title": labels["campaign_terms_title"],
        "labels": labels,
    }
