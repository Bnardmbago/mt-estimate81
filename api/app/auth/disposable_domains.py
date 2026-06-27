"""Common disposable / temporary email domains blocked for contact sign-up."""

DISPOSABLE_EMAIL_DOMAINS = frozenset(
    {
        "mailinator.com",
        "guerrillamail.com",
        "guerrillamail.net",
        "guerrillamail.org",
        "sharklasers.com",
        "grr.la",
        "guerrillamailblock.com",
        "pokemail.net",
        "spam4.me",
        "tempmail.com",
        "temp-mail.org",
        "throwaway.email",
        "yopmail.com",
        "trashmail.com",
        "10minutemail.com",
        "getnada.com",
        "dispostable.com",
        "maildrop.cc",
        "fakeinbox.com",
    }
)


def is_disposable_email(email: str) -> bool:
    normalized = email.strip().lower()
    if "@" not in normalized:
        return False
    domain = normalized.rsplit("@", maxsplit=1)[1]
    return domain in DISPOSABLE_EMAIL_DOMAINS
