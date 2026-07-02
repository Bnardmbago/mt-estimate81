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
        "body": PRICING_LABELS["ja"]["campaign_terms_body"],
    },
    "en": {
        "title": "Special Notes",
        "body": PRICING_LABELS["en"]["campaign_terms_body"],
    },
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
) -> dict[str, str]:
    labels = PRICING_LABELS[locale]
    nrc_discounted = int(pricing_summary["nrc_discounted_total_jpy"])
    special_price = f"{format_currency(nrc_discounted)} {labels['excluding_tax']}"
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
