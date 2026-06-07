import json
from typing import Any, Literal

import anthropic

from app.ai.prompts import build_system_prompt, build_user_prompt
from app.ai.schemas import ExtractedRequirements

AI_TIMEOUT_SECONDS = 90.0


class AnthropicProvider:
    def __init__(self, model: str, api_key: str) -> None:
        self.model = model
        self._client = anthropic.AsyncAnthropic(api_key=api_key, timeout=AI_TIMEOUT_SECONDS)

    async def extract_requirements(
        self,
        form_data: dict[str, Any],
        document_texts: list[str],
        locale: Literal["ja", "en"],
        *,
        rate_card_roles: list[dict[str, Any]] | None = None,
    ) -> ExtractedRequirements:
        response = await self._client.messages.create(
            model=self.model,
            max_tokens=8192,
            system=build_system_prompt(locale),
            messages=[
                {
                    "role": "user",
                    "content": build_user_prompt(form_data, document_texts, rate_card_roles),
                }
            ],
            tools=[
                {
                    "name": "extract_requirements",
                    "description": "Extract structured project requirements and feature items.",
                    "input_schema": ExtractedRequirements.model_json_schema(),
                }
            ],
            tool_choice={"type": "tool", "name": "extract_requirements"},
        )

        tool_block = next(
            (block for block in response.content if block.type == "tool_use"),
            None,
        )
        if tool_block is None:
            raise ValueError("Anthropic returned no tool_use block")

        payload = tool_block.input
        if isinstance(payload, str):
            payload = json.loads(payload)

        return ExtractedRequirements.model_validate(payload)
