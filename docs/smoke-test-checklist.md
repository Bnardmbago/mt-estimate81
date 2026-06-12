# Manual Smoke Test Checklist

Run before each release or after major changes. Requires a running stack (`docker compose up`) with migrations applied and admin seeded.

**Tester:** _______________ **Date:** _______________ **Build/SHA:** _______________

## Prerequisites

- [ ] `docker compose up -d` — all services healthy (web, api, db, hermes, nginx)
- [ ] `docker compose exec api python -m alembic upgrade head` completed
- [ ] `docker compose exec api python scripts/seed_admin.py` completed
- [ ] `.env` has valid `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` for extraction tests

---

## 1. Authentication

- [ ] Login as `admin@example.com` / `admin123` succeeds
- [ ] Invalid credentials show an error message
- [ ] Logout works; protected routes redirect to login

---

## 2. Locales (JP / EN)

- [ ] Switch UI to Japanese — labels and navigation render in Japanese
- [ ] Switch UI to English — labels and navigation render in English
- [ ] Create an estimate in each locale; locale persists on reload

---

## 3. Form-Only Estimate Path

- [ ] Create new estimate (form only, no uploads)
- [ ] Fill all 21 form fields; save and reload — data persists
- [ ] Trigger AI extraction; status moves to `extracting` then `review`
- [ ] Review extracted features; edit hours/roles as needed
- [ ] Run calculation; NRC, RC, and first-year totals display
- [ ] Calculation breakdown is explainable (phase, role, contingency, overhead)

---

## 4. Upload-Only Estimate Path

- [ ] Create new estimate with document upload only (no form data beyond title)
- [ ] Upload at least one supported file (PDF, DOCX, XLSX, TXT, or MD)
- [ ] Hermes extraction completes; document text visible
- [ ] Trigger AI extraction from uploaded text; review screen populates
- [ ] Calculate and verify totals

---

## 5. Combined Form + Upload Path

- [ ] Create estimate with both form fields and uploaded documents
- [ ] AI extraction merges form data and document text
- [ ] Review, calculate, and verify results

---

## 6. AI Provider Switch

- [ ] With `AI_PROVIDER=openai` — extraction completes successfully
- [ ] Stop API, set `AI_PROVIDER=anthropic` and `ANTHROPIC_API_KEY`, restart API
- [ ] Extraction completes successfully with Anthropic provider
- [ ] Admin → AI settings tab shows correct provider/model (read-only)

---

## 7. Exports (all 3 formats × both locales)

For one calculated estimate, generate each export in **Japanese** and **English**:

| Format | JA | EN | File downloads | Content matches calculation |
|--------|----|----|----------------|----------------------------|
| PDF | [ ] | [ ] | [ ] | [ ] |
| Excel | [ ] | [ ] | [ ] | [ ] |
| Markdown | [ ] | [ ] | [ ] | [ ] |

- [ ] PDF page 1 shows Project Summary + Executive Cost Summary (NRC, RC, first-year total, confidence)
- [ ] Excel workbook has Executive, Features, Phase, Role, NRC, RC, Assumptions, and Risks & Reference sheets
- [ ] Markdown export includes all 17 report sections in executive-first order

- [ ] Stale export badge appears when estimate is recalculated after export

---

## 8. Actuals & Variance

- [ ] Mark a calculated estimate as completed
- [ ] Enter actual effort hours, NRC, and monthly RC
- [ ] Variance percentages compute correctly (green ±10%, amber ±10–25%, red >±25%)
- [ ] KPI dashboard shows live cards, pipeline chart, accuracy trend, and variance drill-down; auto-refresh works

---

## 9. Admin

- [ ] Rate cards — view active card, save new version, version history increments
- [ ] Users — create user, reset password, toggle admin flag
- [ ] System — storage usage, service health indicators, stuck extraction flag (>10 min)

---

## 10. Error Handling (spot checks)

- [ ] Upload unsupported file type — clear error, no orphan DB record
- [ ] AI timeout or invalid JSON — retry button or user-facing error shown
- [ ] Calculation with unknown role on a feature line — blocked with line reference

---

## Sign-off

| Result | Notes |
|--------|-------|
| [ ] PASS — all items checked | |
| [ ] FAIL — blockers listed below | |

**Blockers / issues:**

```
(attach issue links or descriptions)
```
