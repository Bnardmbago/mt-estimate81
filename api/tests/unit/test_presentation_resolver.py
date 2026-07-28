"""Unit tests for presentation resolver and catalog defaults."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.presentation import PresentationStyle, PresentationTemplate, PresentationTheme
from app.presentation.resolver import get_presentation_defaults, resolve_presentation
from app.presentation.seeds import (
    COMFORTABLE_STYLE,
    CORPORATE_NAVY_CONFIG,
    CLASSIC_LINEAR_TEMPLATE,
    MODERN_SLATE_CONFIG,
)
from app.presentation import service as presentation_service


async def _seed_catalog(db: AsyncSession) -> None:
    db.add(
        PresentationTheme(
            id="corporate-navy",
            name="Corporate Navy",
            description="default",
            is_default=True,
            is_active=True,
            config=CORPORATE_NAVY_CONFIG,
        )
    )
    db.add(
        PresentationTheme(
            id="modern-slate",
            name="Modern Slate",
            description="alt",
            is_default=False,
            is_active=True,
            config=MODERN_SLATE_CONFIG,
        )
    )
    db.add(
        PresentationStyle(
            id="comfortable",
            name="Comfortable",
            is_default=True,
            is_active=True,
            config=COMFORTABLE_STYLE,
        )
    )
    db.add(
        PresentationStyle(
            id="compact",
            name="Compact",
            is_default=False,
            is_active=True,
            config={"base_font_size_pt": 9, "line_spacing": 1.2},
        )
    )
    db.add(
        PresentationTemplate(
            id="classic-linear",
            name="Classic Linear",
            is_default=True,
            is_active=True,
            config=CLASSIC_LINEAR_TEMPLATE,
        )
    )
    db.add(
        PresentationTemplate(
            id="executive-cover",
            name="Executive Cover",
            is_default=False,
            is_active=True,
            config={"layout": "executive_cover", "cover": True, "section_chrome": "minimal"},
        )
    )
    await db.commit()


@pytest.mark.asyncio
async def test_resolve_defaults_and_override(db_session: AsyncSession):
    await _seed_catalog(db_session)
    defaults = await get_presentation_defaults(db_session)
    assert defaults["theme_id"] == "corporate-navy"
    assert defaults.get("cover_template_id") in (None, "")
    assert defaults["style_id"] == "comfortable"
    assert defaults["template_id"] == "classic-linear"

    bundle = await resolve_presentation(db_session, None, None, None)
    assert bundle.theme_id == "corporate-navy"
    assert bundle.theme_color_map()["primary"] == CORPORATE_NAVY_CONFIG["colors"]["primary"]
    assert "--proposal-primary" in bundle.css_var_map()

    alt = await resolve_presentation(
        db_session, "modern-slate", "compact", "executive-cover"
    )
    assert alt.theme_id == "modern-slate"
    assert alt.style_id == "compact"
    assert alt.template_id == "executive-cover"
    assert alt.layout["cover"] is True
    assert alt.page == {"size": "A4", "orientation": "portrait"}
    assert alt.page_css_size() == "A4 portrait"
    assert len(alt.cover_design["accent_shapes"]) == 1
    assert alt.cover_design["accent_shapes"][0]["type"] == "rectangle"
    assert alt.cover_fields == []
    assert alt.cover_assets == []
    assert alt.theme_color_map()["primary"] == "0F172A"


@pytest.mark.asyncio
async def test_resolve_presentation_stores_canonical_shapes_and_accent_warnings(
    db_session: AsyncSession,
):
    await _seed_catalog(db_session)
    template = await presentation_service.get_preset(
        db_session, "template", "executive-cover"
    )
    template.config = {
        **template.config,
        "page": {"size": "Letter", "orientation": "landscape"},
        "cover_design": {
            "accent_shapes": [
                {
                    "id": "valid-shape",
                    "type": "ellipse",
                    "geometry": {
                        "x_pct": 75,
                        "y_pct": 80,
                        "width_pct": 50,
                        "height_pct": 50,
                        "rotation_deg": 20,
                        "z_index": 3,
                    },
                    "fill": {"mode": "theme"},
                    "locked": True,
                    "visible": False,
                },
                {"id": "bad", "type": "raw_svg"},
            ]
        },
    }
    await db_session.commit()

    bundle = await resolve_presentation(
        db_session, template_id="executive-cover"
    )

    assert bundle.page == {"size": "Letter", "orientation": "landscape"}
    assert bundle.cover_design["accent_shapes"] == [
        {
            "id": "valid-shape",
            "name": "Accent shape",
            "type": "ellipse",
            "visible": False,
            "locked": True,
            "geometry": {
                "x_pct": 75.0,
                "y_pct": 80.0,
                "width_pct": 25.0,
                "height_pct": 20.0,
                "rotation_deg": 20.0,
                "z_index": 3,
            },
            "fill": {"mode": "theme", "opacity": 1.0},
            "border": {
                "enabled": False,
                "color": "#000000",
                "width_pt": 0.0,
                "style": "solid",
                "radius_pct": 0.0,
            },
            "pattern": {
                "type": "none",
                "color": "#ffffff",
                "scale": 1.0,
                "spacing": 1.0,
                "opacity": 0.25,
            },
        }
    ]
    assert bundle.accent_warnings
    assert any("shape" in warning.lower() for warning in bundle.accent_warnings)


@pytest.mark.asyncio
async def test_resolve_unknown_and_inactive_soft_fallback(db_session: AsyncSession):
    await _seed_catalog(db_session)
    theme = await presentation_service.get_preset(db_session, "theme", "modern-slate")
    theme.is_active = False
    await db_session.commit()

    bundle = await resolve_presentation(db_session, "modern-slate", "nope", "missing")
    assert bundle.theme_id == "corporate-navy"
    assert bundle.style_id == "comfortable"
    assert bundle.template_id == "classic-linear"
    assert any("Inactive" in w or "Unknown" in w for w in bundle.warnings)


@pytest.mark.asyncio
async def test_set_default_and_block_deactivate_default(db_session: AsyncSession):
    await _seed_catalog(db_session)
    await presentation_service.set_default(db_session, "theme", "modern-slate")
    defaults = await get_presentation_defaults(db_session)
    assert defaults["theme_id"] == "modern-slate"

    with pytest.raises(HTTPException) as exc:
        await presentation_service.update_preset(
            db_session, "theme", "modern-slate", is_active=False
        )
    assert exc.value.status_code == 400
