from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.ai_config import get_ai_config
from app.ai.anthropic_adapter import AnthropicProvider
from app.ai.openai_adapter import OpenAIProvider
from app.ai.provider import AIProvider


async def get_ai_provider(db: AsyncSession) -> AIProvider:
    config = await get_ai_config(db)
    if config.ai_provider == "anthropic":
        return AnthropicProvider(model=config.ai_model, api_key=config.anthropic_api_key)
    return OpenAIProvider(model=config.ai_model, api_key=config.openai_api_key)
