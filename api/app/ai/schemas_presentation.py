"""Structured AI output for presentation reference generation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PresentationThemeAI(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    primary: str = Field(pattern=r"^#?[0-9A-Fa-f]{6}$")
    accent: str = Field(pattern=r"^#?[0-9A-Fa-f]{6}$")
    surface: str = Field(pattern=r"^#?[0-9A-Fa-f]{6}$")
    text_body: str = Field(pattern=r"^#?[0-9A-Fa-f]{6}$")


class PresentationStyleAI(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    density: Literal["compact", "comfortable", "spacious"] = "comfortable"
    margin_mm: float = Field(default=18, ge=6, le=40)
    line_spacing: float = Field(default=1.4, ge=1, le=2)
    base_font_size_pt: float = Field(default=10, ge=7, le=16)


class PresentationCoverFieldAI(BaseModel):
    key: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    label: str = Field(min_length=1, max_length=120)
    required: bool = False
    default: str = Field(default="", max_length=500)
    auto_fill: str = Field(default="", max_length=64)


class PresentationTemplateAI(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    page_size: Literal["A4", "A3", "Letter", "Legal"] = "A4"
    orientation: Literal["portrait", "landscape"] = "portrait"
    layout: Literal["linear", "executive_cover", "two_column"] = "linear"
    cover: bool = True
    cover_alignment: Literal["left", "center", "right"] = "left"
    cover_padding_mm: float = Field(default=24, ge=0, le=80)
    title_pt: float = Field(default=30, ge=12, le=72)
    metadata_pt: float = Field(default=10, ge=6, le=24)
    cover_fields: list[PresentationCoverFieldAI] = Field(default_factory=list, max_length=12)


class PresentationDraftAI(BaseModel):
    """One structured Theme + Style + Template recommendation."""

    theme: PresentationThemeAI
    style: PresentationStyleAI
    template: PresentationTemplateAI

    def to_draft_payloads(self) -> tuple[dict, dict, dict]:
        def color(value: str) -> str:
            return value.removeprefix("#").upper()

        theme = {
            "name": self.theme.name,
            "description": self.theme.description,
            "is_active": False,
            "config": {
                "colors": {
                    "primary": color(self.theme.primary),
                    "accent": color(self.theme.accent),
                    "surface": color(self.theme.surface),
                    "text_body": color(self.theme.text_body),
                }
            },
        }
        margin = self.style.margin_mm
        style = {
            "name": self.style.name,
            "description": self.style.description,
            "is_active": False,
            "config": {
                "density": self.style.density,
                "margins": {
                    "top_mm": margin,
                    "right_mm": margin,
                    "bottom_mm": margin,
                    "left_mm": margin,
                },
                "line_spacing": self.style.line_spacing,
                "base_font_size_pt": self.style.base_font_size_pt,
            },
        }
        template = {
            "name": self.template.name,
            "description": self.template.description,
            "is_active": False,
            "config": {
                "page": {
                    "size": self.template.page_size,
                    "orientation": self.template.orientation,
                },
                "layout": self.template.layout,
                "cover": self.template.cover,
                "cover_fields": [
                    field.model_dump()
                    for field in self.template.cover_fields
                ],
                "cover_design": {
                    "alignment": self.template.cover_alignment,
                    "padding_mm": self.template.cover_padding_mm,
                    "typography": {
                        "title_pt": self.template.title_pt,
                        "metadata_pt": self.template.metadata_pt,
                    },
                    "assets": [],
                },
            },
        }
        return theme, style, template
