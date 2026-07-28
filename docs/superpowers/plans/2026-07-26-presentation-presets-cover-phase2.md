# Presentation Presets & Cover Design — Phase 2 Implementation Plan (Estimates)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the same `PresentationBundle` resolver, Cover model, and Theme/Style/Template selectors into Estimate preview/export (report, quotation, dossier, spreadsheet) without creating an Estimate-only presentation model.

**Architecture:** Reuse Phase 1 catalogs, cover fields/values, and resolver. Add Estimate persistence columns and inject the resolved bundle into existing estimate export contexts/templates.

**Tech Stack:** Same as Phase 1; Estimate export stack under `api/app/exports/*` and `web/components/ExportPanel.tsx`.

## Global Constraints

- Same as Phase 1 plan/spec.
- Do **not** redesign Admin / Presentation.
- Do **not** duplicate Theme/Style/Template catalogs.
- Paper size default remains A4.
- Explicit EN/JA export locale already exists on Estimate `ExportPanel`; extend it with presentation selectors + cover controls.
- Do not commit unless the user explicitly asks.

**Prerequisite:** Phase 1 complete and Proposal cover/export tests green.

---

### Task 1: Estimate presentation columns + schemas

**Files:**
- Create: `api/alembic/versions/040_estimate_presentation.py`
- Modify: `api/app/models/estimate.py`
- Modify: `api/app/schemas/export.py` (or estimate export schema location)
- Modify: `api/app/schemas/estimate.py` if needed
- Test: `api/tests/unit/test_estimate_presentation_schema.py`

- [ ] **Step 1: Write failing tests for Estimate theme/style/template/cover_values fields**

- [ ] **Step 2: Add migration revising Phase 1 head (`039_...`)**

Columns on `estimates` (and export rows if audit needed):
- `theme_id`, `style_id`, `template_id` nullable strings
- `cover_values` JSONB default `{}`

- [ ] **Step 3: Run tests PASS**

---

### Task 2: Inject PresentationBundle into Estimate export contexts

**Files:**
- Modify: `api/app/exports/service.py`
- Modify: `api/app/exports/report_context.py`
- Modify: `api/app/exports/quotation_context.py`
- Modify: `api/app/exports/internal_dossier.py`
- Modify: `api/app/exports/excel.py`
- Modify: `api/app/exports/docx.py`
- Modify: templates under `api/app/exports/templates/estimate*.html.j2`, `estimate.md.j2`
- Test: `api/tests/unit/test_export_pdf.py`, `test_export_docx.py`, `test_export_excel.py`

- [ ] **Step 1: Write tests proving non-default Theme colors and A4 landscape cover appear in Estimate PDF path**

- [ ] **Step 2: Resolve presentation in export service and pass into contexts**

- [ ] **Step 3: Update templates for cover regions + CSS vars; MD/XLSX best-effort**

- [ ] **Step 4: Run targeted export tests PASS**

---

### Task 3: Estimate UI presentation + cover controls

**Files:**
- Modify: `web/components/ExportPanel.tsx`
- Modify: `web/components/internal/InternalExportPanel.tsx`
- Modify: `web/components/EstimateExtraction.tsx` if needed for state
- Modify: `web/lib/estimate.ts`
- Modify: `web/lib/estimate-types.ts`
- Reuse: `web/components/proposal/PresentationSelectors.tsx` or extract shared selector
- Reuse: cover field components from Phase 1 where practical
- Modify: `web/messages/en.json`, `web/messages/ja.json`

- [ ] **Step 1: Extend export request types/API helpers**

- [ ] **Step 2: Add Theme/Style/Template selectors, cover values, include-cover toggle to Estimate export panels**

Keep existing export locale selector; default remains header/document locale.

- [ ] **Step 3: `cd web && npm run build`** Expected: PASS

---

### Task 4: Phase 2 verification

- [ ] **Step 1: API verification**

```bash
cd api && pytest tests/unit/test_export_pdf.py tests/unit/test_export_docx.py \
  tests/unit/test_export_excel.py tests/integration/test_estimate_export_internal.py -v
```

- [ ] **Step 2: Web build**

```bash
cd web && npm run build
```

- [ ] **Step 3: Confirm Estimate export still works without presentation IDs (defaults)**

---

## Spec coverage checklist

| Spec requirement | Task |
|------------------|------|
| Estimates consume same presets | 1–3 |
| Same resolver, no duplicate model | 2 |
| Cover + page setup in Estimate exports | 2–3 |
| Export locale selector retained | 3 |
