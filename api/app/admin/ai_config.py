from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

OPENAI_MODELS = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4-turbo",
]

ANTHROPIC_MODELS = [
    "claude-opus-4-8",
    "claude-opus-4-7",
    "claude-opus-4-6",
    "claude-opus-4-5-20251101",
    "claude-sonnet-4-6",
    "claude-sonnet-4-5",
    "claude-sonnet-4-5-20250929",
    "claude-haiku-4-5",
    "claude-haiku-4-5-20251001",
]

# Recommended default for estimate extraction (balance of quality and cost).
ANTHROPIC_DEFAULT_MODEL = "claude-sonnet-4-6"

# Lightweight model used to verify API keys (cheap, widely available).
ANTHROPIC_CONNECTION_TEST_MODEL = "claude-haiku-4-5"

# Retired model IDs → current equivalents (see Anthropic model deprecation notices).
LEGACY_ANTHROPIC_MODEL_MAP: dict[str, str] = {
    "claude-sonnet-4-20250514": "claude-sonnet-4-6",
    "claude-3-5-sonnet-latest": "claude-sonnet-4-6",
    "claude-3-5-haiku-latest": "claude-haiku-4-5",
    "claude-3-opus-20240229": "claude-opus-4-6",
}


def normalize_anthropic_model(model: str) -> str:
    return LEGACY_ANTHROPIC_MODEL_MAP.get(model, model)

AIProviderName = Literal["openai", "anthropic"]


@dataclass(frozen=True)
class AIConfig:
    ai_provider: AIProviderName
    ai_model: str
    openai_api_key: str
    anthropic_api_key: str


def mask_api_key(api_key: str | None) -> str | None:
    if not api_key:
        return None
    if len(api_key) <= 4:
        return "****"
    return f"...{api_key[-4:]}"


async def _get_config_row(db: AsyncSession):
    from app.models.system_config import SystemConfig

    result = await db.execute(select(SystemConfig).where(SystemConfig.id == 1))
    row = result.scalar_one_or_none()
    if row is None:
        row = SystemConfig(id=1)
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


async def get_ai_config(db: AsyncSession) -> AIConfig:
    row = await _get_config_row(db)
    provider = row.ai_provider or settings.ai_provider
    if provider not in ("openai", "anthropic"):
        provider = "openai"

    default_model = OPENAI_MODELS[0] if provider == "openai" else ANTHROPIC_DEFAULT_MODEL
    model = row.ai_model or settings.ai_model or default_model
    if provider == "anthropic":
        model = normalize_anthropic_model(model)

    return AIConfig(
        ai_provider=provider,  # type: ignore[arg-type]
        ai_model=model,
        openai_api_key=row.openai_api_key or settings.openai_api_key,
        anthropic_api_key=row.anthropic_api_key or settings.anthropic_api_key,
    )


async def update_ai_config(
    db: AsyncSession,
    *,
    ai_provider: AIProviderName | None = None,
    ai_model: str | None = None,
    openai_api_key: str | None = None,
    anthropic_api_key: str | None = None,
    clear_openai_api_key: bool = False,
    clear_anthropic_api_key: bool = False,
) -> AIConfig:
    row = await _get_config_row(db)

    if ai_provider is not None:
        row.ai_provider = ai_provider
    if ai_model is not None:
        row.ai_model = ai_model
    if openai_api_key is not None:
        row.openai_api_key = openai_api_key
    elif clear_openai_api_key:
        row.openai_api_key = None
    if anthropic_api_key is not None:
        row.anthropic_api_key = anthropic_api_key
    elif clear_anthropic_api_key:
        row.anthropic_api_key = None

    row.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(row)
    return await get_ai_config(db)
