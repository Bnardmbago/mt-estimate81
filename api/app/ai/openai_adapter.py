import json
from typing import Any, Literal

from openai import AsyncOpenAI

from app.ai.rate_limit_retry import with_rate_limit_retry
from app.ai.openai_schema import build_form_fields_suggestion_schema, build_openai_strict_schema
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
from app.estimates.form_fields import field_metadata_for_prompt, schema_field_keys
from app.ai.schemas import (
    EstimateFormFieldsSuggestion,
    ExtractedRequirements,
    GeneratedRateCardSuggestion,
)
from app.ai.section_schemas import section_suggestion_model, section_tool_name
from app.schemas.rate_card import RateCardAiSection

AI_TIMEOUT_SECONDS = 90.0


class OpenAIProvider:
    def __init__(self, model: str, api_key: str) -> None:
        self.model = model
        self._client = AsyncOpenAI(api_key=api_key, timeout=AI_TIMEOUT_SECONDS)

    async def _create_completion(self, **kwargs: Any):
        async def _call():
            return await self._client.chat.completions.create(**kwargs)

        return await with_rate_limit_retry(_call)

    async def extract_requirements(
        self,
        form_data: dict[str, Any],
        document_texts: list[str],
        locale: Literal["ja", "en"],
        *,
        rate_card_roles: list[dict[str, Any]] | None = None,
    ) -> ExtractedRequirements:
        response = await self._create_completion(
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
                    "schema": build_openai_strict_schema(ExtractedRequirements),
                    "strict": True,
                },
            },
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("OpenAI returned an empty response")

        payload = json.loads(content)
        return ExtractedRequirements.model_validate(payload)

    async def generate_rate_card(
        self,
        *,
        project_name: str,
        client_name: str,
        form_data: dict[str, Any],
        document_texts: list[str],
        locale: Literal["ja", "en"],
    ) -> GeneratedRateCardSuggestion:
        response = await self._create_completion(
            model=self.model,
            messages=[
                {"role": "system", "content": build_rate_card_system_prompt(locale)},
                {
                    "role": "user",
                    "content": build_rate_card_user_prompt(
                        project_name=project_name,
                        client_name=client_name,
                        form_data=form_data,
                        document_texts=document_texts,
                    ),
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "generated_rate_card",
                    "schema": build_openai_strict_schema(GeneratedRateCardSuggestion),
                    "strict": True,
                },
            },
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("OpenAI returned an empty response")

        payload = json.loads(content)
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
        response = await self._create_completion(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": build_rate_card_section_system_prompt(
                        locale, section, free_form=free_form
                    ),
                },
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
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": tool_name,
                    "schema": build_openai_strict_schema(model),
                    "strict": True,
                },
            },
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("OpenAI returned an empty response")

        payload = json.loads(content)
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
        response = await self._create_completion(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": build_form_fields_system_prompt(locale, field_metadata),
                },
                {
                    "role": "user",
                    "content": build_form_fields_user_prompt(
                        prompt=prompt,
                        project_name=project_name,
                        client_name=client_name,
                        current_form_data=current_form_data,
                        document_texts=document_texts,
                    ),
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "suggest_estimate_form_fields",
                    "schema": build_form_fields_suggestion_schema(field_keys),
                    "strict": True,
                },
            },
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("OpenAI returned an empty response")

        payload = json.loads(content)
        return EstimateFormFieldsSuggestion.model_validate(payload)
