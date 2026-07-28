"""Purpose presets for proposal Assessment / Proposal / PoC generation depth and budget."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

GenerationPurpose = Literal["concise", "standard", "detailed"]
GenerationPart = Literal["assessment", "proposal", "poc"]

GENERATION_PURPOSES: tuple[GenerationPurpose, ...] = ("concise", "standard", "detailed")

DEFAULT_PROPOSAL_AI_SETTINGS: dict[str, GenerationPurpose] = {
    "assessment_purpose": "standard",
    "proposal_purpose": "detailed",
    "poc_purpose": "detailed",
}

PART_TO_SETTINGS_KEY: dict[GenerationPart, str] = {
    "assessment": "assessment_purpose",
    "proposal": "proposal_purpose",
    "poc": "poc_purpose",
}

LOCATION_TO_PART: dict[str, GenerationPart] = {
    "proposal_assessment": "assessment",
    "proposal_body": "proposal",
    "proposal_poc": "poc",
}


@dataclass(frozen=True)
class PurposePreset:
    purpose: GenerationPurpose
    # Prompt depth
    section_guidance: str
    section_guidance_ja: str
    min_diagrams: int
    min_tables_proposal: int
    min_tables_poc: int
    # Budget
    max_tokens: int
    timeout_seconds: int
    temperature: float = 0.0


PURPOSE_PRESETS: dict[GenerationPurpose, PurposePreset] = {
    "concise": PurposePreset(
        purpose="concise",
        section_guidance=(
            "Keep each section concise: 1–2 sentences plus light bullets where lists help. "
            "Prefer brevity over exhaustive detail."
        ),
        section_guidance_ja=(
            "各セクションは簡潔に：1〜2文と必要に応じた短い箇条書き。"
            "網羅性より簡潔さを優先する。"
        ),
        min_diagrams=1,
        min_tables_proposal=1,
        min_tables_poc=1,
        max_tokens=4096,
        timeout_seconds=90,
    ),
    "standard": PurposePreset(
        purpose="standard",
        section_guidance=(
            "Produce clear analysis — several sentences per section, not one-liners. "
            "Add concrete bullets (3–6) where lists clarify scope, criteria, or next steps."
        ),
        section_guidance_ja=(
            "各セクションは一文で終わらせず、複数文で分かりやすく書く。"
            "範囲・基準・次のステップなどは箇条書き（3〜6項目）を併用する。"
        ),
        min_diagrams=2,
        min_tables_proposal=2,
        min_tables_poc=2,
        max_tokens=8192,
        timeout_seconds=120,
    ),
    "detailed": PurposePreset(
        purpose="detailed",
        section_guidance=(
            "Produce detailed, persuasive analysis — several sentences per section "
            "(typically 2–4 short paragraphs), not one-liners. "
            "Add concrete bullets (3–6) where lists clarify objectives, scope, "
            "deliverables, assumptions, risks, or next steps."
        ),
        section_guidance_ja=(
            "詳細で説得力のある文章にする。各セクションは一文で終わらせず、"
            "通常2〜4の短い段落で書く。目的・範囲・成果物・前提・リスク・次のステップなどは"
            "箇条書き（3〜6項目）を併用する。"
        ),
        min_diagrams=2,
        min_tables_proposal=2,
        min_tables_poc=3,
        max_tokens=16384,
        timeout_seconds=150,
    ),
}


def coerce_purpose(value: object | None, *, fallback: GenerationPurpose) -> GenerationPurpose:
    if isinstance(value, str) and value in PURPOSE_PRESETS:
        return value  # type: ignore[return-value]
    return fallback


def normalize_proposal_ai_settings(raw: dict | None) -> dict[str, GenerationPurpose]:
    data = dict(DEFAULT_PROPOSAL_AI_SETTINGS)
    if not raw:
        return data
    for key, fallback in DEFAULT_PROPOSAL_AI_SETTINGS.items():
        data[key] = coerce_purpose(raw.get(key), fallback=fallback)
    return data


def purpose_for_part(
    settings: dict[str, GenerationPurpose],
    part: GenerationPart,
) -> GenerationPurpose:
    key = PART_TO_SETTINGS_KEY[part]
    return coerce_purpose(settings.get(key), fallback=DEFAULT_PROPOSAL_AI_SETTINGS[key])


def get_preset(purpose: GenerationPurpose) -> PurposePreset:
    return PURPOSE_PRESETS[purpose]


def budget_parameters(purpose: GenerationPurpose) -> dict[str, int | float]:
    preset = get_preset(purpose)
    return {
        "max_tokens": preset.max_tokens,
        "temperature": preset.temperature,
        "timeout_seconds": preset.timeout_seconds,
        "max_document_chars": 80_000,
    }


def min_tables_for_part(purpose: GenerationPurpose, part: GenerationPart) -> int:
    preset = get_preset(purpose)
    if part == "poc":
        return preset.min_tables_poc
    if part == "proposal":
        return preset.min_tables_proposal
    return 0


def purpose_for_location(
    settings: dict[str, GenerationPurpose],
    location: str,
) -> GenerationPurpose | None:
    part = LOCATION_TO_PART.get(location)
    if part is None:
        return None
    return purpose_for_part(settings, part)
