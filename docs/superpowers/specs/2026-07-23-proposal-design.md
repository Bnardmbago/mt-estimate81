# Proposal Feature — Design Spec

> **Date:** 2026-07-23  
> **Status:** Approved via brainstorming  
> **Related plan:** `docs/superpowers/plans/2026-07-23-proposal.md`

## 1. Summary

Add a **Proposal** workspace that turns a calculated Estimate into an editable, stakeholder-facing document pack: **Project Assessment**, **Project Proposal**, and optional **Proof of Concept**. Proposal does not re-estimate; it reuses Estimate data and AI analysis for client-readable packaging.

## 2. Product decisions

| Area | Decision |
|------|----------|
| Route | `/{locale}/proposal` |
| Nav | Welcome · Estimates · Proposal · Rate Cards · Admin · Help |
| Access | Full accounts only (`require_full_account`); contact users excluded |
| Cardinality | One active Proposal per `(estimate_id, locale)` |
| UX | Hybrid: tabs jump parts; Export/Print = one continuous pack + master TOC |
| Editing | Section edit before export; autosave; per-section regenerate with warnings |
| Stale source | Soft warning only; manual Refresh; export not blocked |
| Lexicon | Stakeholder language; no bare NRC/RC/POC abbreviations |
| POC pricing | Engine prices selected feature items; AI may add suggested validation window prose |
| Generation | Three sequential jobs: Assessment → Proposal → POC (if included) |
| Exports | PDF, DOCX, Markdown, Excel; variants full / assessment / proposal / poc |
| Eligible estimates | `calculated` \| `exported` \| `completed` |

## 3. Architecture

```text
Estimate (commercial source of truth)
    → source_snapshot + fingerprint
    → AI Job1 Assessment (structured JSON)
    → AI Job2 Proposal + diagrams
    → AI Job3 POC feature IDs (optional) → engine pricing
    → Editable Proposal row
    → ProposalExport artifacts (Jinja/WeasyPrint/DOCX/…)
```

### Aggregate

- **Proposal** — content, snapshot, generation meta, status
- **ProposalExport** — stored export files with revision (estimate Export table not overloaded)

## 4. Content outline

1. Project Assessment — feasibility, readiness, complexity, risks, recommendation, POC recommended?
2. Project Proposal — executive summary, objectives, solution, scope in/out, deliverables, timeline, cost summary, assumptions, risks, next steps
3. Proof of Concept (optional) — why, objectives, in/out, success criteria, effort/timeline/cost (official from engine), suggested validation window (AI prose)

## 5. Status lifecycle

`generating` → `draft` → `ready` → `finalized`

Finalized packs are not silently overwritten; regenerate/refresh after finalize returns the proposal to draft (v1) while prior exports remain as history.

## 6. Non-goals (v1)

- Contact-user proposals
- Multiple proposals per locale
- AI-invented POC money/dates
- Blocking export on stale source
- Full proposal revision table (history via ProposalExport)

## 7. Lexicon examples

| Avoid | Prefer |
|-------|--------|
| NRC | One-time project cost |
| RC | Monthly recurring cost |
| POC | Proof of Concept |
| Gantt | Project timeline |
