from app.rate_cards.fingerprint import rate_card_settings_fingerprint
from app.rate_cards.defaults import DEFAULT_RATE_CARD_SETTINGS


def test_rate_card_settings_fingerprint_is_stable():
    first = rate_card_settings_fingerprint(DEFAULT_RATE_CARD_SETTINGS)
    second = rate_card_settings_fingerprint(dict(DEFAULT_RATE_CARD_SETTINGS))
    assert first == second


def test_rate_card_settings_fingerprint_changes_when_settings_change():
    baseline = rate_card_settings_fingerprint(DEFAULT_RATE_CARD_SETTINGS)
    changed = dict(DEFAULT_RATE_CARD_SETTINGS)
    changed["contingency_rate"] = 0.99
    assert rate_card_settings_fingerprint(changed) != baseline
