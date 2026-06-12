from app.i18n.localized_content import (
    normalize_locale,
    resolve_feature_item_fields,
    resolve_localized_dict,
    store_feature_item_localization,
    store_localized_dict,
)


def test_resolve_legacy_flat_form_data():
    data = {"main_functional_needs": "Login"}
    assert resolve_localized_dict(data, "ja", "en") == data
    assert resolve_localized_dict(data, "en", "ja") == data


def test_store_and_resolve_localized_dict():
    stored = store_localized_dict(None, "ja", {"main_functional_needs": "ログイン"})
    stored = store_localized_dict(stored, "en", {"main_functional_needs": "Login"})
    assert resolve_localized_dict(stored, "ja", "en")["main_functional_needs"] == "ログイン"
    assert resolve_localized_dict(stored, "en", "ja")["main_functional_needs"] == "Login"


def test_resolve_feature_item_localizations():
    fields = resolve_feature_item_fields(
        name="Auth",
        description="Login flow",
        phase="development",
        role="developer",
        localizations={
            "ja": {
                "name": "認証",
                "description": "ログインフロー",
                "phase": "development",
                "role": "developer",
            }
        },
        display_locale="ja",
        fallback_locale="en",
    )
    assert fields["name"] == "認証"
    assert fields["description"] == "ログインフロー"

    english = resolve_feature_item_fields(
        name="Auth",
        description="Login flow",
        phase="development",
        role="developer",
        localizations={
            "ja": {
                "name": "認証",
                "description": "ログインフロー",
                "phase": "development",
                "role": "developer",
            }
        },
        display_locale="en",
        fallback_locale="ja",
    )
    assert english["name"] == "Auth"
