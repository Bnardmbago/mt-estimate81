from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.ai_instruction_config import (
    effective_prompt_fields,
    get_default_parameters,
    get_instruction_layer,
    get_prompt_defaults,
    is_valid_locale,
    is_valid_location,
    list_instruction_layers,
    merge_parameters,
    reset_instruction_layer,
    upsert_instruction_layer,
)
from app.admin.ai_instruction_preview import layer_to_dict
from app.ai.instruction_resolver import (
    ResolvedInstructions,
    merge_client_constraint_instructions,
    merge_system_prompt,
    preview_instructions as base_preview_instructions,
)
from app.dependencies import get_db, require_admin
from app.models.ai_instruction_layer import INSTRUCTION_LOCATIONS, InstructionLocation
from app.models.user import User

router = APIRouter(prefix="/admin/ai-instruction-layers", tags=["admin"])

InstructionLocale = Literal["en", "ja"]


class InstructionParameters(BaseModel):
    max_tokens: int | None = Field(default=None, ge=256, le=16384)
    temperature: float | None = Field(default=None, ge=0.0, le=1.0)
    timeout_seconds: int | None = Field(default=None, ge=30, le=180)
    max_document_chars: int | None = Field(default=None, ge=5000, le=80000)


class InstructionLayerData(BaseModel):
    system_prompt: str | None = None
    default_prompt: str | None = None
    user_prompt: str | None = None
    negative_prompt: str | None = None
    parameters: InstructionParameters | None = None
    updated_at: str | None = None


class InstructionPreview(BaseModel):
    system: str
    user_prefix: str
    parameters: dict[str, int | float]


class InstructionLayerResponse(BaseModel):
    location: InstructionLocation
    locale: InstructionLocale
    layer: InstructionLayerData
    effective_prompt: InstructionLayerData
    prompt_defaults: InstructionLayerData
    preview: InstructionPreview
    parameter_defaults: dict[str, int | float]
    parameter_bounds: dict[str, list[int | float]]


class InstructionLayerListItem(BaseModel):
    location: InstructionLocation
    locale: InstructionLocale
    layer: InstructionLayerData


class InstructionLayerListResponse(BaseModel):
    locations: list[str]
    items: list[InstructionLayerListItem]


class InstructionLayerUpdate(BaseModel):
    system_prompt: str | None = None
    default_prompt: str | None = None
    user_prompt: str | None = None
    negative_prompt: str | None = None
    parameters: InstructionParameters | None = None
    clear_system_prompt: bool = False
    clear_default_prompt: bool = False
    clear_user_prompt: bool = False
    clear_negative_prompt: bool = False
    clear_parameters: bool = False


def _validate_path_params(location: str, locale: str) -> tuple[str, str]:
    if not is_valid_location(location):
        raise HTTPException(
            status_code=404,
            detail={"error": f"Unknown location: {location}", "code": "INVALID_LOCATION"},
        )
    if not is_valid_locale(locale):
        raise HTTPException(
            status_code=404,
            detail={"error": f"Unknown locale: {locale}", "code": "INVALID_LOCALE"},
        )
    return location, locale


def _parameters_to_dict(parameters: InstructionParameters | None) -> dict[str, Any] | None:
    if parameters is None:
        return None
    data = parameters.model_dump(exclude_none=True)
    return data or None


def _build_response(
    location: InstructionLocation,
    locale: InstructionLocale,
    layer_data: dict[str, Any],
    *,
    row: Any | None = None,
    purpose_defaults: dict[str, int | float] | None = None,
) -> InstructionLayerResponse:
    defaults = get_prompt_defaults(location, locale)
    effective = effective_prompt_fields(location, locale, row)
    prompt_defaults = InstructionLayerData(
        system_prompt=defaults.get("system_prompt"),
        default_prompt=defaults.get("default_prompt"),
        user_prompt=defaults.get("user_prompt"),
        negative_prompt=defaults.get("negative_prompt"),
        parameters=None,
        updated_at=None,
    )
    effective_prompt = InstructionLayerData(
        system_prompt=effective.get("system_prompt"),
        default_prompt=effective.get("default_prompt"),
        user_prompt=effective.get("user_prompt"),
        negative_prompt=effective.get("negative_prompt"),
        parameters=layer_data.get("parameters"),
        updated_at=layer_data.get("updated_at"),
    )

    if location == "extraction_client_constraints":
        from app.estimates.extraction_constraints import (
            ExtractionConstraints,
            format_constraints_for_prompt,
        )

        extraction_effective = effective_prompt_fields("extraction", locale, None)
        base = ResolvedInstructions(
            system=merge_system_prompt(
                location="extraction",
                base_system="",
                system_prompt=extraction_effective.get("system_prompt"),
                default_prompt=extraction_effective.get("default_prompt"),
                negative_prompt=extraction_effective.get("negative_prompt"),
            ),
            user_prefix="",
            parameters=get_default_parameters("extraction"),
        )
        constraint_prompts = {
            "system_prompt": effective.get("system_prompt"),
            "default_prompt": effective.get("default_prompt"),
            "user_prompt": effective.get("user_prompt"),
            "negative_prompt": effective.get("negative_prompt"),
        }
        merged = merge_client_constraint_instructions(base, constraint_prompts)
        sample_constraints = ExtractionConstraints(
            client_budget_jpy=5_000_000,
            max_labor_jpy=3_250_000,
            blended_hourly_rate_jpy=10_000,
            max_hours_budget=325.0,
            delivery_schedule="within_3_6_months",
            target_working_days=130,
            max_hours_schedule=1040.0,
            max_hours=325.0,
            binding_constraint="budget",
        )
        sample_section = format_constraints_for_prompt(
            sample_constraints,
            locale,
            template=effective.get("user_prompt"),
        )
        resolved = ResolvedInstructions(
            system=merged.system,
            user_prefix=f"## Client Constraints\n{sample_section}",
            parameters=get_default_parameters(location),
        )
    else:
        resolved = base_preview_instructions(
            location=location,
            locale=locale,
            base_system="",
            system_prompt=effective.get("system_prompt"),
            default_prompt=effective.get("default_prompt"),
            user_prompt=effective.get("user_prompt"),
            negative_prompt=effective.get("negative_prompt"),
            parameters=layer_data["parameters"],
            parameter_defaults=purpose_defaults,
        )
    from app.admin.ai_instruction_config import PARAMETER_BOUNDS

    return InstructionLayerResponse(
        location=location,
        locale=locale,
        layer=InstructionLayerData(**layer_data),
        effective_prompt=effective_prompt,
        prompt_defaults=prompt_defaults,
        preview=InstructionPreview(
            system=resolved.system,
            user_prefix=resolved.user_prefix,
            parameters=resolved.parameters,
        ),
        parameter_defaults=get_default_parameters(location, purpose_defaults=purpose_defaults),
        parameter_bounds={key: [low, high] for key, (low, high) in PARAMETER_BOUNDS.items()},
    )


async def _purpose_defaults_for_location(
    db: AsyncSession,
    location: InstructionLocation,
) -> dict[str, int | float] | None:
    from app.admin.proposal_ai_config import get_proposal_ai_settings
    from app.proposals.generation_presets import LOCATION_TO_PART, budget_parameters, purpose_for_part

    part = LOCATION_TO_PART.get(location)
    if part is None:
        return None
    settings = await get_proposal_ai_settings(db)
    purpose = purpose_for_part(settings, part)
    return budget_parameters(purpose)


@router.get("", response_model=InstructionLayerListResponse)
async def list_layers(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    rows = await list_instruction_layers(db)
    items = [
        InstructionLayerListItem(
            location=row.location,  # type: ignore[arg-type]
            locale=row.locale,  # type: ignore[arg-type]
            layer=InstructionLayerData(**layer_to_dict(row)),
        )
        for row in rows
    ]
    return InstructionLayerListResponse(locations=list(INSTRUCTION_LOCATIONS), items=items)


@router.get("/{location}/{locale}", response_model=InstructionLayerResponse)
async def get_layer(
    location: str,
    locale: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    loc, lang = _validate_path_params(location, locale)
    row = await get_instruction_layer(db, loc, lang)
    purpose_defaults = await _purpose_defaults_for_location(db, loc)
    return _build_response(
        loc, lang, layer_to_dict(row), row=row, purpose_defaults=purpose_defaults
    )


@router.patch("/{location}/{locale}", response_model=InstructionLayerResponse)
async def patch_layer(
    location: str,
    locale: str,
    body: InstructionLayerUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    loc, lang = _validate_path_params(location, locale)

    has_update = any(
        [
            body.system_prompt is not None,
            body.default_prompt is not None,
            body.user_prompt is not None,
            body.negative_prompt is not None,
            body.parameters is not None,
            body.clear_system_prompt,
            body.clear_default_prompt,
            body.clear_user_prompt,
            body.clear_negative_prompt,
            body.clear_parameters,
        ]
    )
    if not has_update:
        raise HTTPException(
            status_code=400,
            detail={"error": "At least one field must be provided", "code": "INVALID_SETTINGS"},
        )

    try:
        row = await upsert_instruction_layer(
            db,
            location=loc,
            locale=lang,
            system_prompt=body.system_prompt,
            default_prompt=body.default_prompt,
            user_prompt=body.user_prompt,
            negative_prompt=body.negative_prompt,
            parameters=_parameters_to_dict(body.parameters),
            clear_system_prompt=body.clear_system_prompt,
            clear_default_prompt=body.clear_default_prompt,
            clear_user_prompt=body.clear_user_prompt,
            clear_negative_prompt=body.clear_negative_prompt,
            clear_parameters=body.clear_parameters,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": str(exc), "code": "INVALID_INSTRUCTION_LAYER"},
        ) from exc

    purpose_defaults = await _purpose_defaults_for_location(db, loc)
    return _build_response(
        loc, lang, layer_to_dict(row), row=row, purpose_defaults=purpose_defaults
    )


@router.delete("/{location}/{locale}", response_model=InstructionLayerResponse)
async def delete_layer(
    location: str,
    locale: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    loc, lang = _validate_path_params(location, locale)
    await reset_instruction_layer(db, loc, lang)
    purpose_defaults = await _purpose_defaults_for_location(db, loc)
    return _build_response(
        loc, lang, layer_to_dict(None), row=None, purpose_defaults=purpose_defaults
    )
