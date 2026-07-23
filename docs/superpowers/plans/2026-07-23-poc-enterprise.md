# Enterprise PoC Document Implementation Plan

> **For agentic workers:** Implement task-by-task. Checkbox steps track progress.

**Goal:** Expand Proposal PoC tab into a full enterprise PoC document (editable brief + 17 sections + tables/diagrams) while keeping engine pricing on `scope_in.feature_ids`.

**Architecture:** Extend `proposal.poc` JSON in place. AI/stub fills `project_brief`, sections, tables, diagrams; UI/PDF render them with existing theme tokens. PATCH supports brief fields.

**Tech Stack:** FastAPI/Pydantic, existing proposal AI client, Next.js proposal components, Jinja PDF template.

## Global Constraints

- Do not invent official commercial numbers; use `poc_pricing.price_poc_selection`.
- Locale-aware ja/en; stakeholder lexicon (no bare NRC/RC/POC).
- Theme from `EXPORT_THEME` / `--proposal-*`.
- Missing snapshot data → explicit “Assumption:” wording.
- Lives on Proposal page / Proof of Concept tab only.

---

### Task 1: Schemas + prompts

**Files:** `api/app/proposals/schemas_ai.py`, `api/app/proposals/prompts.py`

- Extend `ProposalPocAI` with `project_brief`, `tables`, `diagrams`, `milestones`.
- Add table/diagram models; section ids list for prompts.
- Rewrite PoC system/user prompts for enterprise structure.

### Task 2: Stub + AI storage + generate + patch

**Files:** `ai_generate.py`, `ai_client.py`, `service.py`, API schemas if any

- `build_project_brief_from_snapshot`, full `stub_poc`.
- `_poc_to_storage` includes brief/tables/diagrams.
- `generate_poc_content` prices via `scope_in` (fallback legacy `in_scope`).
- PATCH brief fields on poc blob.

### Task 3: Export + UI

**Files:** export_context, export_formats, proposal_pack.html.j2, proposal-types, ProposalPageClient, Toc, new brief/table components, i18n

### Task 4: Tests + Docker rebuild
