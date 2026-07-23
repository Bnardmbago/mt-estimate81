from app.proposals.poc_pricing import price_poc_selection
from app.proposals.export_context import build_proposal_export_context
from app.models.proposal import Proposal
import uuid
from datetime import datetime


def test_poc_pricing_sums_selected_features():
    features = [
        {"id": "a", "name": "AI chat", "hours": 40, "phase": "development", "role": "developer"},
        {"id": "b", "name": "Login", "hours": 8, "phase": "development", "role": "developer"},
    ]
    result = price_poc_selection(
        selected_feature_ids=["a"],
        features=features,
        role_breakdown=[{"role": "developer", "rate_jpy": 10000}],
        gantt={"total_working_days": 50, "project_start_date": "2026-01-01"},
    )
    assert result["total_effort_hours"] == 40
    assert result["estimated_one_time_cost_jpy"] == 400000
    assert "NRC" not in str(result)
    assert "RC" not in str(result)


def test_export_context_uses_stakeholder_lexicon():
    proposal = Proposal(
        id=uuid.uuid4(),
        estimate_id=uuid.uuid4(),
        locale="en",
        include_poc=False,
        status="draft",
        source_snapshot={
            "project_name": "Demo",
            "client_name": "Acme",
            "costs": {
                "one_time_project_cost_jpy": 100,
                "monthly_recurring_cost_jpy": 10,
                "first_year_total_jpy": 220,
            },
            "gantt": {},
        },
        assessment={"sections": [{"id": "feasibility", "title": "Overall feasibility", "body": "ok"}]},
        proposal_body={"sections": [{"id": "executive_summary", "title": "Executive summary", "body": "ok"}]},
        poc=None,
        diagrams=[],
        milestones=[],
        generation_meta={},
        source_fingerprint="x",
        user_id=uuid.uuid4(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    ctx = build_proposal_export_context(proposal, locale="en", variant="full")
    blob = str(ctx)
    assert "NRC" not in blob
    assert "RC" not in blob or "Proof of Concept" in blob  # allow substring in words carefully
    assert ctx["labels"]["one_time"] == "One-time project cost"
    assert "NRC" not in ctx["labels"]["one_time"]
    assert "RC" not in ctx["labels"]["monthly"]
