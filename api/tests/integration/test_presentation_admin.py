from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


def _localized_axis(name: str, config: dict | None = None) -> dict:
    description = f"{name} description"
    return {
        "name": name,
        "description": description,
        "content": {
            "_i18n": {
                "en": {"name": name, "description": description},
                "ja": {"name": f"{name} JA", "description": f"{description} JA"},
            }
        },
        "config": config or {},
        "is_active": True,
    }


@pytest.mark.asyncio
async def test_presentation_drafts_require_admin(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    response = await client.get("/admin/presentation/drafts", headers=auth_headers)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_read_asset_scoped_to_its_presentation_draft(
    client: AsyncClient,
    admin_headers: dict[str, str],
):
    created = await client.post(
        "/admin/presentation/drafts",
        headers=admin_headers,
        json={"source_locale": "en"},
    )
    assert created.status_code == 201, created.text
    draft_id = created.json()["id"]
    asset_id = str(uuid.uuid4())
    expected_path = f"uploads/presentation-drafts/{draft_id}/{asset_id}.png"
    storage = AsyncMock()
    storage.list_prefix.return_value = [expected_path]
    storage.read.return_value = b"\x89PNG\r\nasset"

    unauthenticated = await client.get(
        f"/admin/presentation/drafts/{draft_id}/assets/{asset_id}"
    )
    assert unauthenticated.status_code == 401

    with patch("app.admin.presentation.get_storage_backend", return_value=storage):
        response = await client.get(
            f"/admin/presentation/drafts/{draft_id}/assets/{asset_id}",
            headers=admin_headers,
        )

    assert response.status_code == 200, response.text
    assert response.content == b"\x89PNG\r\nasset"
    assert response.headers["content-type"] == "image/png"
    assert storage.list_prefix.await_count >= 1
    storage.read.assert_awaited_once_with(expected_path)


@pytest.mark.asyncio
async def test_draft_asset_endpoint_rejects_path_outside_requested_draft(
    client: AsyncClient,
    admin_headers: dict[str, str],
):
    created = await client.post(
        "/admin/presentation/drafts",
        headers=admin_headers,
        json={"source_locale": "en"},
    )
    assert created.status_code == 201, created.text
    draft_id = created.json()["id"]
    asset_id = str(uuid.uuid4())
    storage = AsyncMock()
    storage.list_prefix.return_value = [
        f"uploads/presentation-drafts/{uuid.uuid4()}/{asset_id}.png"
    ]

    with patch("app.admin.presentation.get_storage_backend", return_value=storage):
        response = await client.get(
            f"/admin/presentation/drafts/{draft_id}/assets/{asset_id}",
            headers=admin_headers,
        )

    assert response.status_code == 404
    storage.read.assert_not_awaited()


@pytest.mark.asyncio
async def test_blank_draft_cover_consistency_approve_adds_catalog_presets(
    client: AsyncClient,
    admin_headers: dict[str, str],
):
    created = await client.post(
        "/admin/presentation/drafts",
        headers=admin_headers,
        json={"source_locale": "en"},
    )
    assert created.status_code == 201, created.text
    draft_id = created.json()["id"]

    patched = await client.patch(
        f"/admin/presentation/drafts/{draft_id}",
        headers=admin_headers,
        json={
            "theme_draft": _localized_axis(
                "API Ocean Theme",
                {"colors": {"primary": "17365D", "accent": "D97706"}},
            ),
            "style_draft": _localized_axis(
                "API Spacious Style",
                {
                    "margins": {
                        "top_mm": 16,
                        "right_mm": 16,
                        "bottom_mm": 16,
                        "left_mm": 16,
                    }
                },
            ),
            "template_draft": _localized_axis(
                "API Cover Template",
                {
                    "page": {"size": "A4", "orientation": "portrait"},
                    "cover": True,
                    "cover_fields": [],
                    "cover_design": {
                        "padding_mm": 24,
                        "colors": {"title": "1E3A5F"},
                        "assets": [],
                    },
                },
            ),
        },
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["template_draft"]["config"]["cover_design"]["padding_mm"] == 24

    consistency = await client.post(
        f"/admin/presentation/drafts/{draft_id}/consistency",
        headers=admin_headers,
    )
    assert consistency.status_code == 200, consistency.text
    assert "theme.colors.primary" in {
        item["id"] for item in consistency.json()["suggestions"]
    }

    applied = await client.post(
        f"/admin/presentation/drafts/{draft_id}/apply-suggestions",
        headers=admin_headers,
        json={"suggestion_ids": ["theme.colors.primary"]},
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["theme_draft"]["config"]["colors"]["primary"] == "1E3A5F"

    approved = await client.post(
        f"/admin/presentation/drafts/{draft_id}/approve",
        headers=admin_headers,
    )
    assert approved.status_code == 200, approved.text
    ids = approved.json()
    assert set(ids) == {"theme_id", "style_id", "template_id"}

    fetched = await client.get(
        f"/admin/presentation/drafts/{draft_id}",
        headers=admin_headers,
    )
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "approved"

    for kind, id_key in (
        ("themes", "theme_id"),
        ("styles", "style_id"),
        ("templates", "template_id"),
    ):
        catalog = await client.get(f"/presentation/{kind}", headers=admin_headers)
        assert catalog.status_code == 200, catalog.text
        assert ids[id_key] in {preset["id"] for preset in catalog.json()}

    template_detail = await client.get(
        f"/presentation/templates/{ids['template_id']}",
        headers=admin_headers,
    )
    assert template_detail.status_code == 200, template_detail.text
    assert template_detail.json()["config"]["cover_fields"] == []


@pytest.mark.asyncio
async def test_admin_can_upload_and_read_template_cover_asset(
    client: AsyncClient,
    admin_headers: dict[str, str],
):
    created = await client.post(
        "/admin/presentation/templates",
        headers=admin_headers,
        json={
            "id": "cover-asset-test",
            "name": "Cover Asset Test",
            "config": {
                "layout": "executive_cover",
                "cover": True,
                "page": {"size": "A4", "orientation": "portrait"},
                "cover_fields": [],
                "cover_design": {"assets": []},
            },
            "is_active": True,
        },
    )
    assert created.status_code == 201, created.text

    storage = AsyncMock()
    storage.save = AsyncMock()
    storage.list_prefix = AsyncMock(return_value=[])
    storage.read = AsyncMock(return_value=b"\x89PNG\r\ntpl")

    with patch("app.admin.presentation.get_storage_backend", return_value=storage):
        upload = await client.post(
            "/admin/presentation/templates/cover-asset-test/assets",
            headers=admin_headers,
            files={"file": ("logo.png", b"\x89PNG\r\ntpl", "image/png")},
        )
    assert upload.status_code == 201, upload.text
    asset = upload.json()
    assert asset["id"]
    assert asset["storage_path"].startswith("uploads/presentation-assets/cover-asset-test/")
    storage.save.assert_awaited()

    asset_id = asset["id"]
    expected_path = asset["storage_path"]
    storage.list_prefix.return_value = [expected_path]
    storage.read.return_value = b"\x89PNG\r\ntpl"

    with patch("app.admin.presentation.get_storage_backend", return_value=storage):
        response = await client.get(
            f"/admin/presentation/templates/cover-asset-test/assets/{asset_id}",
            headers=admin_headers,
        )
    assert response.status_code == 200, response.text
    assert response.content == b"\x89PNG\r\ntpl"


@pytest.mark.asyncio
async def test_create_cover_template_defaults_include_cover_true(
    client: AsyncClient,
    admin_headers: dict[str, str],
):
    response = await client.post(
        "/admin/presentation/templates",
        headers=admin_headers,
        json={
            "id": "cover-preset-alpha",
            "name": "Cover Preset Alpha",
            "config": {
                "layout": "executive_cover",
                "cover": True,
                "page": {"size": "A4", "orientation": "portrait"},
                "cover_fields": [
                    {
                        "key": "title",
                        "emphasis": "title",
                        "required": False,
                        "auto_fill": "project_name",
                    }
                ],
                "cover_design": {
                    "alignment": "left",
                    "padding_mm": 24,
                    "colors": {
                        "background": "FFFFFF",
                        "title": "1E3A5F",
                        "text": "334155",
                    },
                    "assets": [],
                },
            },
            "is_active": True,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["config"]["cover"] is True
    assert body["preview"]["has_cover"] is True

    listing = await client.get("/admin/presentation/templates", headers=admin_headers)
    assert listing.status_code == 200
    cover_rows = [row for row in listing.json() if row["id"] == "cover-preset-alpha"]
    assert cover_rows
    assert cover_rows[0]["preview"]["has_cover"] is True
