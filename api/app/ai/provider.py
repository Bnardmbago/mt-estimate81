from typing import Any, Literal, Protocol

from app.ai.instruction_resolver import ResolvedInstructions
from app.estimates.extraction_constraints import ExtractionConstraints
from app.ai.schemas import (
    EstimateFormFieldsSuggestion,
    ExtractedRequirements,
    GeneratedRateCardSuggestion,
    RateCardLineItemsSectionSuggestion,
    RateCardPhasesSectionSuggestion,
    RateCardRolesSectionSuggestion,
)
from app.schemas.rate_card import RateCardAiSection


class AIProvider(Protocol):
    async def extract_requirements(
        self,
        form_data: dict[str, Any],
        document_texts: list[str],
        locale: Literal["ja", "en"],
        *,
        rate_card_roles: list[dict[str, Any]] | None = None,
        instructions: ResolvedInstructions | None = None,
        client_constraints: ExtractionConstraints | None = None,
    ) -> ExtractedRequirements: ...

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
    ) -> GeneratedRateCardSuggestion: ...

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
    ) -> (
        RateCardRolesSectionSuggestion
        | RateCardPhasesSectionSuggestion
        | RateCardLineItemsSectionSuggestion
    ): ...

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
    ) -> EstimateFormFieldsSuggestion: ...
