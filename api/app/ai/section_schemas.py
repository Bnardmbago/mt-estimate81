from typing import Literal, Type

from pydantic import BaseModel

from app.ai.schemas import (
    RateCardLineItemsSectionSuggestion,
    RateCardPhasesSectionSuggestion,
    RateCardRolesSectionSuggestion,
)

RateCardAiSection = Literal["roles", "phases", "setup_cost_items", "monthly_rc_items"]


def section_suggestion_model(section: RateCardAiSection) -> Type[BaseModel]:
    if section == "roles":
        return RateCardRolesSectionSuggestion
    if section == "phases":
        return RateCardPhasesSectionSuggestion
    return RateCardLineItemsSectionSuggestion


def section_tool_name(section: RateCardAiSection) -> str:
    return f"suggest_rate_card_{section}"
