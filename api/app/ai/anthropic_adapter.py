import json
from typing import Any, Literal

import anthropic

from app.ai.rate_limit_retry import with_rate_limit_retry
from app.ai.openai_schema import build_form_fields_suggestion_schema
from app.ai.prompts import (
    build_form_fields_system_prompt,
    build_form_fields_user_prompt,
    build_rate_card_section_system_prompt,
    build_rate_card_section_user_prompt,
    build_rate_card_system_prompt,
    build_rate_card_user_prompt,
    build_system_prompt,
    build_user_prompt,
)
from app.ai.schemas import (
    EstimateFormFieldsSuggestion,
    ExtractedRequirements,
    GeneratedRateCardSuggestion,
)
from app.ai.section_schemas import section_suggestion_model, section_tool_name
from app.estimates.form_fields import field_metadata_for_prompt, schema_field_keys
from app.schemas.rate_card import RateCardAiSection

AI_TIMEOUT_SECONDS = 90.0


class AnthropicProvider:
    def __init__(self, model: str, api_key: str) -> None:
        self.model = model
        self._client = anthropic.AsyncAnthropic(api_key=api_key, timeout=AI_TIMEOUT_SECONDS)

    async def _create_message(self, **kwargs: Any):
        async def _call():
            return await self._client.messages.create(**kwargs)

        return await with_rate_limit_retry(_call)

    async def extract_requirements(
        self,
        form_data: dict[str, Any],
        document_texts: list[str],
        locale: Literal["ja", "en"],
        *,
        rate_card_roles: list[dict[str, Any]] | None = None,
    ) -> ExtractedRequirements:
        response = await self._create_message(
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

    async def generate_rate_card(
        self,
        *,
        project_name: str,
        client_name: str,
        form_data: dict[str, Any],
        document_texts: list[str],
        locale: Literal["ja", "en"],
        feature_items: list[dict[str, Any]] | None = None,
        extracted_data: dict[str, Any] | None = None,
        complexity_profile: dict[str, Any] | None = None,
        cost_breakdown_hints: dict[str, Any] | None = None,
    ) -> GeneratedRateCardSuggestion:
        has_extraction_context = bool(feature_items or extracted_data or complexity_profile)
        response = await self._create_message(
            model=self.model,
            max_tokens=8192,
            system=build_rate_card_system_prompt(
                locale,
                has_extraction_context=has_extraction_context,
            ),
            messages=[
                {
                    "role": "user",
                    "content": build_rate_card_user_prompt(
                        project_name=project_name,
                        client_name=client_name,
                        form_data=form_data,
                        document_texts=document_texts,
                        feature_items=feature_items,
                        extracted_data=extracted_data,
                        complexity_profile=complexity_profile,
                        cost_breakdown_hints=cost_breakdown_hints,
                    ),
                }
            ],
            tools=[
                {
                    "name": "generate_rate_card",
                    "description": "Generate a recommended rate card for the project.",
                    "input_schema": GeneratedRateCardSuggestion.model_json_schema(),
                }
            ],
            tool_choice={"type": "tool", "name": "generate_rate_card"},
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

        return GeneratedRateCardSuggestion.model_validate(payload)

    async def suggest_rate_card_section(
        self,
        *,
        section: RateCardAiSection,
        prompt: str,
        current_section: list[dict[str, Any]],
        estimate_context: dict[str, Any],
        document_texts: list[str],
        locale: Literal["ja", "en"],
        free_form: bool = False,
    ):
        model = section_suggestion_model(section)
        tool_name = section_tool_name(section)
        response = await self._create_message(
            model=self.model,
            max_tokens=8192,
            system=build_rate_card_section_system_prompt(locale, section, free_form=free_form),
            messages=[
                {
                    "role": "user",
                    "content": build_rate_card_section_user_prompt(
                        prompt=prompt,
                        section=section,
                        current_section=current_section,
                        estimate_context=estimate_context,
                        document_texts=document_texts,
                        free_form=free_form,
                    ),
                }
            ],
            tools=[
                {
                    "name": tool_name,
                    "description": f"Suggest additions for rate card section {section}.",
                    "input_schema": model.model_json_schema(),
                }
            ],
            tool_choice={"type": "tool", "name": tool_name},
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

        return model.model_validate(payload)

    async def suggest_estimate_form_fields(
        self,
        *,
        prompt: str,
        project_name: str,
        client_name: str,
        current_form_data: dict[str, Any],
        document_texts: list[str],
        locale: Literal["ja", "en"],
        form_schema: list[dict[str, Any]],
    ) -> EstimateFormFieldsSuggestion:
        field_keys = schema_field_keys(form_schema)
        field_metadata = field_metadata_for_prompt(form_schema)
        response = await self._create_message(
            model=self.model,
            max_tokens=8192,
            system=build_form_fields_system_prompt(locale, field_metadata),
            messages=[
                {
                    "role": "user",
                    "content": build_form_fields_user_prompt(
                        prompt=prompt,
                        project_name=project_name,
                        client_name=client_name,
                        current_form_data=current_form_data,
                        document_texts=document_texts,
                    ),
                }
            ],
            tools=[
                {
                    "name": "suggest_estimate_form_fields",
                    "description": "Suggest questionnaire form field values for a project estimate.",
                    "input_schema": build_form_fields_suggestion_schema(field_keys),
                }
            ],
            tool_choice={"type": "tool", "name": "suggest_estimate_form_fields"},
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

        return EstimateFormFieldsSuggestion.model_validate(payload)
