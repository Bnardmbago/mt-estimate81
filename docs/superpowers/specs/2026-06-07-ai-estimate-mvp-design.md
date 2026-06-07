# AI Driven Estimate System — MVP Design Spec

> **Date:** 2026-06-07  
> **Status:** Approved via brainstorming  
> **Currency:** Japanese Yen (JPY)  
> **Source spec:** `spec.md`, `questionnaire_form.md`

## 1. Summary

Internal web application that helps a small team (≤10 users) generate software project estimates from client requirements. Users input project information via a 21-field form and/or uploaded documents. AI extracts requirements and suggests feature-level effort hours. Users review and edit before a deterministic calculation engine produces NRC, RC, and first-year cost in JPY. Results export to PDF, Excel, and Markdown in Japanese or English.

**Primary goal:** Working internal MVP on an office server, refined over time. No hard deadline — steady progress over rush.

## 2. Requirements Decisions

| Area | Decision |
|------|----------|
| Goal | Internal MVP, refine later |
| Inputs | Form + document upload (both required day one) |
| Users | ≤10, simple auth, one admin for rate cards |
| Language | Bilingual UI + exports (JP/EN toggle) |
| Hosting | Office Docker server now → GCP within ~6 months |
| AI | OpenAI default; Hermes.ai for document extraction; swappable providers (Anthropic, etc.) via config |
| Sizing | Hybrid — AI lists features + suggested hours; user edits; system rolls up to NRC/RC |
| Effort units | Person-hours and person-days (`hours ÷ 8`); no calendar schedule or holidays in MVP |
| Exports | PDF + Excel + Markdown from launch |
| Feedback | Actuals + basic variance (estimate vs actual) in MVP |
| Timeline | No hard deadline |

## 3. Architecture

### 3.1 Approach

**Next.js UI + FastAPI backend** (Approach 2), orchestrated by Docker Compose on the office server.

```text
┌─────────────────────────────────────────────────────────────┐
│  Office Server (Docker Compose)                             │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  Next.js UI  │───▶│  FastAPI API │───▶│  PostgreSQL  │  │
│  │  (port 3000) │    │  (port 8000) │    │              │  │
│  └──────────────┘    └──────┬───────┘    └──────────────┘  │
│                             │                               │
│                    ┌────────┴────────┐                      │
│                    ▼                 ▼                      │
│           ┌──────────────┐  ┌──────────────┐               │
│           │ Hermes Agent │  │ File Storage │               │
│           │  (sidecar)   │  │ (local vol)  │               │
│           └──────────────┘  └──────────────┘               │
└─────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
   Team browsers (LAN)          OpenAI / Anthropic APIs
```

### 3.2 Components

| Component | Responsibility | Tech |
|-----------|----------------|------|
| Web UI | Login, estimate wizard, review/edit, admin, variance reports, language toggle | Next.js 15, React, `next-intl` |
| API | Auth, CRUD, AI orchestration, calculation engine, exports, audit log | FastAPI, SQLAlchemy, Pydantic |
| Database | Users, estimates, requirements, feature items, rate cards, actuals, audit | PostgreSQL 16 |
| File storage | Uploads and generated exports | Local `./data/` (GCS-ready abstraction) |
| Hermes sidecar | Document → markdown text | Hermes Agent, pymupdf, marker-pdf (optional) |
| AI provider layer | Structured extraction + hour suggestions | OpenAI, Anthropic, OpenRouter adapters |
| nginx | LAN reverse proxy | nginx |

### 3.3 FastAPI Modules

| Module | Purpose |
|--------|---------|
| `auth` | Email/password login, JWT sessions, `is_admin` flag |
| `estimates` | Estimate lifecycle CRUD |
| `documents` | Upload, Hermes extraction, store text |
| `ai` | Provider abstraction, locale-aware prompts, JSON validation |
| `calculation` | Pure NRC/RC/effort functions |
| `exports` | PDF, Excel, Markdown generators |
| `admin` | Rate cards, users, system health |
| `feedback` | Actuals entry, variance computation |
| `audit` | Append-only change log |

### 3.4 Auth Model

- Email + password (no SSO in MVP)
- **User:** create/edit estimates, view all estimates
- **Admin:** above + rate card settings, user management
- JWT in httpOnly cookie; Next.js proxies to FastAPI

## 4. User Workflow

### 4.1 Estimate Lifecycle

```text
draft → extracting → review → calculated → exported → completed
```

| State | User action |
|-------|-------------|
| draft | Fill form, upload files, trigger extraction |
| extracting | Wait (progress indicator, poll status) |
| review | Edit requirements, features, hours |
| calculated | View NRC/RC breakdown; recalculate after edits |
| exported | Download PDF / Excel / Markdown |
| completed | Enter actuals; view variance |

Users can return from `calculated` to `review` to edit line items without restarting.

### 4.2 Extraction Pipeline

```text
1. Save form data
2. For each uploaded file → Hermes → markdown text
3. Combine form JSON + document texts
4. AI provider → structured JSON
5. Populate extracted_data + feature_items
6. status → review
```

Target: under 2 minutes for normal documents. UI polls `GET /estimates/{id}/status` every 2 seconds during extraction.

### 4.3 Partial Failure

- If some documents fail, extraction continues with successful files
- Failed files marked `extraction_status: failed`; user can retry individually
- `confidence_notes` records which documents were skipped

## 5. Data Model

### 5.1 Entity Overview

```text
users ──────────────┐
rate_cards ─────────┼──▶ estimates ──▶ estimate_documents
  └── rate_card_    │       ├── form_data (JSONB)
      versions      │       ├── extracted_data (JSONB)
                    │       ├── feature_items
                    │       ├── calculation_result (JSONB)
                    │       ├── exports
                    │       ├── actuals
                    │       └── audit_logs
```

### 5.2 Key Tables

**users:** id, email, password_hash, display_name, is_admin, preferred_locale, created_at

**rate_cards:** id, name, is_active, created_by, created_at

**rate_card_versions:** id, rate_card_id, version_number, settings (JSONB), created_at — immutable snapshots

**estimates:** id, project_name, client_name, status, locale, created_by, rate_card_version_id, form_data, extracted_data, calculation_result, created_at, updated_at

**estimate_documents:** id, estimate_id, original_filename, file_type, storage_path, extracted_text, extraction_status, uploaded_at

**feature_items:** id, estimate_id, sort_order, name, description, hours, phase, role, is_ai_generated, created_at, updated_at

**exports:** id, estimate_id, format, storage_path, locale, generated_at, generated_by

**actuals:** id, estimate_id (unique), actual_effort_hours, actual_duration_days, actual_nrc_jpy, actual_rc_monthly_jpy, variance_notes, entered_by, entered_at

**audit_logs:** id, estimate_id, user_id, action, changes (JSONB), created_at — append-only

### 5.3 Rate Card Settings (JSONB)

```json
{
  "roles": [{ "name": "PM", "hourly_rate_jpy": 8000, "daily_rate_jpy": 64000 }],
  "phases": [{ "name": "development", "percentage": 0.40 }],
  "contingency_rate": 0.15,
  "overhead_rate": 0.10,
  "monthly_rc_items": [{ "name": "hosting", "amount_jpy": 50000 }],
  "setup_costs": { "infrastructure_jpy": 300000, "tooling_jpy": 100000, "third_party_jpy": 0 },
  "productivity": { "hours_per_feature_default": 40 },
  "tax_rate": 0.10
}
```

### 5.4 Form Data Keys

Maps to all 21 fields in `questionnaire_form.md`: project_name, nature_of_work, scope_boundaries, project_overview, system_type, business_domain, main_functional_needs, non_functional_needs, users_and_load, integrations, data_complexity, ui_complexity, technology_preferences, development_approach, rules_and_standards, team_and_resources, development_location, delivery_timing, maintenance_support, risks_unknowns, budget.

### 5.5 AI Output Schema

```json
{
  "functional_requirements": [],
  "non_functional_requirements": [],
  "user_roles": [],
  "modules": [],
  "external_systems": [],
  "risks": [],
  "gaps": [],
  "confidence_notes": "",
  "feature_items": [
    {
      "name": "User login & auth",
      "description": "...",
      "suggested_hours": 40,
      "phase": "development",
      "role": "developer"
    }
  ],
  "maintenance_assumptions": {
    "monthly_support_hours": 20,
    "notes": "..."
  }
}
```

## 6. AI Layer & Hermes

### 6.1 Two-Stage Pipeline

| Stage | Service | Input → Output |
|-------|---------|--------------|
| 1 | Hermes (local) | File → markdown text |
| 2 | AI provider (configurable) | Form + texts → structured JSON |

Raw files never sent to external AI providers — only extracted markdown.

### 6.2 Document Routing

| File type | Method |
|-----------|--------|
| PDF (text) | pymupdf |
| PDF (scanned) | marker-pdf (optional, ~3 GB models) |
| DOCX | python-docx |
| XLSX | openpyxl |
| TXT / MD | Direct read |

Hermes API (internal): `POST /internal/extract` → `{ markdown, page_count, method }`

### 6.3 Provider Abstraction

```python
class AIProvider(Protocol):
    async def extract_requirements(
        form_data: dict,
        document_texts: list[str],
        locale: Literal["ja", "en"],
    ) -> ExtractedRequirements: ...
```

**MVP adapters:** OpenAI, Anthropic, OpenRouter

**Switch via `.env` (no code changes):**

```env
AI_PROVIDER=openai
AI_MODEL=gpt-4o
OPENAI_API_KEY=sk-...
```

### 6.4 Prompt & Validation

- System prompt requests JSON matching schema; output language matches locale
- User prompt: form data + document texts + active rate card roles/phases
- Provider-native JSON mode where available
- Pydantic validation; one auto-retry on failure
- 90-second timeout; max ~80K chars combined document text (truncation noted in confidence_notes)

## 7. Calculation Engine

Pure Python — no AI. Deterministic and unit-testable.

### 7.1 Effort Units

- **Person-hours:** sum of feature item hours
- **Person-days:** `person-hours ÷ 8` (effort unit only)
- **No calendar schedule**, Mon–Fri logic, or holiday exclusion in MVP

### 7.2 Formulas

```text
Phase Hours      = Total Effort Hours × Phase Percentage
Role Cost        = Role Hours × Hourly Rate (JPY)
Labor Cost       = Σ Role Costs
Contingency      = Labor Cost × Contingency Rate
Overhead         = Labor Cost × Overhead Rate
NRC              = Labor + Setup + Contingency + Overhead
Maintenance Cost = Monthly Support Hours × Support Role Hourly Rate
Monthly RC       = Σ Monthly RC Items + Maintenance Cost
Annual RC        = Monthly RC × 12
First Year Cost  = NRC + Annual RC
```

Phase breakdown is informational (management readability). Role hours drive cost.

### 7.3 Rate Card Snapshot

On first calculate, active rate card version is frozen on the estimate. Recalculation uses frozen version unless user explicitly chooses "Recalculate with current rates" (audit logged).

### 7.4 Validation

Calculation blocked if a feature item references a role not in the rate card — error points to the offending line item.

## 8. Exports

All formats generated server-side, locale-aware, stored in file storage.

### 8.1 Report Sections (all formats)

Project summary, input assumptions, extracted requirements, feature line items, effort summary (hours + effort-days), phase breakdown, role breakdown, NRC breakdown, RC breakdown, first-year total, risks/gaps, AI confidence notes, rate card reference.

Currency: `¥X,XXX,XXX`. Dates: `2026年6月7日` (JA) or `June 7, 2026` (EN).

### 8.2 Format Details

| Format | Library | Notes |
|--------|---------|-------|
| PDF | WeasyPrint or ReportLab via Jinja2 HTML | A4, Noto Sans JP bundled |
| Excel | openpyxl | Multi-sheet workbook with auditable formulas |
| Markdown | Jinja2 template | Pipe tables, wiki-friendly |

Stale export badge shown when calculation is newer than last export.

## 9. Admin, Feedback & Variance

### 9.1 Admin Tabs

1. **Rate cards** — edit roles, phases, rates, RC items, setup costs; save creates new immutable version
2. **Users** — create, reset password, toggle admin, set locale
3. **AI settings** — read-only display of provider/model from env; health indicator
4. **System** — storage usage, Hermes/API/DB health, app version

### 9.2 Actuals & Variance

On completion, user enters: actual effort hours, actual effort-days, actual NRC, actual RC monthly, variance notes.

```text
variance_pct = ((actual - estimated) / estimated) × 100
```

Color coding: green ±10%, amber ±10–25%, red beyond ±25%.

Team variance dashboard: table of completed estimates, sortable by variance %, filterable by date/client. No charts in MVP.

## 10. Error Handling

| Scenario | Behavior |
|----------|----------|
| Upload fails | User message; no DB record |
| Hermes fails | File marked failed; others continue; retry available |
| AI timeout | Retry button; partial doc text preserved |
| Invalid AI JSON | Auto-retry once; then user-facing error |
| Unknown role | Calculation blocked with line reference |
| Export fails | Logged; no export record |

API error shape: `{ "error": "...", "code": "AI_TIMEOUT", "details": {} }`

Estimates stuck in `extracting` >10 minutes flagged on admin system tab; idempotent retry clears partial AI output before re-run.

## 11. Testing

| Layer | Scope |
|-------|-------|
| Unit (pytest) | calculation, ai validation, export templates, auth — ≥80% on calculation + ai |
| Integration | Form → mock AI → calculate; upload → mock Hermes; rate card versioning; variance |
| Manual smoke | Both locales, form-only + upload paths, provider switch, all 3 exports, actuals |

External AI and Hermes mocked in CI.

## 12. Deployment

### 12.1 Docker Compose Services

```text
web (3000) | api (8000) | db (5432) | hermes (8080) | nginx (80)
```

Volumes: `postgres_data`, `upload_data`, `export_data`, `hermes_cache` (optional OCR).

### 12.2 Operations

```bash
docker compose up -d
docker compose exec api python -m alembic upgrade head
docker compose exec api python scripts/seed_admin.py
```

Nightly `pg_dump` via host cron.

### 12.3 Resource Requirements

| | Minimum | Recommended |
|--|---------|-------------|
| CPU | 4 cores | 8 cores |
| RAM | 8 GB | 16 GB |
| Disk | 50 GB | 100 GB |

### 12.4 Cloud Migration (GCP ~6 months)

| Component | Now | Later |
|-----------|-----|-------|
| App | Docker Compose | Cloud Run or GCE VM |
| Database | Container | Cloud SQL |
| Storage | Local (`STORAGE_BACKEND=local`) | GCS (`STORAGE_BACKEND=gcs`) |
| Secrets | `.env` | GCP Secret Manager |

No application code changes required — config and infrastructure only.

## 13. Build Phases

| Phase | Deliverable |
|-------|-------------|
| 1. Foundation | Docker Compose, DB schema, auth, UI shell |
| 2. Form & estimates | 21-field form, CRUD, audit log |
| 3. Documents + Hermes | Upload pipeline, text extraction |
| 4. AI extraction | Provider layer, review UI |
| 5. Calculation | Engine, rate card admin |
| 6. Exports | PDF, Excel, Markdown (bilingual) |
| 7. Feedback | Actuals, variance dashboard |
| 8. Polish | i18n, error handling, smoke tests |

## 14. Out of Scope (MVP)

- Calendar-based project duration (Mon–Fri, holidays)
- SSO / complex RBAC
- Function point automation (JFPUG / COSMIC)
- Multi-tenant SaaS billing
- Gantt chart planning
- Editable AI provider settings in admin UI (env-only for MVP)
- Variance charts / analytics dashboards

## 15. Success Criteria

- Generate estimate from form input alone
- Generate estimate from uploaded documents alone
- Generate estimate from form + documents combined
- NRC and RC clearly calculated with explainable breakdown
- Cost assumptions editable via rate cards
- Export to PDF, Excel, and Markdown in JP and EN
- Management can trace how each cost line was calculated
- Capture actuals and show basic estimate vs actual variance
