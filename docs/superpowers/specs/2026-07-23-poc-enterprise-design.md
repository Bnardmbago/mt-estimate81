# Enterprise Proof of Concept Document — Design

**Date:** 2026-07-23  
**Status:** Approved — implementing  
**Parent:** Proposal pack (`docs/superpowers/specs/2026-07-23-proposal-design.md`)

## Goal

Expand the Proposal **Proof of Concept** part into a full enterprise PoC document: project brief + 16 stakeholder sections, with tables and Mermaid diagrams, themed like the rest of the proposal pack. Commercial numbers and selected feature pricing remain estimate-engine bound.

## Decisions (locked)

| Decision | Choice |
|----------|--------|
| Storage | Expand `proposal.poc` JSON in place (Approach 1) |
| Brief source | Derive from estimate snapshot; mark gaps as assumptions |
| Brief editing | Hybrid — AI/stub fills; five brief fields editable in UI |
| Pricing | `official` via `poc_pricing.price_poc_selection`; feature ids from `scope_in` |
| Locale | Same as proposal locale (`ja` / `en`) |
| Theme | Reuse `EXPORT_THEME` / `--proposal-*` CSS variables |

## Project brief

Editable object on `proposal.poc.project_brief`:

| Field | Source when available | If missing |
|-------|----------------------|------------|
| `project_name` | Snapshot `project_name` | Assumption note |
| `project_description` | Modules + functional requirements summary | Assumption note |
| `business_problem` | Risks / gaps / problem signals in extracted data | Assumption note |
| `target_users` | Snapshot `user_roles` / roles | Assumption note |
| `technology_stack` | Modules, feature names, any stack hints | Assumption note |
| `constraints` | Costs, timeline working days, exclusions | Assumption note |

Assumption language must be explicit (e.g. “Assumption: target users were not specified in the estimate; assuming Admin and end users.”).

UI: brief fields edit like section bodies (inline edit → PATCH). Prefer extending section-patch API or a small dedicated brief patch on the same endpoint.

## Required PoC sections (fixed ids, order)

1. `executive_summary` — Executive Summary  
2. `problem_statement` — Problem Statement  
3. `objectives` — Objectives  
4. `scope_in` — Scope / In Scope (holds `feature_ids` for engine pricing)  
5. `scope_out` — Scope / Out of Scope  
6. `success_criteria` — Success Criteria  
7. `assumptions` — Assumptions  
8. `technical_approach` — Technical Approach  
9. `proposed_architecture` — Proposed Architecture (prose + diagram reference)  
10. `technology_stack` — Technology Stack (prose + optional table)  
11. `implementation_plan` — Implementation Plan  
12. `risks_mitigation` — Risks and Mitigation (prose + optional table)  
13. `testing_validation` — Testing & Validation Strategy  
14. `expected_outcomes` — Expected Outcomes  
15. `timeline_milestones` — Timeline & Milestones (prose + optional table / PoC milestones)  
16. `deliverables` — Deliverables  
17. `recommendations` — Recommendations / Next Steps  

Note: User list had “4. Scope” with In/Out nested; we store as two sections for TOC/edit simplicity, labeled as Scope children in TOC if needed.

Legacy short ids (`why_poc`, `in_scope`, …) are replaced. Regenerating a PoC rewrites to the new shape. No migration of old stub PoCs beyond regenerate.

## Rich blocks on PoC blob

```json
{
  "project_brief": { "...": "..." },
  "sections": [ { "id", "title", "body", "bullets?", "feature_ids?", "tables?" } ],
  "diagrams": [ { "id", "title", "engine": "mermaid", "source" } ],
  "tables": [ { "id", "title", "headers": [], "rows": [[]] } ],
  "milestones": [ { "id", "name", "date?" } ],
  "suggested_validation_window": "...",
  "official": { "...engine pricing..." }
}
```

Section-level optional `tables` may also be used for risk/stack matrices; top-level `tables`/`diagrams` are fine for export.

**Illustrations:** Mermaid for architecture / validation flow.  
**Graphs:** Prefer simple Mermaid or table-based timeline; no new charting library required for v1.  
**Tables:** Markdown/HTML table rendering in UI + PDF (theme borders/header fill).

## AI / stub behavior

- Prompts require all section ids, detailed stakeholder prose, feasibility focus (not production readiness), professional headings/bullets, and tables/diagrams where useful.
- Must not invent official hours/costs/dates for `official`; may propose narrative timeline and milestone labels with assumptions.
- `selected_feature_ids` / `scope_in.feature_ids` only from snapshot feature catalog.
- Stub path fills the same structure with shorter but complete sections + one architecture diagram + risk/scope tables so export never looks empty.

## API / UI

- Generation jobs unchanged (Assessment → Proposal → PoC).
- PATCH: allow updating `project_brief` fields and section content; preserve `user_edited` where applicable.
- PoC tab: brief panel (theme chrome) → TOC sections → diagrams/tables → official cost box.
- TOC: include brief anchor + all 16/17 section entries.
- Export (PDF/MD/DOCX/XLSX): render brief, sections, tables, diagrams, official costs with theme tokens.

## Out of scope

- Separate PoC microservice or new top-level route
- Inventing engine commercial figures
- New charting library (Recharts etc.)
- Full redesign of Assessment / Proposal parts
- Auto-migrating historical short PoCs without Regenerate

## Success criteria

1. Regenerated PoC includes brief + full section set in UI and PDF.  
2. Missing snapshot data surfaces as labeled assumptions.  
3. Brief fields editable and persist.  
4. Engine `official` still prices selected `scope_in` features.  
5. Theme colors applied to brief/tables/diagram chrome consistently with proposal pack.
