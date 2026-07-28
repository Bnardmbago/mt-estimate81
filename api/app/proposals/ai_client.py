"""Real AI generation for proposal parts (OpenAI / Anthropic) with None on failure."""

from __future__ import annotations

import json
import logging
from typing import Any, Literal, TypeVar

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.ai_config import get_ai_config
from app.admin.proposal_ai_config import get_proposal_ai_settings
from app.ai.adapter_instructions import AI_TIMEOUT_SECONDS, anthropic_completion_kwargs
from app.ai.instruction_resolver import merge_user_message, resolve_instructions
from app.ai.openai_schema import build_openai_strict_schema
from app.ai.rate_limit_retry import with_rate_limit_retry
from app.database import SessionLocal
from app.proposals.generation_presets import (
    GenerationPurpose,
    budget_parameters,
    purpose_for_part,
)
from app.proposals.prompts import (
    build_assessment_system_prompt,
    build_assessment_user_prompt,
    build_poc_system_prompt,
    build_poc_user_prompt,
    build_proposal_system_prompt,
    build_proposal_user_prompt,
)
from app.proposals.schemas_ai import (
    ProposalAssessmentAI,
    ProposalBodyAI,
    ProposalPocAI,
)

logger = logging.getLogger(__name__)

Locale = Literal["ja", "en"]
T = TypeVar("T", bound=BaseModel)

_DEFAULT_MAX_TOKENS = 8192


def _section_to_dict(section: Any) -> dict[str, Any]:
    data = {
        "id": section.id,
        "title": section.title,
        "body": section.body or "",
        "user_edited": False,
    }
    if section.bullets:
        data["bullets"] = list(section.bullets)
    if section.rating:
        data["rating"] = section.rating
    if section.feature_ids:
        data["feature_ids"] = list(section.feature_ids)
    if section.drivers:
        data["drivers"] = list(section.drivers)
    if section.poc_recommended:
        data["poc_recommended"] = True
    return data


def _assessment_to_storage(model: ProposalAssessmentAI) -> dict[str, Any]:
    return {
        "sections": [_section_to_dict(s) for s in model.sections],
        "poc_recommended": bool(model.poc_recommended),
        "summary_cost_note": model.summary_cost_note or "",
    }


def _proposal_to_storage(
    model: ProposalBodyAI,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    body = {
        "sections": [_section_to_dict(s) for s in model.sections],
        "tables": [
            {
                "id": t.id,
                "title": t.title,
                "headers": list(t.headers or []),
                "rows": [list(row) for row in (t.rows or [])],
            }
            for t in (model.tables or [])
        ],
    }
    diagrams = [
        {
            "id": d.id,
            "title": d.title,
            "engine": d.engine,
            "source": d.source,
        }
        for d in model.diagrams
    ]
    milestones = [
        {"id": m.id, "name": m.name, "date": m.date or None}
        for m in model.milestones
    ]
    return body, diagrams, milestones


def _poc_to_storage(model: ProposalPocAI) -> dict[str, Any]:
    sections = [_section_to_dict(s) for s in model.sections]
    selected = list(model.selected_feature_ids or [])
    if not selected:
        for section in sections:
            if section.get("id") in {"scope_in", "in_scope"} and section.get("feature_ids"):
                selected = list(section["feature_ids"])
                break
    brief = model.project_brief.model_dump() if model.project_brief else {}
    return {
        "project_brief": brief,
        "sections": sections,
        "tables": [
            {
                "id": t.id,
                "title": t.title,
                "headers": list(t.headers or []),
                "rows": [list(row) for row in (t.rows or [])],
            }
            for t in (model.tables or [])
        ],
        "diagrams": [
            {
                "id": d.id,
                "title": d.title,
                "engine": d.engine,
                "source": d.source,
            }
            for d in (model.diagrams or [])
        ],
        "milestones": [
            {"id": m.id, "name": m.name, "date": m.date or None}
            for m in (model.milestones or [])
        ],
        "suggested_validation_window": model.suggested_validation_window or "",
        "official": {"selected_feature_ids": selected},
    }


def _budget_from_parameters(parameters: dict[str, int | float]) -> tuple[int, float, float | None]:
    max_tokens = int(parameters.get("max_tokens") or _DEFAULT_MAX_TOKENS)
    timeout_seconds = float(parameters.get("timeout_seconds") or AI_TIMEOUT_SECONDS)
    temperature = parameters.get("temperature")
    temp_value = float(temperature) if temperature is not None else None
    return max_tokens, timeout_seconds, temp_value


async def _complete_openai(
    *,
    model: str,
    api_key: str,
    system: str,
    user: str,
    schema_model: type[T],
    schema_name: str,
    max_tokens: int = _DEFAULT_MAX_TOKENS,
    timeout_seconds: float = AI_TIMEOUT_SECONDS,
    temperature: float | None = None,
) -> T:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key, timeout=timeout_seconds)

    async def _call():
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "schema": build_openai_strict_schema(schema_model),
                    "strict": True,
                },
            },
            "max_tokens": max_tokens,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        return await client.chat.completions.create(**kwargs)

    response = await with_rate_limit_retry(_call)
    content = response.choices[0].message.content
    if not content:
        raise ValueError("OpenAI returned an empty proposal response")
    return schema_model.model_validate(json.loads(content))


async def _complete_anthropic(
    *,
    model: str,
    api_key: str,
    system: str,
    user: str,
    schema_model: type[T],
    tool_name: str,
    tool_description: str,
    max_tokens: int = _DEFAULT_MAX_TOKENS,
    timeout_seconds: float = AI_TIMEOUT_SECONDS,
    temperature: float | None = None,
) -> T:
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=api_key, timeout=timeout_seconds)

    async def _call():
        kwargs = anthropic_completion_kwargs(None)
        kwargs["max_tokens"] = max_tokens
        if temperature is not None:
            kwargs["temperature"] = temperature
        return await client.messages.create(
            model=model,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=[
                {
                    "name": tool_name,
                    "description": tool_description,
                    "input_schema": schema_model.model_json_schema(),
                }
            ],
            tool_choice={"type": "tool", "name": tool_name},
            **kwargs,
        )

    response = await with_rate_limit_retry(_call)
    tool_block = next(
        (block for block in response.content if getattr(block, "type", None) == "tool_use"),
        None,
    )
    if tool_block is None:
        raise ValueError("Anthropic returned no tool_use block for proposal")
    payload = tool_block.input
    if isinstance(payload, str):
        payload = json.loads(payload)
    return schema_model.model_validate(payload)


async def _complete(
    db: AsyncSession,
    *,
    system: str,
    user: str,
    schema_model: type[T],
    schema_name: str,
    tool_description: str,
    max_tokens: int = _DEFAULT_MAX_TOKENS,
    timeout_seconds: float = AI_TIMEOUT_SECONDS,
    temperature: float | None = None,
) -> T:
    config = await get_ai_config(db)
    if config.ai_provider == "anthropic":
        if not config.anthropic_api_key:
            raise ValueError("Anthropic API key is not configured")
        return await _complete_anthropic(
            model=config.ai_model,
            api_key=config.anthropic_api_key,
            system=system,
            user=user,
            schema_model=schema_model,
            tool_name=schema_name,
            tool_description=tool_description,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
            temperature=temperature,
        )
    if not config.openai_api_key:
        raise ValueError("OpenAI API key is not configured")
    return await _complete_openai(
        model=config.ai_model,
        api_key=config.openai_api_key,
        system=system,
        user=user,
        schema_model=schema_model,
        schema_name=schema_name,
        max_tokens=max_tokens,
        timeout_seconds=timeout_seconds,
        temperature=temperature,
    )


async def _resolve_purpose(db: AsyncSession, part: Literal["assessment", "proposal", "poc"]) -> GenerationPurpose:
    settings = await get_proposal_ai_settings(db)
    return purpose_for_part(settings, part)


async def generate_assessment(snapshot: dict[str, Any], locale: Locale) -> dict[str, Any] | None:
    try:
        async with SessionLocal() as db:
            purpose = await _resolve_purpose(db, "assessment")
            instructions = await resolve_instructions(
                db,
                "proposal_assessment",
                locale,
                build_base_system=build_assessment_system_prompt,
                system_kwargs={"locale": locale, "purpose": purpose},
                parameter_defaults=budget_parameters(purpose),
            )
            user = merge_user_message(
                instructions.user_prefix,
                build_assessment_user_prompt(snapshot, locale, purpose=purpose),
            )
            max_tokens, timeout_seconds, temperature = _budget_from_parameters(
                instructions.parameters
            )
            model = await _complete(
                db,
                system=instructions.system,
                user=user,
                schema_model=ProposalAssessmentAI,
                schema_name="proposal_assessment",
                tool_description="Produce a stakeholder project assessment.",
                max_tokens=max_tokens,
                timeout_seconds=timeout_seconds,
                temperature=temperature,
            )
        return _assessment_to_storage(model)
    except Exception:
        logger.exception("Proposal assessment AI generation failed")
        return None


async def generate_proposal(
    snapshot: dict[str, Any],
    assessment: dict[str, Any],
    locale: Locale,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]] | None:
    try:
        async with SessionLocal() as db:
            purpose = await _resolve_purpose(db, "proposal")
            instructions = await resolve_instructions(
                db,
                "proposal_body",
                locale,
                build_base_system=build_proposal_system_prompt,
                system_kwargs={"locale": locale, "purpose": purpose},
                parameter_defaults=budget_parameters(purpose),
            )
            user = merge_user_message(
                instructions.user_prefix,
                build_proposal_user_prompt(snapshot, assessment, locale, purpose=purpose),
            )
            max_tokens, timeout_seconds, temperature = _budget_from_parameters(
                instructions.parameters
            )
            model = await _complete(
                db,
                system=instructions.system,
                user=user,
                schema_model=ProposalBodyAI,
                schema_name="proposal_body",
                tool_description=(
                    "Produce a stakeholder project proposal with sections, tables, "
                    "and mermaid diagrams."
                ),
                max_tokens=max_tokens,
                timeout_seconds=timeout_seconds,
                temperature=temperature,
            )
        return _proposal_to_storage(model)
    except Exception:
        logger.exception("Proposal body AI generation failed")
        return None


async def generate_poc(
    snapshot: dict[str, Any],
    assessment: dict[str, Any],
    locale: Locale,
) -> dict[str, Any] | None:
    try:
        async with SessionLocal() as db:
            purpose = await _resolve_purpose(db, "poc")
            instructions = await resolve_instructions(
                db,
                "proposal_poc",
                locale,
                build_base_system=build_poc_system_prompt,
                system_kwargs={"locale": locale, "purpose": purpose},
                parameter_defaults=budget_parameters(purpose),
            )
            user = merge_user_message(
                instructions.user_prefix,
                build_poc_user_prompt(snapshot, assessment, locale, purpose=purpose),
            )
            max_tokens, timeout_seconds, temperature = _budget_from_parameters(
                instructions.parameters
            )
            model = await _complete(
                db,
                system=instructions.system,
                user=user,
                schema_model=ProposalPocAI,
                schema_name="proposal_poc",
                tool_description=(
                    "Produce a Proof of Concept plan with sections, tables, and mermaid diagrams."
                ),
                max_tokens=max_tokens,
                timeout_seconds=timeout_seconds,
                temperature=temperature,
            )
        return _poc_to_storage(model)
    except Exception:
        logger.exception("Proposal POC AI generation failed")
        return None
