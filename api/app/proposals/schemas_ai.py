"""Structured AI output schemas for proposal generation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ProposalAISection(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    body: str = ""
    bullets: list[str] = Field(default_factory=list)
    rating: str = ""
    feature_ids: list[str] = Field(default_factory=list)
    drivers: list[str] = Field(default_factory=list)
    poc_recommended: bool = False


class ProposalAssessmentAI(BaseModel):
    sections: list[ProposalAISection]
    poc_recommended: bool = False
    summary_cost_note: str = ""


class ProposalDiagramAI(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    engine: Literal["mermaid"] = "mermaid"
    source: str = Field(min_length=1)


class ProposalMilestoneAI(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    date: str = ""


class ProposalTableAI(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)


class ProposalBodyAI(BaseModel):
    sections: list[ProposalAISection]
    tables: list[ProposalTableAI] = Field(default_factory=list)
    diagrams: list[ProposalDiagramAI] = Field(default_factory=list)
    milestones: list[ProposalMilestoneAI] = Field(default_factory=list)


class ProposalProjectBriefAI(BaseModel):
    project_name: str = ""
    project_description: str = ""
    business_problem: str = ""
    target_users: str = ""
    technology_stack: str = ""
    constraints: str = ""


class ProposalPocAI(BaseModel):
    project_brief: ProposalProjectBriefAI
    sections: list[ProposalAISection]
    tables: list[ProposalTableAI] = Field(default_factory=list)
    diagrams: list[ProposalDiagramAI] = Field(default_factory=list)
    milestones: list[ProposalMilestoneAI] = Field(default_factory=list)
    suggested_validation_window: str = ""
    selected_feature_ids: list[str] = Field(default_factory=list)


class PresentationRecommendAI(BaseModel):
    theme_id: str = Field(min_length=1)
    style_id: str = Field(min_length=1)
    template_id: str = Field(min_length=1)
    rationale: str = ""


POC_SECTION_IDS: list[str] = [
    "executive_summary",
    "problem_statement",
    "objectives",
    "scope_in",
    "scope_out",
    "success_criteria",
    "assumptions",
    "technical_approach",
    "proposed_architecture",
    "technology_stack",
    "implementation_plan",
    "risks_mitigation",
    "testing_validation",
    "expected_outcomes",
    "timeline_milestones",
    "deliverables",
    "recommendations",
]

POC_BRIEF_FIELDS: list[str] = [
    "project_name",
    "project_description",
    "business_problem",
    "target_users",
    "technology_stack",
    "constraints",
]
