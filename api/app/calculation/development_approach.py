from enum import StrEnum


class DevelopmentApproach(StrEnum):
    TRADITIONAL = "traditional"
    AI_ASSISTED = "ai_assisted"
    HYBRID = "hybrid"
    LOW_CODE = "low_code"


class ApproachFactors:
    __slots__ = ("effort_multiplier", "team_size_multiplier", "productivity_multiplier")

    def __init__(
        self,
        *,
        effort_multiplier: float,
        team_size_multiplier: float,
        productivity_multiplier: float,
    ) -> None:
        self.effort_multiplier = effort_multiplier
        self.team_size_multiplier = team_size_multiplier
        self.productivity_multiplier = productivity_multiplier


APPROACH_FACTORS: dict[DevelopmentApproach, ApproachFactors] = {
    DevelopmentApproach.TRADITIONAL: ApproachFactors(
        effort_multiplier=1.0,
        team_size_multiplier=1.0,
        productivity_multiplier=1.0,
    ),
    DevelopmentApproach.AI_ASSISTED: ApproachFactors(
        effort_multiplier=0.75,
        team_size_multiplier=0.85,
        productivity_multiplier=0.75,
    ),
    DevelopmentApproach.HYBRID: ApproachFactors(
        effort_multiplier=0.875,
        team_size_multiplier=0.90,
        productivity_multiplier=0.875,
    ),
    DevelopmentApproach.LOW_CODE: ApproachFactors(
        effort_multiplier=0.55,
        team_size_multiplier=0.70,
        productivity_multiplier=0.55,
    ),
}


def coerce_development_approach(approach: DevelopmentApproach | str) -> DevelopmentApproach:
    if isinstance(approach, DevelopmentApproach):
        return approach
    return DevelopmentApproach(approach)


def get_approach_factors(approach: DevelopmentApproach) -> ApproachFactors:
    return APPROACH_FACTORS[approach]
