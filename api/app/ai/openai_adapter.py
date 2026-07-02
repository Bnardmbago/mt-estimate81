import json
from typing import Any, Literal

from openai import AsyncOpenAI

from app.ai.adapter_instructions import AI_TIMEOUT_SECONDS, completion_kwargs, max_document_chars
from app.ai.instruction_resolver import ResolvedInstructions, merge_user_message
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
        instructions: ResolvedInstructions | None = None,
    ) -> ExtractedRequirements:
        doc_chars = max_document_chars(instructions)
        system = (
            instructions.system
            if instructions
            else build_system_prompt(locale)
        )
        user_content = build_user_prompt(
            form_data,
            document_texts,
            rate_card_roles,
            max_document_chars=doc_chars,
        )
        if instructions:
            user_content = merge_user_message(instructions.user_prefix, user_content)

        response = await self._create_completion(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "extracted_requirements",
                    "schema": build_openai_strict_schema(ExtractedRequirements),
                    "strict": True,
                },
            },
            **completion_kwargs(instructions),
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
        feature_items: list[dict[str, Any]] | None = None,
        extracted_data: dict[str, Any] | None = None,
        complexity_profile: dict[str, Any] | None = None,
        cost_breakdown_hints: dict[str, Any] | None = None,
        instructions: ResolvedInstructions | None = None,
    ) -> GeneratedRateCardSuggestion:
        has_extraction_context = bool(feature_items or extracted_data or complexity_profile)
        doc_chars = max_document_chars(instructions)
        system = (
            instructions.system
            if instructions
            else build_rate_card_system_prompt(
                locale,
                has_extraction_context=has_extraction_context,
            )
        )
        user_content = build_rate_card_user_prompt(
            project_name=project_name,
            client_name=client_name,
            form_data=form_data,
            document_texts=document_texts,
            feature_items=feature_items,
            extracted_data=extracted_data,
            complexity_profile=complexity_profile,
            cost_breakdown_hints=cost_breakdown_hints,
            max_document_chars=doc_chars,
        )
        if instructions:
            user_content = merge_user_message(instructions.user_prefix, user_content)

        response = await self._create_completion(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "generated_rate_card",
                    "schema": build_openai_strict_schema(GeneratedRateCardSuggestion),
                    "strict": True,
                },
            },
            **completion_kwargs(instructions),
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
        instructions: ResolvedInstructions | None = None,
    ):
        model = section_suggestion_model(section)
        tool_name = section_tool_name(section)
        doc_chars = max_document_chars(instructions)
        system = (
            instructions.system
            if instructions
            else build_rate_card_section_system_prompt(locale, section, free_form=free_form)
        )
        user_content = build_rate_card_section_user_prompt(
            prompt=prompt,
            section=section,
            current_section=current_section,
            estimate_context=estimate_context,
            document_texts=document_texts,
            free_form=free_form,
            max_document_chars=doc_chars,
        )
        if instructions:
            user_content = merge_user_message(instructions.user_prefix, user_content)

        response = await self._create_completion(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": tool_name,
                    "schema": build_openai_strict_schema(model),
                    "strict": True,
                },
            },
            **completion_kwargs(instructions),
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
        instructions: ResolvedInstructions | None = None,
    ) -> EstimateFormFieldsSuggestion:
        field_keys = schema_field_keys(form_schema)
        field_metadata = field_metadata_for_prompt(form_schema)
        doc_chars = max_document_chars(instructions)
        system = (
            instructions.system
            if instructions
            else build_form_fields_system_prompt(locale, field_metadata)
        )
        user_content = build_form_fields_user_prompt(
            prompt=prompt,
            project_name=project_name,
            client_name=client_name,
            current_form_data=current_form_data,
            document_texts=document_texts,
            max_document_chars=doc_chars,
        )
        if instructions:
            user_content = merge_user_message(instructions.user_prefix, user_content)

        response = await self._create_completion(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "suggest_estimate_form_fields",
                    "schema": build_form_fields_suggestion_schema(field_keys),
                    "strict": True,
                },
            },
            **completion_kwargs(instructions),
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("OpenAI returned an empty response")

        payload = json.loads(content)
        return EstimateFormFieldsSuggestion.model_validate(payload)
