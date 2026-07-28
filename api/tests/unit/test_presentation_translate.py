from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import ExportNarrativeTranslation, TranslatedFormField
from app.i18n.localized_content import has_localized_locale, resolve_localized_dict
from app.models.presentation import PresentationStyle, PresentationTemplate, PresentationTheme
from app.presentation.translate import PresentationTranslationError, ensure_preset_bilingual
from app.presentation.drafts import approve_draft, create_blank_draft, update_draft_axis


class _TranslationProvider:
    def __init__(self, values: dict[str, str]):
        self.values = values
        self.requests: list[dict] = []

    async def translate_export_narrative(
        self,
        *,
        source_locale: str,
        target_locale: str,
        payload: dict,
    ) -> ExportNarrativeTranslation:
        self.requests.append(
            {
                "source_locale": source_locale,
                "target_locale": target_locale,
                "payload": payload,
            }
        )
        return ExportNarrativeTranslation(
            form_fields=[
                TranslatedFormField(key=key, value=value)
                for key, value in self.values.items()
            ]
        )


def _axis(name: str, *, config: dict | None = None) -> dict:
    return {
        "name": name,
        "description": f"{name} description",
        "config": config or {},
        "is_active": True,
    }


@pytest.mark.asyncio
async def test_ensure_preset_bilingual_translates_metadata_and_cover_content(
    db_session: AsyncSession,
    monkeypatch,
):
    provider = _TranslationProvider(
        {
            "name": "海洋テンプレート",
            "description": "海洋テンプレートの説明",
            "cover_fields.title.label": "件名",
            "cover_fields.title.default_text": "既定の件名",
        }
    )

    async def get_provider(_db):
        return provider

    monkeypatch.setattr("app.presentation.translate.get_ai_provider", get_provider)
    payload = _axis(
        "Ocean Template",
        config={
            "cover_fields": [
                {
                    "key": "title",
                    "content": {
                        "_i18n": {
                            "en": {
                                "label": "Title",
                                "default_text": "Default title",
                            }
                        }
                    },
                }
            ]
        },
    )

    result = await ensure_preset_bilingual(db_session, payload, content_locale="en")

    assert has_localized_locale(result["content"], "en")
    assert has_localized_locale(result["content"], "ja")
    assert resolve_localized_dict(result["content"], "ja", "en") == {
        "name": "海洋テンプレート",
        "description": "海洋テンプレートの説明",
    }
    field_content = result["config"]["cover_fields"][0]["content"]
    assert resolve_localized_dict(field_content, "ja", "en") == {
        "label": "件名",
        "default_text": "既定の件名",
    }
    assert provider.requests[0]["payload"]["form_fields"] == {
        "name": "Ocean Template",
        "description": "Ocean Template description",
        "cover_fields.title.label": "Title",
        "cover_fields.title.default_text": "Default title",
    }


@pytest.mark.asyncio
async def test_ensure_preset_bilingual_requires_source_name_before_translate(
    db_session: AsyncSession,
    monkeypatch,
):
    called = False

    async def get_provider(_db):
        nonlocal called
        called = True
        raise AssertionError("translation should not run without a source name")

    monkeypatch.setattr("app.presentation.translate.get_ai_provider", get_provider)

    with pytest.raises(
        PresentationTranslationError,
        match="preset name is required for locale 'en'",
    ):
        await ensure_preset_bilingual(
            db_session,
            {"name": "", "description": "", "config": {}},
            content_locale="en",
        )

    assert called is False


@pytest.mark.asyncio
async def test_approve_keeps_draft_and_creates_no_presets_when_translation_fails(
    db_session: AsyncSession,
    monkeypatch,
):
    async def failing_provider(_db):
        raise RuntimeError("translation service unavailable")

    monkeypatch.setattr("app.presentation.translate.get_ai_provider", failing_provider)
    draft = await create_blank_draft(db_session, source_locale="en")
    await update_draft_axis(
        db_session,
        draft.id,
        theme_draft=_axis("Theme"),
        style_draft=_axis("Style"),
        template_draft=_axis(
            "Template",
            config={
                "cover_fields": [
                    {
                        "key": "title",
                        "content": {
                            "_i18n": {
                                "en": {
                                    "label": "Title",
                                    "default_text": "Default title",
                                }
                            }
                        },
                    }
                ]
            },
        ),
    )

    with pytest.raises(HTTPException, match="Bilingual translation failed") as exc:
        await approve_draft(db_session, draft.id, source_locale="en")

    assert exc.value.status_code == 422
    await db_session.refresh(draft)
    assert draft.status == "draft"
    assert draft.errors
    assert "translation service unavailable" in draft.errors[0]
    for model in (PresentationTheme, PresentationStyle, PresentationTemplate):
        rows = await db_session.execute(select(model))
        assert rows.scalars().all() == []
