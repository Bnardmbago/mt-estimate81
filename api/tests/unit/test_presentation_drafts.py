from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.presentation import PresentationStyle, PresentationTemplate, PresentationTheme
from app.models.presentation_draft import PresentationPresetDraft
from app.presentation.cleanup import cleanup_stale_presentation_drafts
from app.presentation.drafts import (
    approve_draft,
    create_blank_draft,
    discard_draft,
    update_draft_axis,
)
from app.storage.local import LocalStorageBackend


def _axis(name: str, config: dict | None = None) -> dict:
    return {
        "name": name,
        "description": f"{name} description",
        "content": {
            "_i18n": {
                "en": {"name": name, "description": f"{name} description"},
                "ja": {"name": name, "description": f"{name} description"},
            }
        },
        "config": config or {},
        "is_active": True,
    }


@pytest.mark.asyncio
async def test_blank_draft_seeds_named_axis_payloads(db_session: AsyncSession):
    draft = await create_blank_draft(db_session, source_locale="en")

    assert draft.theme_draft["name"] == "New Theme"
    assert draft.style_draft["name"] == "New Style"
    assert draft.template_draft["name"] == "New Template"
    assert draft.template_draft["config"]["page"] == {
        "size": "A4",
        "orientation": "portrait",
    }


@pytest.mark.asyncio
async def test_blank_patch_approve_creates_three_presets_and_promotes_assets(
    db_session: AsyncSession,
    tmp_path,
    monkeypatch,
):
    storage = LocalStorageBackend(str(tmp_path))
    monkeypatch.setattr(
        "app.presentation.drafts.get_storage_backend",
        lambda: storage,
    )

    draft = await create_blank_draft(db_session, source_locale="en")
    candidate = f"uploads/presentation-drafts/{draft.id}/hero.png"
    await storage.save(candidate, b"hero")
    await update_draft_axis(
        db_session,
        draft.id,
        theme_draft=_axis("Ocean Theme", {"colors": {"primary": "123456"}}),
        style_draft=_axis("Dense Style", {"line_spacing": 1.1}),
        template_draft=_axis(
            "Hero Template",
            {
                "page": {"size": "unknown", "orientation": "landscape"},
                "cover_design": {
                    "background": {
                        "role": "background",
                        "storage_path": candidate,
                        "opacity": 1.4,
                        "rotation": 25,
                    }
                },
            },
        ),
    )

    ids = await approve_draft(db_session, draft.id, source_locale="en")

    assert set(ids) == {"theme_id", "style_id", "template_id"}
    assert ids["theme_id"].startswith("ocean-theme")
    assert ids["style_id"].startswith("dense-style")
    assert ids["template_id"].startswith("hero-template")
    theme = await db_session.get(PresentationTheme, ids["theme_id"])
    style = await db_session.get(PresentationStyle, ids["style_id"])
    template = await db_session.get(PresentationTemplate, ids["template_id"])
    assert theme is not None
    assert style is not None
    assert template is not None
    assert template.config["page"] == {"size": "A4", "orientation": "landscape"}
    background = template.config["cover_design"]["background"]
    approved_path = f"uploads/presentation-assets/{ids['template_id']}/hero.png"
    assert background["storage_path"] == approved_path
    assert background["opacity"] == 1.0
    assert "rotation" not in background
    assert await storage.read(approved_path) == b"hero"
    assert await storage.list_prefix(f"uploads/presentation-drafts/{draft.id}") == []
    await db_session.refresh(draft)
    assert draft.status == "approved"


@pytest.mark.asyncio
async def test_approve_updates_target_presets(db_session: AsyncSession):
    theme = PresentationTheme(id="theme-target", name="Old", config={}, is_active=True)
    style = PresentationStyle(id="style-target", name="Old", config={}, is_active=True)
    template = PresentationTemplate(id="template-target", name="Old", config={}, is_active=True)
    db_session.add_all([theme, style, template])
    await db_session.commit()
    draft = await create_blank_draft(
        db_session,
        source_locale="ja",
        target_theme_id=theme.id,
        target_style_id=style.id,
        target_template_id=template.id,
    )
    await update_draft_axis(
        db_session,
        draft.id,
        theme_draft=_axis("Updated Theme"),
        style_draft=_axis("Updated Style"),
        template_draft=_axis("Updated Template"),
    )

    ids = await approve_draft(db_session, draft.id, source_locale="ja")

    assert ids == {
        "theme_id": "theme-target",
        "style_id": "style-target",
        "template_id": "template-target",
    }
    await db_session.refresh(theme)
    await db_session.refresh(style)
    await db_session.refresh(template)
    assert (theme.name, style.name, template.name) == (
        "Updated Theme",
        "Updated Style",
        "Updated Template",
    )


@pytest.mark.asyncio
async def test_discard_deletes_draft_candidates(
    db_session: AsyncSession,
    tmp_path,
    monkeypatch,
):
    storage = LocalStorageBackend(str(tmp_path))
    monkeypatch.setattr(
        "app.presentation.drafts.get_storage_backend",
        lambda: storage,
    )
    draft = await create_blank_draft(db_session, source_locale="en")
    prefix = f"uploads/presentation-drafts/{draft.id}"
    await storage.save(f"{prefix}/unused.webp", b"unused")

    await discard_draft(db_session, draft.id)

    assert await db_session.get(PresentationPresetDraft, draft.id) is None
    assert await storage.list_prefix(prefix) == []


@pytest.mark.asyncio
async def test_cleanup_removes_expired_drafts_and_storage(
    db_session: AsyncSession,
    tmp_path,
    monkeypatch,
):
    storage = LocalStorageBackend(str(tmp_path))
    monkeypatch.setattr(
        "app.presentation.cleanup.get_storage_backend",
        lambda: storage,
    )
    expired = PresentationPresetDraft(
        source_locale="en",
        expires_at=datetime.utcnow() - timedelta(seconds=1),
    )
    current = PresentationPresetDraft(
        source_locale="en",
        expires_at=datetime.utcnow() + timedelta(days=1),
    )
    db_session.add_all([expired, current])
    await db_session.commit()
    await storage.save(f"presentation-drafts/{expired.id}/old.png", b"old")
    await storage.save(f"presentation-drafts/{current.id}/keep.png", b"keep")

    removed = await cleanup_stale_presentation_drafts(db_session)

    assert removed == 1
    assert await db_session.get(PresentationPresetDraft, expired.id) is None
    assert await db_session.get(PresentationPresetDraft, current.id) is not None
    assert await storage.list_prefix(f"presentation-drafts/{expired.id}") == []
    assert await storage.list_prefix(f"presentation-drafts/{current.id}") == [
        f"presentation-drafts/{current.id}/keep.png"
    ]


@pytest.mark.asyncio
async def test_local_storage_prefix_helpers_are_scoped_and_sorted(tmp_path):
    storage = LocalStorageBackend(str(tmp_path))
    await storage.save("presentation-drafts/one/b.png", b"b")
    await storage.save("presentation-drafts/one/nested/a.png", b"a")
    await storage.save("presentation-drafts/other/keep.png", b"k")

    assert await storage.list_prefix("presentation-drafts/one") == [
        "presentation-drafts/one/b.png",
        "presentation-drafts/one/nested/a.png",
    ]

    await storage.delete_prefix("presentation-drafts/one")

    assert await storage.list_prefix("presentation-drafts/one") == []
    assert await storage.exists("presentation-drafts/other/keep.png")


@pytest.mark.asyncio
async def test_approve_rolls_back_promoted_assets_when_commit_fails(
    db_session: AsyncSession,
    tmp_path,
    monkeypatch,
):
    storage = LocalStorageBackend(str(tmp_path))
    monkeypatch.setattr(
        "app.presentation.drafts.get_storage_backend",
        lambda: storage,
    )
    draft = await create_blank_draft(db_session, source_locale="en")
    candidate = f"presentation-drafts/{draft.id}/hero.png"
    await storage.save(candidate, b"hero")
    await update_draft_axis(
        db_session,
        draft.id,
        theme_draft=_axis("Theme"),
        style_draft=_axis("Style"),
        template_draft=_axis(
            "Template",
            {"cover_design": {"assets": [{"storage_path": candidate}]}},
        ),
    )
    real_commit = db_session.commit

    async def failing_commit():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(db_session, "commit", failing_commit)
    with pytest.raises(RuntimeError, match="database unavailable"):
        await approve_draft(db_session, draft.id, source_locale="en")
    monkeypatch.setattr(db_session, "commit", real_commit)

    approved = await storage.list_prefix("presentation-assets")
    assert approved == []
    assert await storage.exists(candidate)
    rows = await db_session.execute(select(PresentationTemplate))
    assert rows.scalars().all() == []
