"""Recommend Theme / Style / Template IDs for a proposal."""

from __future__ import annotations

import logging
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.presentation import service as presentation_service
from app.presentation.resolver import get_presentation_defaults
from app.proposals.ai_client import _complete
from app.proposals.prompts import (
    build_presentation_recommend_system_prompt,
    build_presentation_recommend_user_prompt,
)
from app.proposals.schemas_ai import PresentationRecommendAI

logger = logging.getLogger(__name__)

Locale = Literal["ja", "en"]


async def _active_catalog(db: AsyncSession) -> dict[str, list[dict[str, str]]]:
    themes = await presentation_service.list_presets(db, "theme", active_only=True)
    styles = await presentation_service.list_presets(db, "style", active_only=True)
    templates = await presentation_service.list_presets(db, "template", active_only=True)
    return {
        "themes": [
            {"id": t.id, "name": t.name, "description": t.description or ""} for t in themes
        ],
        "styles": [
            {"id": s.id, "name": s.name, "description": s.description or ""} for s in styles
        ],
        "templates": [
            {"id": t.id, "name": t.name, "description": t.description or ""} for t in templates
        ],
    }


def _valid_ids(catalog: dict[str, list[dict[str, str]]]) -> dict[str, set[str]]:
    return {
        "themes": {row["id"] for row in catalog.get("themes") or []},
        "styles": {row["id"] for row in catalog.get("styles") or []},
        "templates": {row["id"] for row in catalog.get("templates") or []},
    }


async def recommend_presentation(
    db: AsyncSession,
    snapshot: dict[str, Any],
    locale: Locale,
    *,
    include_poc: bool,
    theme_id: str | None = None,
    style_id: str | None = None,
    template_id: str | None = None,
) -> tuple[str, str, str, dict[str, Any]]:
    """
    Resolve presentation IDs.

    Returns (theme_id, style_id, template_id, presentation_meta).
    User-provided IDs win; empty axes are filled by AI or admin defaults.
    """
    defaults = await get_presentation_defaults(db)
    catalog = await _active_catalog(db)
    valid = _valid_ids(catalog)

    user_theme = theme_id or None
    user_style = style_id or None
    user_template = template_id or None

    if user_theme and user_style and user_template:
        return (
            user_theme,
            user_style,
            user_template,
            {
                "source": "user",
                "recommended": {
                    "theme_id": user_theme,
                    "style_id": user_style,
                    "template_id": user_template,
                },
                "warnings": [],
            },
        )

    recommended: dict[str, Any] = dict(defaults)
    source = "default"
    warnings: list[str] = []
    try:
        model = await _complete(
            db,
            system=build_presentation_recommend_system_prompt(locale),
            user=build_presentation_recommend_user_prompt(
                snapshot, catalog, locale, include_poc=include_poc
            ),
            schema_model=PresentationRecommendAI,
            schema_name="presentation_recommend",
            tool_description="Recommend Theme, Style, and Template preset ids.",
        )
        recommended = {
            "theme_id": model.theme_id,
            "style_id": model.style_id,
            "template_id": model.template_id,
            "rationale": model.rationale or "",
        }
        source = "ai"
        if recommended["theme_id"] not in valid["themes"]:
            warnings.append(f"AI theme_id '{recommended['theme_id']}' invalid")
            recommended["theme_id"] = defaults["theme_id"]
        if recommended["style_id"] not in valid["styles"]:
            warnings.append(f"AI style_id '{recommended['style_id']}' invalid")
            recommended["style_id"] = defaults["style_id"]
        if recommended["template_id"] not in valid["templates"]:
            warnings.append(f"AI template_id '{recommended['template_id']}' invalid")
            recommended["template_id"] = defaults["template_id"]
    except Exception:
        logger.exception("Presentation AI recommend call failed")
        warnings.append("ai_recommend_failed")
        recommended = dict(defaults)
        source = "default"

    final_theme = user_theme or str(recommended["theme_id"])
    final_style = user_style or str(recommended["style_id"])
    final_template = user_template or str(recommended["template_id"])

    if user_theme or user_style or user_template:
        if user_theme and user_style and user_template:
            source = "user"
        else:
            source = "mixed"

    return (
        final_theme,
        final_style,
        final_template,
        {
            "source": source,
            "recommended": recommended,
            "warnings": warnings,
        },
    )
