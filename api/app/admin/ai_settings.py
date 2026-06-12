from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.ai_config import (
    ANTHROPIC_MODELS,
    OPENAI_MODELS,
    get_ai_config,
    mask_api_key,
    update_ai_config,
)
from app.admin.ai_connection_test import test_anthropic_connection, test_openai_connection
from app.dependencies import get_db, require_admin
from app.documents.hermes_client import HermesClient
from app.models.user import User

router = APIRouter(prefix="/admin/ai-settings", tags=["admin"])


class AISettingsResponse(BaseModel):
    ai_provider: Literal["openai", "anthropic"]
    ai_model: str
    openai_api_key_configured: bool
    openai_api_key_hint: str | None
    anthropic_api_key_configured: bool
    anthropic_api_key_hint: str | None
    openai_models: list[str]
    anthropic_models: list[str]
    hermes: str


class AISettingsUpdate(BaseModel):
    ai_provider: Literal["openai", "anthropic"] | None = None
    ai_model: str | None = Field(default=None, min_length=1, max_length=100)
    openai_api_key: str | None = Field(default=None, max_length=255)
    anthropic_api_key: str | None = Field(default=None, max_length=255)
    clear_openai_api_key: bool = False
    clear_anthropic_api_key: bool = False


class AIConnectionTestRequest(BaseModel):
    provider: Literal["openai", "anthropic"]
    api_key: str | None = Field(default=None, max_length=255)
    model: str | None = Field(default=None, max_length=100)


class AIConnectionTestResponse(BaseModel):
    provider: Literal["openai", "anthropic"]
    success: bool
    message: str


def get_hermes_client() -> HermesClient:
    return HermesClient()


async def build_ai_settings_response(
    db: AsyncSession,
    hermes: HermesClient,
) -> AISettingsResponse:
    config = await get_ai_config(db)
    return AISettingsResponse(
        ai_provider=config.ai_provider,
        ai_model=config.ai_model,
        openai_api_key_configured=bool(config.openai_api_key),
        openai_api_key_hint=mask_api_key(config.openai_api_key),
        anthropic_api_key_configured=bool(config.anthropic_api_key),
        anthropic_api_key_hint=mask_api_key(config.anthropic_api_key),
        openai_models=OPENAI_MODELS,
        anthropic_models=ANTHROPIC_MODELS,
        hermes=await hermes.ping(),
    )


@router.get("", response_model=AISettingsResponse)
async def get_ai_settings(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
    hermes: HermesClient = Depends(get_hermes_client),
):
    return await build_ai_settings_response(db, hermes)


@router.patch("", response_model=AISettingsResponse)
async def patch_ai_settings(
    body: AISettingsUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
    hermes: HermesClient = Depends(get_hermes_client),
):
    openai_key = body.openai_api_key.strip() if body.openai_api_key else None
    anthropic_key = body.anthropic_api_key.strip() if body.anthropic_api_key else None

    await update_ai_config(
        db,
        ai_provider=body.ai_provider,
        ai_model=body.ai_model,
        openai_api_key=openai_key if openai_key else None,
        anthropic_api_key=anthropic_key if anthropic_key else None,
        clear_openai_api_key=body.clear_openai_api_key,
        clear_anthropic_api_key=body.clear_anthropic_api_key,
    )
    return await build_ai_settings_response(db, hermes)


@router.post("/test-connection", response_model=AIConnectionTestResponse)
async def test_ai_connection(
    body: AIConnectionTestRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    config = await get_ai_config(db)

    if body.provider == "openai":
        api_key = (body.api_key or "").strip() or config.openai_api_key
        success, message = await test_openai_connection(api_key)
    else:
        api_key = (body.api_key or "").strip() or config.anthropic_api_key
        model = (body.model or "").strip() or config.ai_model or ANTHROPIC_MODELS[0]
        success, message = await test_anthropic_connection(api_key, model)

    return AIConnectionTestResponse(
        provider=body.provider,
        success=success,
        message=message,
    )
