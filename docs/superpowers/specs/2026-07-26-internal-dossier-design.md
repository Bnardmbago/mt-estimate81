# Internal Dossier (Estimate) — Design

**Date:** 2026-07-26  
**Status:** Approved for planning (export UX revised)

## Goal

Give admins an **internal-only** view of one estimate’s complete delivery package: full estimate details (including sections omitted from client docs), the frozen rate card, and linked proposal(s). Support live browsing on a dedicated page, plus an **Export** experience that feels identical to estimate and proposal exports (formats, preview, history, email, destinations).

Client-facing quotations and reports stay unchanged.

## Decisions (locked)

| Decision | Choice |
|----------|--------|
| Delivery shape | New admin-only page (not export-toggle-only) |
| Scope | One estimate’s dossier: estimate + linked proposal(s) + rate card used for that estimate |
| Access | Admins only (web + API) |
| Save/download | Live browse + Export panel identical in feel to estimate/proposal |
| Disclosure level | Full rate card + full estimate calculation + full proposal/POC, including content client docs omit (cost drivers, risks, questionnaire appendix, AI confidence notes, etc.) |
| Export formats | Same family as estimate report exports: PDF, DOCX, XLSX, MD (internal content; **no** quotation variants) |
| Destinations / email | Included (same as estimate/proposal); all artifacts carry INTERNAL labeling |
| Editing | Read-only on this page; edit elsewhere |

## Access, routing, entry points

**Route:** `/{locale}/estimates/[id]/internal`

**Web:** Server-side admin check (same pattern as `/admin`). Non-admins redirect away. Contact users never see the link.

**API:** Dossier read and all internal export generate/list/download/delete/email/send-to endpoints require admin (`require_admin`).

**Entry:** Admin-only control on the estimate detail page (“Internal dossier”). Optional later: entry from proposal page pointing at the same estimate dossier — not required for v1.

**Unchanged:** Existing client/quotation exports, contact export limits, and non-admin estimate/proposal/rate-card UX.

## Page layout (live dossier)

**Header**
- Project / client name, estimate id, status
- Banner: **Internal — not for clients**
- Rate card name + frozen version (when calculated); link to rate card editor when useful
- Back to estimate

**Tabs**

| Tab | Content |
|-----|---------|
| Estimate | Full internal report: executive summary, assumptions, requirements, features, effort/phase/role breakdowns, NRC/RC detail, cost drivers, risks & gaps, exclusions, AI confidence, questionnaire appendix when present |
| Rate card | Full frozen settings: roles/rates, NRC setup items, RC monthly items, policy metadata — not name/version only |
| Proposal | Linked proposal(s) for this estimate (per locale if multiple): full proposal + POC; empty state if none |

**Export section** (below tabs, or a fourth “Export” tab — prefer a dedicated section matching `ExportPanel` / `ProposalExportPanel` layout)

Same controls and flow as estimate/proposal export:

- Locale selector (`ja` / `en`)
- Format multi-select: **PDF**, **DOCX**, **XLSX**, **Markdown** (no report/quotation version split — every format is the full internal dossier content)
- Export button → generates one stored file per selected format
- Downloads / history list: preview (PDF), download, delete, selection checkboxes
- Email selected exports
- Send to Google / Canva for compatible formats (same destination rules as today)
- Stale-export confirmation when calculation is newer than last export (same pattern)

**Behavior**
- Read-only live data composed from existing records
- Clear warning if calculation is missing or rate card/fingerprint is stale; still show what exists
- UI locale for labels; proposal tab can switch among available proposal locales
- Export disabled (or blocked with `CALCULATION_REQUIRED`) until a calculation exists

## API and data flow

### Live dossier

`GET /estimates/{id}/internal-dossier` (admin-only)

Composed response (no new dossier table):
- Estimate summary + full internal report context (same richness as detailed report, including sections client docs omit)
- Frozen rate card settings, or null with reason
- Linked proposals (id, locale, status, sections) for this estimate

### Internal exports

Reuse the estimate export pipeline with **internal format codes** (parallel to `pdf_quotation`):

| Format code | Artifact |
|-------------|----------|
| `pdf_internal` | Full dossier PDF |
| `docx_internal` | Full dossier DOCX |
| `xlsx_internal` | Full dossier workbook |
| `md_internal` | Full dossier Markdown |

`POST /estimates/{id}/export` with one of the above formats (admin-only).

Each artifact includes:
- Full estimate internal report content
- Full rate card appendix
- Proposal/POC appendix when present (else marked none)
- Clear INTERNAL labeling (PDF watermark / header-footer; equivalent banner text in DOCX/MD; sheet note in XLSX)

Writes normal `exports` rows. List/download/delete/email/send-to use the **same endpoints** as other estimate exports, with admin-only enforcement whenever `format` is `*_internal`.

Non-admins: 403 on generate, download, delete, email, and send-to for internal formats (even if they know the export id).

Internal formats appear in the **internal dossier Export section** as the primary UI. They may also show in the main estimate export list labeled as Internal (generate still admin-only); if that clutters the client export list, hide `*_internal` from the non-admin ExportPanel and only show them on the internal page — **prefer: show internal history only on the internal dossier page** so client export UI stays clean.

### Flow

```text
Estimate page (admin) → Internal dossier page
        ↓
GET internal-dossier → render tabs (live)
        ↓
Export section (same UX as ExportPanel)
        ↓
POST export format=pdf_internal|docx_internal|xlsx_internal|md_internal
        ↓
list / preview / download / delete / email / send-to (existing endpoints, admin-gated for *_internal)
```

### Errors

| Case | Behavior |
|------|----------|
| Non-admin | 403 |
| Estimate missing / inaccessible | 404 |
| Export requested with no calculation | 422 with code `CALCULATION_REQUIRED` |
| No proposal yet | Export still generates; proposal section marked none |

## Architecture notes

- Reuse `build_report_context` / DOCX / XLSX / MD generators; add an internal dossier context that appends full rate card settings + proposal/POC + ensures omitted sections are present.
- Load frozen `rate_card_version` settings for the estimate’s `rate_card_version_id`.
- Load proposals by `estimate_id` (unique per locale today).
- Extend `ExportFormat` and `ExportRequest` pattern for `pdf_internal`, `docx_internal`, `xlsx_internal`, `md_internal`.
- Frontend: page under `web/app/[locale]/estimates/[id]/internal/` with dossier tabs + an export panel component modeled on `ExportPanel` / `ProposalExportPanel` (shared patterns for preview, destinations, email).

## Out of scope (v1)

- Editing from the internal page
- Access for contact or non-admin full accounts
- Cross-project internal hub / search
- ZIP multi-file pack as a separate format (multi-format multi-select already covers separate files)
- Changing client quotation/report export contents
- Quotation-style variants for internal exports

## Testing

- **Unit:** Dossier composer includes rate card settings + omitted report sections; each internal format contains markers for estimate / rate card / proposal (or “none”) and INTERNAL labeling
- **Integration:** Non-admin → 403 on dossier and all `*_internal` generate/download/email/send-to; admin can export each format, preview PDF, download, delete, email, send-to
- **UI:** Admin sees identical export controls on the internal page; non-admin does not see the page; main estimate ExportPanel does not offer internal formats to non-admins

## Success criteria

- Admin can open one estimate’s internal dossier and see estimate, full rate card, and proposals without client omissions
- Admin can export internal PDF/DOCX/XLSX/MD with the same feel as estimate/proposal export (history, preview, email, destinations)
- Non-admins cannot open the page or generate/download/email/send internal exports via API
- Client-facing export formats and ExportPanel options remain unchanged for non-admins
- Every internal artifact is clearly labeled as internal / do not distribute
