# Internal Dossier (Estimate) — Design

**Date:** 2026-07-26  
**Status:** Approved for planning

## Goal

Give admins an **internal-only** view of one estimate’s complete delivery package: full estimate details (including sections omitted from client docs), the frozen rate card, and linked proposal(s). Support live browsing on a dedicated page and optionally saving a dated **internal pack** into export history for later download.

Client-facing quotations and reports stay unchanged.

## Decisions (locked)

| Decision | Choice |
|----------|--------|
| Delivery shape | New admin-only page (not export-toggle-only) |
| Scope | One estimate’s dossier: estimate + linked proposal(s) + rate card used for that estimate |
| Access | Admins only (web + API) |
| Save/download | Live browse + optional dated pack in export history |
| Disclosure level | Full rate card + full estimate calculation + full proposal/POC, including content client docs omit (cost drivers, risks, questionnaire appendix, AI confidence notes, etc.) |
| Pack format (v1) | Single PDF (`internal_pack`); ZIP multi-file deferred |
| Editing | Read-only on this page; edit elsewhere |

## Access, routing, entry points

**Route:** `/{locale}/estimates/[id]/internal`

**Web:** Server-side admin check (same pattern as `/admin`). Non-admins redirect away. Contact users never see the link.

**API:** Dossier read and `internal_pack` generation require admin (`require_admin`).

**Entry:** Admin-only control on the estimate detail page (“Internal dossier”). Optional later: entry from proposal page pointing at the same estimate dossier — not required for v1.

**Unchanged:** Existing client/quotation exports, contact export limits, watermarks, and non-admin estimate/proposal/rate-card UX.

## Page layout (live dossier)

**Header**
- Project / client name, estimate id, status
- Banner: **Internal — not for clients**
- Rate card name + frozen version (when calculated); link to rate card editor when useful
- Actions: Save internal pack, download latest pack (if any), back to estimate

**Tabs**

| Tab | Content |
|-----|---------|
| Estimate | Full internal report: executive summary, assumptions, requirements, features, effort/phase/role breakdowns, NRC/RC detail, cost drivers, risks & gaps, exclusions, AI confidence, questionnaire appendix when present |
| Rate card | Full frozen settings: roles/rates, NRC setup items, RC monthly items, policy metadata — not name/version only |
| Proposal | Linked proposal(s) for this estimate (per locale if multiple): full proposal + POC; empty state if none |

**Behavior**
- Read-only live data composed from existing records
- Clear warning if calculation is missing or rate card/fingerprint is stale; still show what exists
- UI locale for labels; proposal tab can switch among available proposal locales

## API and data flow

### Live dossier

`GET /estimates/{id}/internal-dossier` (admin-only)

Composed response (no new dossier table):
- Estimate summary + full internal report context (same richness as detailed report, including sections client docs omit)
- Frozen rate card settings, or null with reason
- Linked proposals (id, locale, status, sections) for this estimate

### Save pack

`POST /estimates/{id}/export` with format `internal_pack` (admin-only; reject for non-admins)

- Builds one stored PDF artifact
- Contents: estimate internal report + full rate card appendix + proposal/POC appendix when present
- PDF header/footer watermark: e.g. `INTERNAL — DO NOT DISTRIBUTE`
- Writes normal `exports` row (`format=internal_pack`) for re-download/delete via existing export endpoints
- Visible on the internal page history; may also appear in the estimate export list labeled **Internal pack** (generate restricted to admins)
- `GET /exports/{id}/download` (and delete) for `format=internal_pack` also requires admin — non-admins get 403 even if they somehow know the export id

### Flow

```text
Estimate page (admin) → Internal dossier page
        ↓
GET internal-dossier → render tabs (live)
        ↓
POST export format=internal_pack → store file → list/download via existing export endpoints
```

### Errors

| Case | Behavior |
|------|----------|
| Non-admin | 403 |
| Estimate missing / inaccessible | 404 |
| Pack requested with no calculation | 422 with code `CALCULATION_REQUIRED` |
| No proposal yet | Pack still generates; proposal section marked none |

## Architecture notes

- Reuse `build_report_context` (and related export builders) for estimate content; extend or add an internal view model so rate card **settings** and omitted sections are included in dossier + pack.
- Load frozen `rate_card_version` settings for the estimate’s `rate_card_version_id`.
- Load proposals by `estimate_id` (unique per locale today).
- Extend `ExportFormat` / export request pattern to accept `internal_pack`.
- Frontend: new page under `web/app/[locale]/estimates/[id]/internal/` plus a small client component for tabs, pack actions, and history.

## Out of scope (v1)

- Editing from the internal page
- Send-to Google/Canva or email of internal packs to clients
- Access for contact or non-admin full accounts
- Cross-project internal hub / search
- ZIP multi-file pack
- Changing client quotation/report export contents

## Testing

- **Unit:** Dossier composer includes rate card settings + omitted report sections; pack PDF contains markers for estimate / rate card / proposal (or “none”)
- **Integration:** Non-admin → 403 on dossier and `internal_pack`; admin can GET dossier and POST/download pack; pack appears in export list
- **UI:** Admin sees link and page; non-admin does not

## Success criteria

- Admin can open one estimate’s internal dossier and see estimate, full rate card, and proposals without client omissions
- Admin can save a dated `internal_pack` PDF and re-download it from history
- Non-admins cannot open the page or generate/download internal packs via API
- Client-facing export formats remain unchanged
- Internal pack is clearly labeled as internal / do not distribute
