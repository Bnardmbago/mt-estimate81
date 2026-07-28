"""Build stakeholder-facing export context for proposals."""

from __future__ import annotations

from typing import Any

from app.exports.gantt_svg import build_gantt_svg
from app.exports.theme import EXPORT_THEME
from app.i18n.localized_content import resolve_localized_dict
from app.models.proposal import Proposal
from app.presentation.accent_shapes import (
    PAGE_DIMENSIONS_MM,
    render_accent_svg,
)
from app.presentation.background_style import cover_background_inline_css
from app.presentation.cover import cover_surface_colors, resolve_cover_fields
from app.presentation.resolver import PresentationBundle


def _page_dimensions_mm(page: dict[str, Any]) -> tuple[float, float]:
    width, height = PAGE_DIMENSIONS_MM.get(
        str(page.get("size")),
        PAGE_DIMENSIONS_MM["A4"],
    )
    return (height, width) if page.get("orientation") == "landscape" else (width, height)


def _lexicon_labels(locale: str) -> dict[str, str]:
    if locale == "ja":
        return {
            "title": "プロジェクト提案書",
            "toc": "目次",
            "assessment": "プロジェクト評価",
            "proposal": "プロジェクト提案",
            "poc": "概念実証（Proof of Concept）",
            "one_time": "一次性のプロジェクト費用",
            "monthly": "月次の継続費用",
            "first_year": "初年度合計",
            "timeline": "プロジェクトタイムライン",
            "milestones": "マイルストーン",
            "official_poc_cost": "概念実証の公式費用（見積エンジン）",
            "suggested_window": "推奨する検証期間（目安）",
            "effort_hours": "想定工数（時間）",
            "effort_days": "想定工数（人日）",
            "working_days": "想定期間（稼働日）",
            "project_brief": "プロジェクト概要",
            "brief_project_name": "プロジェクト名",
            "brief_description": "プロジェクト説明",
            "brief_business_problem": "ビジネス課題",
            "brief_target_users": "想定利用者",
            "brief_technology_stack": "技術スタック",
            "brief_constraints": "制約条件",
            "poc_diagrams": "図",
            "poc_tables": "表",
            "poc_milestones": "概念実証マイルストーン",
        }
    return {
        "title": "Project Proposal Pack",
        "toc": "Table of Contents",
        "assessment": "Project Assessment",
        "proposal": "Project Proposal",
        "poc": "Proof of Concept",
        "one_time": "One-time project cost",
        "monthly": "Monthly recurring cost",
        "first_year": "First-year total",
        "timeline": "Project timeline",
        "milestones": "Milestones",
        "official_poc_cost": "Official Proof of Concept cost (from estimate engine)",
        "suggested_window": "Suggested validation window",
        "effort_hours": "Estimated effort (hours)",
        "effort_days": "Estimated effort (days)",
        "working_days": "Estimated timeline (working days)",
        "project_brief": "Project brief",
        "brief_project_name": "Project name",
        "brief_description": "Project description",
        "brief_business_problem": "Business problem",
        "brief_target_users": "Target users",
        "brief_technology_stack": "Technology stack",
        "brief_constraints": "Constraints",
        "poc_diagrams": "Illustrations",
        "poc_tables": "Tables",
        "poc_milestones": "Proof of Concept milestones",
    }


def _toc_entries(proposal: Proposal, locale: str, variant: str) -> list[dict[str, str]]:
    labels = _lexicon_labels(locale)
    entries: list[dict[str, str]] = []
    include_assessment = variant in {"full", "assessment"}
    include_proposal = variant in {"full", "proposal"}
    include_poc = variant in {"full", "poc"} and proposal.include_poc and proposal.poc

    def add_part(part_key: str, part_label: str, blob: dict[str, Any] | None) -> None:
        entries.append({"id": part_key, "title": part_label, "level": "1"})
        for section in (blob or {}).get("sections") or []:
            entries.append(
                {
                    "id": f"{part_key}-{section.get('id')}",
                    "title": str(section.get("title") or section.get("id")),
                    "level": "2",
                }
            )

    if include_assessment:
        add_part("assessment", labels["assessment"], proposal.assessment)
    if include_proposal:
        add_part("proposal", labels["proposal"], proposal.proposal_body)
    if include_poc:
        entries.append({"id": "poc", "title": labels["poc"], "level": "1"})
        if (proposal.poc or {}).get("project_brief"):
            entries.append(
                {
                    "id": "poc-project_brief",
                    "title": labels["project_brief"],
                    "level": "2",
                }
            )
        for section in (proposal.poc or {}).get("sections") or []:
            entries.append(
                {
                    "id": f"poc-{section.get('id')}",
                    "title": str(section.get("title") or section.get("id")),
                    "level": "2",
                }
            )
    return entries


def build_proposal_export_context(
    proposal: Proposal,
    *,
    locale: str | None = None,
    variant: str = "full",
    project_name: str | None = None,
    presentation: PresentationBundle | None = None,
    include_cover: bool | None = None,
    cover_values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    loc = locale or proposal.locale
    labels = _lexicon_labels(loc)
    snapshot = proposal.source_snapshot or {}
    costs = snapshot.get("costs") or {}
    gantt = snapshot.get("gantt") or {}

    # Stakeholder cost block — never use NRC/RC abbreviations
    cost_summary = {
        "one_time_project_cost_jpy": costs.get("one_time_project_cost_jpy"),
        "monthly_recurring_cost_jpy": costs.get("monthly_recurring_cost_jpy"),
        "annual_recurring_cost_jpy": costs.get("annual_recurring_cost_jpy"),
        "first_year_total_jpy": costs.get("first_year_total_jpy"),
        "total_effort_hours": costs.get("total_effort_hours"),
        "total_effort_days": costs.get("total_effort_days"),
    }

    display_name = (project_name or "").strip() or (snapshot.get("project_name") or "")

    poc = proposal.poc if variant in {"full", "poc"} and proposal.include_poc else None
    if poc and display_name:
        poc = dict(poc)
        brief = dict(poc.get("project_brief") or {})
        if brief:
            brief["project_name"] = display_name
            poc["project_brief"] = brief

    theme_map = dict(EXPORT_THEME)
    style_tokens: dict[str, Any] = {}
    layout: dict[str, Any] = {"layout": "linear", "cover": False, "section_chrome": "ruled", "columns": 1}
    if presentation is not None:
        theme_map = presentation.theme_color_map()
        style_tokens = presentation.style_tokens
        layout = presentation.layout
    gantt_svg = ""
    try:
        gantt_svg = (
            build_gantt_svg(
                gantt,
                accent_color=f"#{str(theme_map.get('chart', theme_map['accent'])).lstrip('#')}",
            )
            if gantt
            else ""
        )
    except Exception:
        gantt_svg = ""

    template_cover = bool(layout.get("cover"))
    resolved_include_cover = template_cover if include_cover is None else include_cover
    fallback_locale = proposal.locale if proposal.locale != loc else ("ja" if loc == "en" else "en")
    document_facts = resolve_localized_dict(snapshot, loc, fallback_locale)
    document_facts.update(
        {
            "title": display_name,
            "project_name": display_name,
            "client_name": snapshot.get("client_name") or "",
            "document_type": labels["title"],
        }
    )
    resolved_cover_fields: list[dict[str, Any]] = []
    cover_warnings: list[str] = []
    cover_assets: list[dict[str, Any]] = []
    cover_design: dict[str, Any] = {}
    page = {"size": "A4", "orientation": "portrait", "css_size": "A4 portrait"}
    if presentation is not None:
        page = {
            **presentation.page,
            "css_size": presentation.page_css_size(),
        }
        cover_design = presentation.cover_design
        if resolved_include_cover:
            resolved_cover_fields, cover_warnings = resolve_cover_fields(
                presentation.cover_fields,
                cover_values if cover_values is not None else proposal.cover_values,
                display_locale=loc,
                fallback_locale=fallback_locale,
                document_facts=document_facts,
            )
            for raw_asset in presentation.cover_assets:
                if not isinstance(raw_asset, dict):
                    continue
                asset = dict(raw_asset)
                asset["region"] = asset.get("region") or asset.get("role") or "decorative"
                asset["url"] = (
                    asset.get("url")
                    or asset.get("data_uri")
                    or asset.get("storage_path")
                    or ""
                )
                if asset["region"] == "background":
                    asset["background_css"] = cover_background_inline_css(asset)
                cover_assets.append(asset)
            if presentation.logo_storage_path and not any(
                asset.get("region") == "logo" for asset in cover_assets
            ):
                cover_assets.append(
                    {
                        "region": "logo",
                        "url": presentation.logo_storage_path,
                        "storage_path": presentation.logo_storage_path,
                        "alt": presentation.theme_name,
                    }
                )

    cover_colors = cover_surface_colors(cover_design)
    cover_background_color = cover_colors["background"]
    cover_accent_svg = ""
    if presentation is not None:
        page_width_mm, page_height_mm = _page_dimensions_mm(page)
        cover_accent_svg = render_accent_svg(
            cover_design.get("accent_shapes") or [],
            theme_accent=f"#{str(theme_map['accent']).lstrip('#')}",
            width_mm=page_width_mm,
            height_mm=page_height_mm,
        )
        cover_warnings.extend(presentation.accent_warnings)

    return {
        "labels": labels,
        "locale": loc,
        "variant": variant,
        "project_name": display_name,
        "client_name": snapshot.get("client_name") or "",
        "toc": _toc_entries(proposal, loc, variant),
        "assessment": proposal.assessment if variant in {"full", "assessment"} else None,
        "proposal_body": proposal.proposal_body if variant in {"full", "proposal"} else None,
        "poc": poc,
        "diagrams": proposal.diagrams or [],
        "milestones": proposal.milestones or [],
        "cost_summary": cost_summary,
        "gantt": gantt,
        "gantt_svg": gantt_svg,
        "include_poc": proposal.include_poc,
        "theme": theme_map,
        "style": style_tokens,
        "layout": layout,
        "include_cover": resolved_include_cover,
        "page": page,
        "cover": {
            "fields": resolved_cover_fields,
            "assets": cover_assets,
            "design": cover_design,
            "accent_svg": cover_accent_svg,
            "background_color": cover_background_color,
            "title_color": cover_colors["title"],
            "text_color": cover_colors["text"],
            "warnings": cover_warnings,
        },
        "presentation": {
            "theme_id": presentation.theme_id if presentation else None,
            "style_id": presentation.style_id if presentation else None,
            "template_id": presentation.template_id if presentation else None,
            "layout_class": presentation.layout_class() if presentation else "proposal-layout-linear",
        },
    }
