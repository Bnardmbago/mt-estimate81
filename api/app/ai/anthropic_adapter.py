import base64
import json
from typing import Any, Literal

import anthropic

from app.ai.adapter_instructions import AI_TIMEOUT_SECONDS, anthropic_completion_kwargs, max_document_chars
from app.ai.instruction_resolver import ResolvedInstructions, merge_user_message
from app.ai.rate_limit_retry import with_rate_limit_retry
from app.ai.openai_schema import build_form_fields_suggestion_schema
from app.ai.prompts import (
    build_export_translation_system_prompt,
    build_export_translation_user_prompt,
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
    ExportNarrativeTranslation,
    ExtractedRequirements,
    GeneratedRateCardSuggestion,
)
from app.ai.schemas_presentation import PresentationDraftAI
from app.ai.section_schemas import section_suggestion_model, section_tool_name
from app.estimates.form_fields import field_metadata_for_prompt, schema_field_keys
from app.estimates.extraction_constraints import ExtractionConstraints
from app.schemas.rate_card import RateCardAiSection


class AnthropicProvider:
    def __init__(self, model: str, api_key: str) -> None:
        self.model = model
        self._client = anthropic.AsyncAnthropic(api_key=api_key, timeout=AI_TIMEOUT_SECONDS)

    async def _create_message(self, **kwargs: Any):
        async def _call():
            return await self._client.messages.create(**kwargs)

        return await with_rate_limit_retry(_call)

    def supports_vision(self) -> bool:
        model = self.model.casefold()
        return model.startswith("claude-3") or model.startswith(
            ("claude-4", "claude-sonnet-4", "claude-opus-4", "claude-haiku-4")
        )

    async def generate_presentation_draft(
        self,
        *,
        source_locale: Literal["ja", "en"],
        signals: dict[str, Any],
        page_images: list[dict[str, Any]],
    ) -> PresentationDraftAI:
        if not self.supports_vision():
            raise ValueError(f"Model '{self.model}' does not support vision")
        if not page_images:
            raise ValueError("No rasterized reference pages are available")

        content: list[dict[str, Any]] = []
        for image in page_images[:10]:
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image["media_type"],
                        "data": base64.b64encode(image["content"]).decode("ascii"),
                    },
                }
            )
        content.append(
            {
                "type": "text",
                "text": (
                    "Analyze this presentation reference and produce a cohesive Theme, "
                    "Style, and Template draft, including page setup and cover fields. "
                    f"Write names and labels in locale '{source_locale}'. "
                    f"Deterministic signals: {json.dumps(signals, ensure_ascii=False)}"
                ),
            }
        )
        response = await self._create_message(
            model=self.model,
            system=(
                "You are a presentation design analyst. Return safe, practical preset "
                "recommendations grounded in the supplied reference."
            ),
            messages=[{"role": "user", "content": content}],
            tools=[
                {
                    "name": "generate_presentation_draft",
                    "description": "Generate structured presentation preset drafts.",
                    "input_schema": PresentationDraftAI.model_json_schema(),
                }
            ],
            tool_choice={"type": "tool", "name": "generate_presentation_draft"},
            **anthropic_completion_kwargs(None),
        )
        tool_block = next(
            (block for block in response.content if block.type == "tool_use"),
            None,
        )
        if tool_block is None:
            raise ValueError("Anthropic returned no presentation draft tool_use block")
        payload = tool_block.input
        if isinstance(payload, str):
            payload = json.loads(payload)
        return PresentationDraftAI.model_validate(payload)

    async def extract_requirements(
        self,
        form_data: dict[str, Any],
        document_texts: list[str],
        locale: Literal["ja", "en"],
        *,
        rate_card_roles: list[dict[str, Any]] | None = None,
        instructions: ResolvedInstructions | None = None,
        client_constraints: ExtractionConstraints | None = None,
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
            client_constraints=client_constraints,
            locale=locale,
            constraints_section_template=(
                instructions.constraints_section_template if instructions else None
            ),
        )
        if instructions:
            user_content = merge_user_message(instructions.user_prefix, user_content)

        response = await self._create_message(
            model=self.model,
            system=system,
            messages=[{"role": "user", "content": user_content}],
            tools=[
                {
                    "name": "extract_requirements",
                    "description": "Extract structured project requirements and feature items.",
                    "input_schema": ExtractedRequirements.model_json_schema(),
                }
            ],
            tool_choice={"type": "tool", "name": "extract_requirements"},
            **anthropic_completion_kwargs(instructions),
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

        response = await self._create_message(
            model=self.model,
            system=system,
            messages=[{"role": "user", "content": user_content}],
            tools=[
                {
                    "name": "generate_rate_card",
                    "description": "Generate a recommended rate card for the project.",
                    "input_schema": GeneratedRateCardSuggestion.model_json_schema(),
                }
            ],
            tool_choice={"type": "tool", "name": "generate_rate_card"},
            **anthropic_completion_kwargs(instructions),
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

        response = await self._create_message(
            model=self.model,
            system=system,
            messages=[{"role": "user", "content": user_content}],
            tools=[
                {
                    "name": tool_name,
                    "description": f"Suggest additions for rate card section {section}.",
                    "input_schema": model.model_json_schema(),
                }
            ],
            tool_choice={"type": "tool", "name": tool_name},
            **anthropic_completion_kwargs(instructions),
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

        response = await self._create_message(
            model=self.model,
            system=system,
            messages=[{"role": "user", "content": user_content}],
            tools=[
                {
                    "name": "suggest_estimate_form_fields",
                    "description": "Suggest questionnaire form field values for a project estimate.",
                    "input_schema": build_form_fields_suggestion_schema(field_keys),
                }
            ],
            tool_choice={"type": "tool", "name": "suggest_estimate_form_fields"},
            **anthropic_completion_kwargs(instructions),
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

    async def translate_export_narrative(
        self,
        *,
        source_locale: Literal["ja", "en"],
        target_locale: Literal["ja", "en"],
        payload: dict[str, Any],
    ) -> ExportNarrativeTranslation:
        system = build_export_translation_system_prompt(target_locale)
        user_content = build_export_translation_user_prompt(payload)
        response = await self._create_message(
            model=self.model,
            system=system,
            messages=[{"role": "user", "content": user_content}],
            tools=[
                {
                    "name": "translate_export_narrative",
                    "description": "Translate estimate narrative content for export.",
                    "input_schema": ExportNarrativeTranslation.model_json_schema(),
                }
            ],
            tool_choice={"type": "tool", "name": "translate_export_narrative"},
            **anthropic_completion_kwargs(None),
        )
        tool_block = next(
            (block for block in response.content if block.type == "tool_use"),
            None,
        )
        if tool_block is None:
            raise ValueError("Anthropic returned no tool_use block for translation")
        tool_payload = tool_block.input
        if isinstance(tool_payload, str):
            tool_payload = json.loads(tool_payload)
        return ExportNarrativeTranslation.model_validate(tool_payload)
