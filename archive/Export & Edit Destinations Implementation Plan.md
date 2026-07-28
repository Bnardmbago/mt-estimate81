# Export & Edit Destinations Implementation Plan

> **Status:** Dual path — local Download and open with + OAuth cloud (Google Docs/Sheets, Canva). No Replace file.

**Goal:** Polish exports either on the PC (installed apps) or in Google/Canva via OAuth auto-upload, while mt-estimate81 remains the source of truth for pricing.

## Paths

1. **Download and open with {App}** — DOCX→Word/Pages, XLSX→Excel/Numbers, Proposal/POC PDF→Canva, MD→IDE.
2. **Open in Docs / Sheets / Canva** — Admin configures OAuth apps; users connect under Settings; send-to uploads and opens.

## Admin / Settings

- Admin → OAuth apps (Google + Canva credentials + Canva template IDs)
- Settings → Connected accounts
- Migration `038_restore_oauth_destinations`

## Out of scope

- Replace-file re-upload
- Native force-launch of Word without download
- External tools as pricing system of record
