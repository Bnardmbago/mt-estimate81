from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.ai_instruction_config import (
    get_default_parameters,
    get_instruction_layer,
    is_valid_locale,
    is_valid_location,
    list_instruction_layers,
    merge_parameters,
    reset_instruction_layer,
    upsert_instruction_layer,
)
from app.admin.ai_instruction_preview import build_preview_base_system, layer_to_dict
from app.ai.instruction_resolver import preview_instructions
from app.dependencies import get_db, require_admin
from app.models.ai_instruction_layer import INSTRUCTION_LOCATIONS, InstructionLocation
from app.models.user import User

router = APIRouter(prefix="/admin/ai-instruction-layers", tags=["admin"])

InstructionLocale = Literal["en", "ja"]


class InstructionParameters(BaseModel):
    max_tokens: int | None = Field(default=None, ge=256, le=8192)
    temperature: float | None = Field(default=None, ge=0.0, le=1.0)
    timeout_seconds: int | None = Field(default=None, ge=30, le=120)
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
) -> InstructionLayerResponse:
    base_system = build_preview_base_system(location, locale)
    resolved = preview_instructions(
        location=location,
        locale=locale,
        base_system=base_system,
        system_prompt=layer_data["system_prompt"],
        default_prompt=layer_data["default_prompt"],
        user_prompt=layer_data["user_prompt"],
        negative_prompt=layer_data["negative_prompt"],
        parameters=layer_data["parameters"],
    )
    from app.admin.ai_instruction_config import PARAMETER_BOUNDS

    return InstructionLayerResponse(
        location=location,
        locale=locale,
        layer=InstructionLayerData(**layer_data),
        preview=InstructionPreview(
            system=resolved.system,
            user_prefix=resolved.user_prefix,
            parameters=resolved.parameters,
        ),
        parameter_defaults=get_default_parameters(location),
        parameter_bounds={key: [low, high] for key, (low, high) in PARAMETER_BOUNDS.items()},
    )


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
    return _build_response(loc, lang, layer_to_dict(row))


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

    return _build_response(loc, lang, layer_to_dict(row))


@router.delete("/{location}/{locale}", response_model=InstructionLayerResponse)
async def delete_layer(
    location: str,
    locale: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    loc, lang = _validate_path_params(location, locale)
    await reset_instruction_layer(db, loc, lang)
    return _build_response(loc, lang, layer_to_dict(None))
