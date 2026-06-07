from app.ai.anthropic_adapter import AnthropicProvider
from app.ai.openai_adapter import OpenAIProvider
from app.ai.provider import AIProvider
from app.config import settings


def get_ai_provider() -> AIProvider:
    if settings.ai_provider == "anthropic":
        return AnthropicProvider(model=settings.ai_model, api_key=settings.anthropic_api_key)
    return OpenAIProvider(model=settings.ai_model, api_key=settings.openai_api_key)
