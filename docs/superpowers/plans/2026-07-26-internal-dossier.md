# Internal Dossier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an admin-only estimate internal dossier page (full estimate + rate card + proposals) with an Export UX identical to estimate/proposal exports (`pdf_internal` / `docx_internal` / `xlsx_internal` / `md_internal`).

**Architecture:** Compose a live dossier from existing estimate, frozen rate card version, and linked proposals (no new dossier table). Extend the estimate export pipeline with four `*_internal` format codes that generate full-disclosure artifacts with INTERNAL labeling. Gate generate/list/download/delete/email/send-to for those formats to admins. Frontend: `/{locale}/estimates/[id]/internal` with tabs + an `InternalExportPanel` modeled on `ExportPanel`.

**Tech Stack:** FastAPI, SQLAlchemy async, Pydantic, WeasyPrint/Jinja2, python-docx, openpyxl, Next.js App Router, next-intl.

## Global Constraints

- Admins only (web + API) for dossier and all `*_internal` export operations
- Client quotation/report formats and non-admin ExportPanel unchanged
- Internal export formats: `pdf_internal`, `docx_internal`, `xlsx_internal`, `md_internal` only (no quotation variants)
- Every internal artifact labeled INTERNAL / DO NOT DISTRIBUTE
- Prefer internal export history only on the internal dossier page (exclude `*_internal` from default estimate export list)
- No editing on the dossier page
- Spec: `docs/superpowers/specs/2026-07-26-internal-dossier-design.md`

## File map

| File | Responsibility |
|------|----------------|
| `api/app/models/estimate.py` | Add `ExportFormat` enum members for `*_internal` |
| `api/app/schemas/export.py` | Allow `*_internal` in `ExportRequest.format` |
| `api/app/schemas/internal_dossier.py` | Response schema for `GET .../internal-dossier` |
| `api/app/exports/internal_formats.py` | `INTERNAL_FORMATS`, `is_internal_format()`, admin gate helper |
| `api/app/exports/internal_dossier.py` | Compose dossier context; generate MD/PDF/DOCX/XLSX bytes |
| `api/app/exports/templates/estimate_internal_dossier.html.j2` | Internal PDF HTML |
| `api/app/exports/service.py` | Wire formats, admin gates, list filter |
| `api/app/exports/pdf.py` | Optional watermark_text override for internal |
| `api/app/destinations/mime.py` | Map `docx_internal` / `xlsx_internal` / `pdf_internal` |
| `api/app/estimates/router.py` | `GET /{estimate_id}/internal-dossier` |
| `api/tests/unit/test_internal_dossier.py` | Context + generators |
| `api/tests/unit/test_export_destinations.py` | MIME for internal formats |
| `api/tests/integration/test_internal_dossier.py` | Admin/non-admin API |
| `web/app/[locale]/estimates/[id]/internal/page.tsx` | Admin-gated page |
| `web/components/internal/InternalDossierClient.tsx` | Tabs + header |
| `web/components/internal/InternalExportPanel.tsx` | Export UX |
| `web/lib/internal-dossier.ts` | API helpers + types |
| `web/lib/export-destinations.ts` | Treat `*_internal` like sibling formats |
| `web/components/ExportPanel.tsx` | Hide `*_internal` rows if any leak through |
| `web/components/EstimateDetailContent.tsx` (or extraction header) | Admin link to dossier |
| `web/messages/en.json`, `web/messages/ja.json` | i18n |

---

### Task 1: Internal format constants + enum + request schema

**Files:**
- Create: `api/app/exports/internal_formats.py`
- Modify: `api/app/models/estimate.py` (`ExportFormat`)
- Modify: `api/app/schemas/export.py` (`ExportRequest.format` pattern)
- Test: `api/tests/unit/test_internal_formats.py`

**Interfaces:**
- Produces:
  - `INTERNAL_FORMATS: frozenset[str]`
  - `def is_internal_format(fmt: str) -> bool`
  - `def require_admin_for_internal_format(fmt: str, user: User) -> None` — raises `AppError` 403 `INTERNAL_EXPORT_ADMIN_REQUIRED` if `is_internal_format(fmt)` and not `user.is_admin`
  - `ExportFormat.PDF_INTERNAL = "pdf_internal"` (and DOCX/XLSX/MD)

- [ ] **Step 1: Write failing unit test**

```python
# api/tests/unit/test_internal_formats.py
from app.exports.internal_formats import (
    INTERNAL_FORMATS,
    is_internal_format,
    require_admin_for_internal_format,
)
from app.exceptions import AppError
from app.models.user import User
import pytest
import uuid


def test_internal_formats_set():
    assert INTERNAL_FORMATS == {
        "pdf_internal",
        "docx_internal",
        "xlsx_internal",
        "md_internal",
    }


def test_is_internal_format():
    assert is_internal_format("pdf_internal")
    assert not is_internal_format("pdf")
    assert not is_internal_format("pdf_quotation")


def test_require_admin_blocks_non_admin():
    user = User(
        id=uuid.uuid4(),
        email="u@example.com",
        hashed_password="x",
        display_name="U",
        is_admin=False,
    )
    with pytest.raises(AppError) as exc:
        require_admin_for_internal_format("pdf_internal", user)
    assert exc.value.status_code == 403
    assert exc.value.code == "INTERNAL_EXPORT_ADMIN_REQUIRED"


def test_require_admin_allows_admin():
    user = User(
        id=uuid.uuid4(),
        email="a@example.com",
        hashed_password="x",
        display_name="A",
        is_admin=True,
    )
    require_admin_for_internal_format("pdf_internal", user)
```

- [ ] **Step 2: Run test — expect import/fail**

```bash
cd api && python -m pytest tests/unit/test_internal_formats.py -v
```

Expected: FAIL (module missing)

- [ ] **Step 3: Implement**

```python
# api/app/exports/internal_formats.py
from app.exceptions import AppError
from app.models.user import User

INTERNAL_FORMATS = frozenset(
    {
        "pdf_internal",
        "docx_internal",
        "xlsx_internal",
        "md_internal",
    }
)


def is_internal_format(fmt: str) -> bool:
    return fmt in INTERNAL_FORMATS


def require_admin_for_internal_format(fmt: str, user: User) -> None:
    if is_internal_format(fmt) and not user.is_admin:
        raise AppError(
            "Internal exports are restricted to administrators",
            "INTERNAL_EXPORT_ADMIN_REQUIRED",
            status_code=403,
        )
```

Add to `ExportFormat` in `api/app/models/estimate.py`:

```python
PDF_INTERNAL = "pdf_internal"
DOCX_INTERNAL = "docx_internal"
XLSX_INTERNAL = "xlsx_internal"
MD_INTERNAL = "md_internal"
```

Update `ExportRequest.format` pattern in `api/app/schemas/export.py` to:

```python
pattern=r"^(md|xlsx|pdf|pdf_quotation|docx|docx_quotation|pdf_internal|docx_internal|xlsx_internal|md_internal)$"
```

- [ ] **Step 4: Re-run tests — expect PASS**

```bash
cd api && python -m pytest tests/unit/test_internal_formats.py -v
```

- [ ] **Step 5: Commit**

```bash
git add api/app/exports/internal_formats.py api/app/models/estimate.py api/app/schemas/export.py api/tests/unit/test_internal_formats.py
git commit -m "Add internal export format constants and admin gate helper."
```

---

### Task 2: Dossier context builder + schema

**Files:**
- Create: `api/app/schemas/internal_dossier.py`
- Create: `api/app/exports/internal_dossier.py` (context builder only in this task)
- Test: `api/tests/unit/test_internal_dossier.py`

**Interfaces:**
- Consumes: `build_report_context`, `Estimate`, `RateCardVersion.settings`, `Proposal` rows
- Produces:
  - `async def build_internal_dossier_payload(db, estimate, *, locale: str) -> dict` used by API
  - `def build_internal_export_context(report_context, rate_card_block, proposals_block, *, locale) -> dict` used by generators
  - Pydantic: `InternalDossierResponse` with fields: `estimate_id`, `project_name`, `client_name`, `status`, `locale`, `has_calculation`, `rate_card_stale` (bool), `warnings` (list[str]), `report` (dict), `rate_card` (nullable object), `proposals` (list)

Rate card block shape:

```python
{
  "rate_card_id": str | None,
  "name": str | None,
  "version_number": int | None,
  "effective_date": str | None,  # ISO or None
  "settings": dict,  # full frozen settings
}
```

Proposal list item shape:

```python
{
  "id": str,
  "locale": str,
  "status": str,
  "include_poc": bool,
  "assessment": dict | None,
  "proposal_body": dict | None,
  "poc": dict | None,
}
```

- [ ] **Step 1: Write failing unit test for context**

```python
# api/tests/unit/test_internal_dossier.py
from app.exports.internal_dossier import build_internal_export_context


def test_export_context_includes_rate_card_and_proposal_markers():
    report = {"project_summary": {"project_name": "P"}, "extracted": {"cost_drivers": [{"name": "x"}]}}
    rate_card = {
        "name": "RC",
        "version_number": 2,
        "settings": {"roles": [{"name": "Engineer", "hourly_rate": 10000}]},
    }
    proposals = [{"locale": "en", "status": "draft", "assessment": {"sections": []}, "proposal_body": None, "poc": None}]
    ctx = build_internal_export_context(report, rate_card, proposals, locale="en")
    assert ctx["internal_banner"] == "INTERNAL — DO NOT DISTRIBUTE"
    assert ctx["rate_card"]["settings"]["roles"][0]["name"] == "Engineer"
    assert ctx["proposals"][0]["locale"] == "en"
    assert "cost_drivers" in ctx["report"]["extracted"]


def test_export_context_marks_missing_proposal():
    ctx = build_internal_export_context({"project_summary": {}}, None, [], locale="en")
    assert ctx["proposals_status"] == "none"
```

- [ ] **Step 2: Run — expect fail**

```bash
cd api && python -m pytest tests/unit/test_internal_dossier.py::test_export_context_includes_rate_card_and_proposal_markers -v
```

- [ ] **Step 3: Implement builder + schema**

In `api/app/exports/internal_dossier.py`:

```python
from __future__ import annotations
from typing import Any


INTERNAL_BANNER = "INTERNAL — DO NOT DISTRIBUTE"


def build_internal_export_context(
    report: dict[str, Any],
    rate_card: dict[str, Any] | None,
    proposals: list[dict[str, Any]],
    *,
    locale: str,
) -> dict[str, Any]:
    return {
        "locale": locale,
        "internal_banner": INTERNAL_BANNER,
        "report": report,
        "rate_card": rate_card,
        "proposals": proposals,
        "proposals_status": "none" if not proposals else "present",
    }
```

Add `build_internal_dossier_payload` that:
1. Calls `build_report_context(...)` when `estimate.calculation_result` exists; else `report={}` and warning
2. Loads `RateCardVersion` by `estimate.rate_card_version_id` for full `settings`
3. Selects `Proposal` where `estimate_id == estimate.id`
4. Returns dict matching `InternalDossierResponse`

Define `InternalDossierResponse` in `api/app/schemas/internal_dossier.py` with the fields above.

Also add async helper used by exports:

```python
async def load_internal_export_parts(db, estimate, locale: str) -> dict:
    """Return build_internal_export_context(...) ready for generators."""
```

- [ ] **Step 4: Tests PASS**

```bash
cd api && python -m pytest tests/unit/test_internal_dossier.py -v
```

- [ ] **Step 5: Commit**

```bash
git add api/app/exports/internal_dossier.py api/app/schemas/internal_dossier.py api/tests/unit/test_internal_dossier.py
git commit -m "Add internal dossier context builder and response schema."
```

---

### Task 3: `GET /estimates/{id}/internal-dossier` (admin-only)

**Files:**
- Modify: `api/app/estimates/router.py`
- Modify: service wiring (either `api/app/exports/internal_dossier.py` or thin `api/app/estimates/internal_dossier_service.py`)
- Test: `api/tests/integration/test_internal_dossier.py`

**Interfaces:**
- Consumes: `require_admin`, `get_estimate_for_user`, `build_internal_dossier_payload`
- Produces: `GET /estimates/{estimate_id}/internal-dossier` → `InternalDossierResponse`

- [ ] **Step 1: Write failing integration tests**

```python
# api/tests/integration/test_internal_dossier.py
import pytest


@pytest.mark.asyncio
async def test_internal_dossier_forbidden_for_non_admin(
    client, full_user_headers, calculated_estimate_id
):
    r = await client.get(
        f"/estimates/{calculated_estimate_id}/internal-dossier",
        headers=full_user_headers,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_internal_dossier_ok_for_admin(
    client, admin_headers, calculated_estimate_id
):
    r = await client.get(
        f"/estimates/{calculated_estimate_id}/internal-dossier",
        headers=admin_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["estimate_id"] == str(calculated_estimate_id)
    assert "report" in data
    assert "rate_card" in data
    assert "proposals" in data
```

Use the repo’s existing fixtures/helpers for admin vs full user and a calculated estimate (mirror patterns in `api/tests/integration/test_proposals.py` / export tests). Rename fixtures to match what exists if names differ.

- [ ] **Step 2: Run — expect 404 or fail**

```bash
cd api && python -m pytest tests/integration/test_internal_dossier.py -v
```

- [ ] **Step 3: Add route**

```python
# in api/app/estimates/router.py
from app.dependencies import require_admin
from app.schemas.internal_dossier import InternalDossierResponse
from app.exports import internal_dossier as dossier_service

@router.get("/{estimate_id}/internal-dossier", response_model=InternalDossierResponse)
async def get_internal_dossier(
    estimate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return await dossier_service.get_internal_dossier(db, estimate_id, admin)
```

`get_internal_dossier` loads estimate via `get_estimate_for_user`, then `build_internal_dossier_payload`.

- [ ] **Step 4: Tests PASS**

- [ ] **Step 5: Commit**

```bash
git commit -m "Add admin-only GET internal-dossier endpoint."
```

---

### Task 4: Internal artifact generators (MD + PDF first)

**Files:**
- Modify: `api/app/exports/internal_dossier.py` (add `generate_internal_markdown`, `generate_internal_pdf`)
- Create: `api/app/exports/templates/estimate_internal_dossier.html.j2`
- Modify: `api/app/exports/pdf.py` — allow `watermark_text` override on `_render_template` / add `generate_internal_dossier_pdf`
- Test: extend `api/tests/unit/test_internal_dossier.py`

**Interfaces:**
- Produces:
  - `generate_internal_markdown(ctx: dict) -> str`
  - `generate_internal_pdf(ctx: dict) -> bytes`
- PDF must start with `%PDF` and contain banner text when extracted (or HTML source check via `_build_template_html`)

- [ ] **Step 1: Failing tests**

```python
def test_internal_markdown_contains_banner_and_rate_card():
    ctx = build_internal_export_context(
        {"project_summary": {"project_name": "Alpha"}},
        {"name": "RC1", "settings": {"roles": [{"name": "PM", "hourly_rate": 1}]}},
        [],
        locale="en",
    )
    md = generate_internal_markdown(ctx)
    assert "INTERNAL — DO NOT DISTRIBUTE" in md
    assert "Alpha" in md
    assert "PM" in md
    assert "none" in md.lower() or "No proposal" in md


def test_internal_pdf_is_pdf_and_html_has_banner():
    from app.exports.pdf import build_internal_dossier_html  # or internal helper
    ctx = build_internal_export_context(
        {"project_summary": {"project_name": "Alpha"}, "labels": {}, "extracted": {}},
        {"name": "RC1", "settings": {"roles": []}},
        [],
        locale="en",
    )
    html = build_internal_dossier_html(ctx)
    assert "INTERNAL — DO NOT DISTRIBUTE" in html
    pdf = generate_internal_pdf(ctx)
    assert pdf.startswith(b"%PDF")
```

- [ ] **Step 2: Implement**

Markdown: concatenate report markdown (reuse `generate_markdown(report)` if possible) + rate card tables + proposal section dumps + banner at top.

PDF template: new Jinja2 file that:
1. Shows banner / watermark
2. Embeds key report sections (can `{% include %}` shared partials or inline critical blocks from `estimate_report.html.j2` patterns)
3. Rate card appendix (roles, NRC, RC items from `settings`)
4. Proposal appendix (assessment / proposal_body / poc JSON-ish readable sections, or “none”)

```python
# api/app/exports/pdf.py — extend _build_template_html
def _build_template_html(..., watermark_text: str | None = None, ...):
    return template.render(
        show_watermark=show_watermark,
        watermark_text=watermark_text or CONTACT_EXPORT_WATERMARK_TEXT,
        ...
    )


def generate_internal_dossier_pdf(ctx: dict[str, Any]) -> bytes:
    return _render_template(
        "estimate_internal_dossier.html.j2",
        show_watermark=True,
        watermark_text="INTERNAL — DO NOT DISTRIBUTE",
        ctx=ctx,
        format_currency=format_currency,
        ...
    )
```

- [ ] **Step 3: Tests PASS**

- [ ] **Step 4: Commit**

```bash
git commit -m "Add internal dossier Markdown and PDF generators."
```

---

### Task 5: Internal DOCX + XLSX generators

**Files:**
- Modify: `api/app/exports/internal_dossier.py`
- Optionally thin wrappers in `docx.py` / `excel.py`
- Test: `api/tests/unit/test_internal_dossier.py`

**Interfaces:**
- Produces: `generate_internal_docx(ctx) -> bytes`, `generate_internal_xlsx(ctx) -> bytes`

- [ ] **Step 1: Failing tests** — assert DOCX is zip (`PK`), XLSX is zip; banner or rate card role string appears in document XML / workbook shared strings (same approach as existing `test_export_docx.py` / `test_export_excel.py`).

- [ ] **Step 2: Implement** — start from `generate_report_docx` / `generate_excel`, then append rate card + proposal sections and a leading INTERNAL paragraph / sheet note. Prefer calling existing generators on `ctx["report"]` then appending, to avoid duplicating all report logic.

- [ ] **Step 3: Tests PASS + commit**

```bash
git commit -m "Add internal dossier DOCX and XLSX generators."
```

---

### Task 6: Wire `*_internal` into `export_estimate` + destination MIME

**Files:**
- Modify: `api/app/exports/service.py` — `FORMAT_EXTENSIONS`, `CONTENT_TYPES`, generation branch, `require_admin_for_internal_format` at start of `export_estimate`
- Modify: `api/app/destinations/mime.py` — include `docx_internal`, `xlsx_internal`, `pdf_internal` in format sets
- Modify: `web/lib/export-destinations.ts` — `isDocxFormat` / `isXlsxFormat` include internal variants (PDF already matches `pdf_`)
- Test: unit destination tests + integration export admin gate

**Interfaces:**
- Consumes: `load_internal_export_parts`, generators from Task 4–5
- On `export_estimate`: if `is_internal_format(export_format)` → `require_admin_for_internal_format`; build internal ctx; dispatch generator; always `show_watermark=True` for PDF internal

- [ ] **Step 1: Failing tests**

```python
def test_docx_internal_maps_to_google_docs():
    assert google_source_mime_for_format("docx_internal") == DOCX_SOURCE_MIME


@pytest.mark.asyncio
async def test_non_admin_cannot_create_pdf_internal(client, full_user_headers, calculated_estimate_id):
    r = await client.post(
        f"/estimates/{calculated_estimate_id}/export",
        headers=full_user_headers,
        json={"format": "pdf_internal", "locale": "en"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_create_pdf_internal(client, admin_headers, calculated_estimate_id):
    r = await client.post(
        f"/estimates/{calculated_estimate_id}/export",
        headers=admin_headers,
        json={"format": "pdf_internal", "locale": "en"},
    )
    assert r.status_code == 201
    assert r.json()["format"] == "pdf_internal"
```

- [ ] **Step 2: Implement service wiring**

In `FORMAT_EXTENSIONS` / `CONTENT_TYPES` add the four internal formats (same extensions/MIME as non-internal siblings).

In `_generate_export_bytes` (or equivalent), add branches for internal formats calling `generate_internal_*`.

Filename suffix in `download_export`: use `-internal` for `is_internal_format`.

- [ ] **Step 3: Tests PASS + commit**

```bash
git commit -m "Wire internal export formats into estimate export and destinations."
```

---

### Task 7: Admin gates on download/delete/email/send-to + list filter

**Files:**
- Modify: `api/app/exports/service.py` — `list_exports`, `download_export`, `delete_export`, `send_exports_email`
- Modify: `api/app/destinations/service.py` — if estimate send-to loads export, call `require_admin_for_internal_format`
- Modify: `api/app/exports/router.py` — optional query `audience=internal` on list endpoint
- Test: integration tests

**Interfaces:**
- `list_exports(..., *, audience: str | None = None)`  
  - default / `audience=client`: exclude rows where `is_internal_format(format)`  
  - `audience=internal`: require admin; return only internal formats
- `download_export` / `delete_export` / email / send-to: if record format is internal → `require_admin_for_internal_format`

- [ ] **Step 1: Failing tests** — non-admin download of an admin-created `pdf_internal` → 403; admin list `?audience=internal` returns only internal; default list excludes internal.

- [ ] **Step 2: Implement + PASS + commit**

```bash
git commit -m "Restrict internal export download and list to admins."
```

---

### Task 8: Frontend internal dossier page + entry link

**Files:**
- Create: `web/app/[locale]/estimates/[id]/internal/page.tsx`
- Create: `web/lib/internal-dossier.ts`
- Modify: `web/components/EstimateDetailContent.tsx` (or visible admin chrome on estimate page) — link when `profile.is_admin`
- Modify: `web/messages/en.json`, `web/messages/ja.json` — `internalDossier.*` keys

**Interfaces:**
- Page: cookie auth → `GET /auth/me` → if not `is_admin` redirect to `/{locale}/estimates/{id}`; else render client
- `fetchInternalDossier(estimateId): Promise<InternalDossier>`

- [ ] **Step 1: Add i18n keys** (`title`, `banner`, `backToEstimate`, `tabEstimate`, `tabRateCard`, `tabProposal`, `openLink`, warnings, empty proposal, export section labels mirroring `export.*` where useful)

- [ ] **Step 2: Create page** (mirror `admin/page.tsx` 403 redirect pattern using `/auth/me` `is_admin` or a probe to `/internal-dossier`)

```tsx
// web/app/[locale]/estimates/[id]/internal/page.tsx
// force-dynamic; require token; if !profile.is_admin redirect to estimate; render <InternalDossierClient estimateId={id} />
```

- [ ] **Step 3: Add admin-only link** on estimate detail header area:

```tsx
{isAdmin ? (
  <Link href={`/${locale}/estimates/${estimate.id}/internal`}>
    {t("internalDossier.openLink")}
  </Link>
) : null}
```

Pass `isAdmin` from page via `/auth/me` into `EstimateDetailContent` (add prop; do not infer from contact alone).

- [ ] **Step 4: Smoke — commit**

```bash
git commit -m "Add admin internal dossier page route and estimate entry link."
```

---

### Task 9: Dossier tabs UI (live browse)

**Files:**
- Create: `web/components/internal/InternalDossierClient.tsx`
- Optionally small presentational children for rate card / proposal read-only views

**Interfaces:**
- Consumes: `fetchInternalDossier`
- Tabs: Estimate | Rate card | Proposal; header with banner; warnings; proposal locale switcher if multiple

- [ ] **Step 1: Implement client** — load dossier on mount; tab state; render:
  - Estimate: readable sections from `report` (reuse display patterns from calculation/export preview where practical; simple definition lists/tables OK)
  - Rate card: table of `settings.roles`, NRC items, `monthly_rc_items`
  - Proposal: show assessment/proposal/poc section titles + body/bullets; empty state

- [ ] **Step 2: Commit**

```bash
git commit -m "Add internal dossier live tabs UI."
```

---

### Task 10: `InternalExportPanel` (identical export feel)

**Files:**
- Create: `web/components/internal/InternalExportPanel.tsx`
- Modify: `web/components/internal/InternalDossierClient.tsx` — mount panel below tabs
- Modify: `web/lib/export-destinations.ts` if needed
- Modify: `web/components/ExportPanel.tsx` — filter out `is_internal_format` from displayed history (defense in depth)

**Interfaces:**
- Mirror `ExportPanel` controls:
  - locale `ja`/`en`
  - formats multi-select mapping to `pdf_internal`, `docx_internal`, `xlsx_internal`, `md_internal`
  - export → `POST /estimates/{id}/export`
  - list → `GET /estimates/{id}/exports?audience=internal`
  - preview / download / delete / email / send-to Google / Canva (reuse helpers)
- Disable export when `!has_calculation`; show API error for `CALCULATION_REQUIRED`

- [ ] **Step 1: Implement panel** by adapting `ExportPanel.tsx` (copy structure; remove quotation version selectors; hard-map format family to `*_internal`; load history with `audience=internal`).

- [ ] **Step 2: Ensure `ExportPanel` ignores internal formats:**

```typescript
function isInternalFormat(format: string): boolean {
  return format.endsWith("_internal");
}
// when setting exports from API: records.filter(r => !isInternalFormat(r.format))
```

- [ ] **Step 3: Manual smoke checklist (document in commit message):** admin exports PDF, preview, download; non-admin cannot open page; main ExportPanel has no internal rows.

- [ ] **Step 4: Commit**

```bash
git commit -m "Add InternalExportPanel matching estimate export UX."
```

---

### Task 11: Integration sweep + verification

**Files:** tests only / small fixes

- [ ] **Step 1: Run unit suite for internal + destinations + export pdf/docx**

```bash
cd api && python -m pytest tests/unit/test_internal_formats.py tests/unit/test_internal_dossier.py tests/unit/test_export_destinations.py -v
```

- [ ] **Step 2: Run integration**

```bash
cd api && python -m pytest tests/integration/test_internal_dossier.py -v
```

- [ ] **Step 3: Fix any failures; ensure CALCULATION_REQUIRED path returns 422 for internal when no calculation** — if shared raise is still 400, raise with `status_code=422` for internal formats (or update shared raise + tests to 422 per spec).

- [ ] **Step 4: Final commit if fixes needed**

```bash
git commit -m "Fix internal dossier edge cases from verification."
```

---

## Spec coverage (self-review)

| Spec requirement | Task |
|------------------|------|
| Admin-only page `.../internal` | 8 |
| Live tabs estimate / rate card / proposal | 9 |
| Full disclosure + omitted sections | 2, 4–5 (report context reuse) |
| Export UX identical (formats, preview, email, destinations) | 10, 6–7 |
| Formats `*_internal` | 1, 6 |
| INTERNAL labeling | 4–5 |
| History only on internal page | 7, 10 |
| Non-admin 403 on API ops | 1, 3, 6, 7 |
| No calculation → clear error | 6, 10 |
| Client exports unchanged | 7, 10 filter |
| Entry link from estimate | 8 |

## Out of scope (do not implement)

- Editing on dossier page
- Non-admin access
- Cross-project hub
- ZIP pack format
- Changing client quotation/report contents
