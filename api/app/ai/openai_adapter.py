import json
from typing import Any, Literal

from openai import AsyncOpenAI

from app.ai.prompts import build_system_prompt, build_user_prompt
from app.ai.schemas import ExtractedRequirements

AI_TIMEOUT_SECONDS = 90.0


class OpenAIProvider:
    def __init__(self, model: str, api_key: str) -> None:
        self.model = model
        self._client = AsyncOpenAI(api_key=api_key, timeout=AI_TIMEOUT_SECONDS)

    async def extract_requirements(
        self,
        form_data: dict[str, Any],
        document_texts: list[str],
        locale: Literal["ja", "en"],
        *,
        rate_card_roles: list[dict[str, Any]] | None = None,
    ) -> ExtractedRequirements:
        response = await self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": build_system_prompt(locale)},
                {
                    "role": "user",
                    "content": build_user_prompt(form_data, document_texts, rate_card_roles),
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "extracted_requirements",
                    "schema": ExtractedRequirements.model_json_schema(),
                    "strict": True,
                },
            },
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("OpenAI returned an empty response")

        payload = json.loads(content)
        return ExtractedRequirements.model_validate(payload)
