import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.schemas import ExportNarrativeTranslation, TranslatedFeatureItem, TranslatedFormField
from app.exports.narrative_translate import (
    apply_export_narrative_translation,
    build_export_translation_request,
    ensure_export_narrative_locale,
    needs_export_narrative_translation,
)
from app.i18n.localized_content import resolve_localized_dict, store_localized_dict


def _estimate(
    *,
    locale: str = "en",
    form_data=None,
    extracted_data=None,
    feature_items=None,
    form_schema_snapshot=None,
):
    return SimpleNamespace(
        id=uuid.uuid4(),
        locale=locale,
        form_data=form_data or {},
        extracted_data=extracted_data or {},
        feature_items=feature_items or [],
        form_schema_snapshot=form_schema_snapshot
        or [
            {"key": "desired_system", "type": "text", "section": "header", "sort_order": 1},
            {"key": "nature_of_work", "type": "select", "section": "specification", "sort_order": 2},
            {
                "key": "scope_boundaries",
                "type": "textarea",
                "section": "specification",
                "sort_order": 3,
            },
        ],
    )


def test_needs_translation_when_target_locale_missing():
    estimate = _estimate(
        form_data=store_localized_dict(None, "en", {"desired_system": "Portal", "nature_of_work": "enhancement"}),
        extracted_data=store_localized_dict(
            None,
            "en",
            {"functional_requirements": ["Login"], "estimate_type": "Web"},
        ),
        feature_items=[
            SimpleNamespace(
                id=uuid.uuid4(),
                name="Auth",
                description="Login flow",
                phase="development",
                role="developer",
                localizations={
                    "en": {
                        "name": "Auth",
                        "description": "Login flow",
                        "phase": "development",
                        "role": "developer",
                    }
                },
            )
        ],
    )
    assert needs_export_narrative_translation(estimate, "ja") is True
    assert needs_export_narrative_translation(estimate, "en") is False


def test_needs_translation_false_when_target_already_present():
    form = store_localized_dict(None, "en", {"desired_system": "Portal"})
    form = store_localized_dict(form, "ja", {"desired_system": "ポータル"})
    extracted = store_localized_dict(None, "en", {"functional_requirements": ["Login"]})
    extracted = store_localized_dict(extracted, "ja", {"functional_requirements": ["ログイン"]})
    fid = uuid.uuid4()
    estimate = _estimate(
        form_data=form,
        extracted_data=extracted,
        feature_items=[
            SimpleNamespace(
                id=fid,
                name="Auth",
                description="Login",
                phase="development",
                role="developer",
                localizations={
                    "en": {
                        "name": "Auth",
                        "description": "Login",
                        "phase": "development",
                        "role": "developer",
                    },
                    "ja": {
                        "name": "認証",
                        "description": "ログイン",
                        "phase": "development",
                        "role": "developer",
                    },
                },
            )
        ],
    )
    assert needs_export_narrative_translation(estimate, "ja") is False


def test_build_request_only_includes_free_text_form_fields():
    estimate = _estimate(
        form_data=store_localized_dict(
            None,
            "en",
            {
                "desired_system": "Customer portal",
                "nature_of_work": "enhancement",
                "scope_boundaries": "No mobile apps",
            },
        ),
        extracted_data=store_localized_dict(
            None,
            "en",
            {
                "functional_requirements": ["Login"],
                "non_functional_requirements": ["HA"],
                "user_roles": ["Admin"],
                "modules": ["Auth"],
                "external_systems": ["Stripe"],
                "estimate_exclusions": ["Native apps"],
                "estimate_type": "Web Application",
            },
        ),
        feature_items=[
            SimpleNamespace(
                id=uuid.uuid4(),
                name="Auth",
                description="OAuth",
                phase="development",
                role="developer",
                localizations={},
            )
        ],
    )
    request = build_export_translation_request(estimate, "ja")
    assert request is not None
    assert set(request["form_fields"].keys()) == {"desired_system", "scope_boundaries"}
    assert "nature_of_work" not in request["form_fields"]
    assert request["functional_requirements"] == ["Login"]
    assert len(request["features"]) == 1
    assert request["source_locale"] == "en"
    assert request["target_locale"] == "ja"


def test_apply_translation_persists_i18n_without_changing_source():
    fid = uuid.uuid4()
    estimate = _estimate(
        form_data=store_localized_dict(
            None,
            "en",
            {
                "desired_system": "Customer portal",
                "nature_of_work": "enhancement",
                "scope_boundaries": "No mobile",
            },
        ),
        extracted_data=store_localized_dict(
            None,
            "en",
            {
                "functional_requirements": ["Login"],
                "non_functional_requirements": [],
                "user_roles": [],
                "modules": [],
                "external_systems": [],
                "estimate_exclusions": ["Native"],
                "estimate_type": "Web Application",
                "confidence_score": 80,
            },
        ),
        feature_items=[
            SimpleNamespace(
                id=fid,
                name="Auth",
                description="OAuth",
                phase="development",
                role="developer",
                localizations={
                    "en": {
                        "name": "Auth",
                        "description": "OAuth",
                        "phase": "development",
                        "role": "developer",
                    }
                },
            )
        ],
    )
    translation = ExportNarrativeTranslation(
        form_fields=[
            TranslatedFormField(key="desired_system", value="顧客ポータル"),
            TranslatedFormField(key="scope_boundaries", value="モバイルなし"),
        ],
        functional_requirements=["ログイン"],
        non_functional_requirements=[],
        user_roles=[],
        modules=[],
        external_systems=[],
        estimate_exclusions=["ネイティブ"],
        estimate_type="Webアプリ",
        features=[
            TranslatedFeatureItem(id=str(fid), name="認証", description="OAuth認証"),
        ],
    )

    apply_export_narrative_translation(estimate, "ja", translation)

    en_form = resolve_localized_dict(estimate.form_data, "en", "en")
    ja_form = resolve_localized_dict(estimate.form_data, "ja", "en")
    assert en_form["desired_system"] == "Customer portal"
    assert ja_form["desired_system"] == "顧客ポータル"
    assert ja_form["nature_of_work"] == "enhancement"

    ja_extracted = resolve_localized_dict(estimate.extracted_data, "ja", "en")
    assert ja_extracted["functional_requirements"] == ["ログイン"]
    assert ja_extracted["confidence_score"] == 80

    locs = estimate.feature_items[0].localizations
    assert locs["en"]["name"] == "Auth"
    assert locs["ja"]["name"] == "認証"
    assert locs["ja"]["phase"] == "development"


@pytest.mark.asyncio
async def test_ensure_skips_ai_when_not_needed():
    form = store_localized_dict(None, "en", {"desired_system": "Portal"})
    form = store_localized_dict(form, "ja", {"desired_system": "ポータル"})
    extracted = store_localized_dict(None, "en", {"functional_requirements": ["Login"]})
    extracted = store_localized_dict(extracted, "ja", {"functional_requirements": ["ログイン"]})
    estimate = _estimate(form_data=form, extracted_data=extracted, feature_items=[])
    db = MagicMock()
    provider = AsyncMock()
    translated = await ensure_export_narrative_locale(
        db,
        estimate,
        "ja",
        provider=provider,
    )
    assert translated is False
    provider.translate_export_narrative.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_calls_ai_and_applies_result():
    fid = uuid.uuid4()
    estimate = _estimate(
        form_data=store_localized_dict(None, "en", {"desired_system": "Portal", "nature_of_work": "enhancement"}),
        extracted_data=store_localized_dict(
            None,
            "en",
            {"functional_requirements": ["Login"], "estimate_type": "Web"},
        ),
        feature_items=[
            SimpleNamespace(
                id=fid,
                name="Auth",
                description="Login",
                phase="development",
                role="developer",
                localizations={"en": {"name": "Auth", "description": "Login", "phase": "development", "role": "developer"}},
            )
        ],
    )
    provider = AsyncMock()
    provider.translate_export_narrative.return_value = ExportNarrativeTranslation(
        form_fields=[TranslatedFormField(key="desired_system", value="ポータル")],
        functional_requirements=["ログイン"],
        non_functional_requirements=[],
        user_roles=[],
        modules=[],
        external_systems=[],
        estimate_exclusions=[],
        estimate_type="Webアプリ",
        features=[TranslatedFeatureItem(id=str(fid), name="認証", description="ログイン")],
    )
    db = MagicMock()
    translated = await ensure_export_narrative_locale(
        db,
        estimate,
        "ja",
        provider=provider,
    )
    assert translated is True
    provider.translate_export_narrative.assert_awaited_once()
    assert resolve_localized_dict(estimate.form_data, "ja", "en")["desired_system"] == "ポータル"
    assert estimate.feature_items[0].localizations["ja"]["name"] == "認証"
