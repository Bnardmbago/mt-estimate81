# Unified Admin Presentation Presets & Cover Design — Design

**Date:** 2026-07-26  
**Status:** Approved

## Goal

Make **Admin / Presentation** the single place to create and customize **Theme**, **Style**, **Template**, and **Cover** design presets—manually or by uploading a reference JPEG/PNG/PDF and generating drafts with AI. Saved presets are consumed by **Estimate** and **Proposal** preview/export. Strict English/Japanese i18n is required; UI locale follows the existing system header language selector.

## Decisions (locked)

| Decision | Choice |
|----------|--------|
| Scope | Theme + Style + Template + Cover administration on one Admin / Presentation page |
| Rollout | Phase 1: shared admin + Proposal integration; Phase 2: Estimate export integration |
| Preset generation | Hybrid extraction + multimodal AI → editable drafts → admin approve/save |
| Vision fallback | If provider/model lacks vision, use deterministic extraction and manual completion |
| Save flow | Show editable previews; admin approves before any preset becomes active |
| Draft persistence | Persist draft preset sets and candidate assets; stale drafts expire after 30 days |
| Source upload retention | Source bytes are ephemeral; candidate assets are temporary draft objects; only approved assets persist beyond draft expiry |
| Cover ownership | Cover design, assets, page setup, and ordered fields live on **Template** |
| Theme/Style role | Theme supplies brand tokens (colors, fonts, logo); Style supplies spacing/density; Cover may inherit Theme tokens |
| Cover fields | Custom ordered schema per Template; Proposal/Estimate may override values |
| Cover field layout | Backward-compatible ordered layout plus native drag/resize canvas for positioned fields |
| Cover assets | Logo, background image, decorative images; AI candidates or admin upload |
| Background movement | Drag in preview + X/Y/zoom/opacity sliders + exact values; fit modes Cover/Contain/Stretch |
| Design controls | Mixed: selections for position/alignment; sliders + numbers for size/opacity/rotation/zoom; unit inputs for padding/fonts; color picker + hex |
| Direct manipulation | Free movement with optional snapping; resize handles for text, logos, and images |
| Per-field typography | Full font, size, weight, color, alignment, spacing, opacity, geometry, and layer controls |
| Design consistency | Deterministic rule-based Cover→Theme/Style recommendations in v1; suggestions never auto-apply |
| Page setup | Orientation Portrait/Landscape; paper size default **A4**; also A3, Letter, Legal |
| Admin page exports | None — no document export actions on Admin / Presentation |
| Locale UI | Follow system header JA/EN (and dark/light); no language switcher inside the customization panel |
| Preset bilingual content | Enter in current header language; auto-translate the other locale on save; both required before activate |
| Export language | Explicit EN/JA selector on Estimate/Proposal export screens; default = document/current (header) locale |
| Consumers | Estimate and Proposal generate/preview/export select Theme + Style + Template |

## Architecture

### Unified Admin / Presentation page

Tabs/sections on one page:

1. **Overview** — preset set list, create blank, generate from reference  
2. **Theme** — colors, fonts, logo, watermark  
3. **Style** — margins, spacing, type scale, density  
4. **Template** — layout chrome, columns, TOC, cover on/off, **page size/orientation**  
5. **Cover design** — assets, mixed placement controls, ordered variable fields, live preview  
6. **Defaults** — org-wide default Theme / Style / Template  

Creation paths:

- **Generate from reference:** upload JPEG/PNG/PDF → validate → deterministic extraction (palette, geometry) → multimodal AI drafts Theme + Style + Template (+ Cover) → admin review/edit → transactional approve/save  
- **Create blank / edit existing:** same editors without AI seed  

Drafts are not active presets until approval. Saving Theme + Style + Template (and approved assets) is transactional.

### Phased delivery

The current `PresentationBundle` is already wired into Proposal services and exports, while Estimate reports, quotations, dossiers, and spreadsheets use a separate export stack. Keep one target architecture but deliver it in two implementation phases:

1. **Phase 1 — Admin + Proposals:** unified Admin / Presentation, persistent drafts, reference generation, Cover designer, resolver extensions, Proposal preview/export.
2. **Phase 2 — Estimates:** wire the same resolver into Estimate report/quotation/dossier/spreadsheet preview/export adapters. No duplicate Estimate-only presentation model.

Phase 1 may ship independently without implying Estimate support is complete. Phase 2 reuses the approved preset model and does not redesign Admin / Presentation.

### Data flow

```text
Reference upload (ephemeral)
  → extract signals + rasterize PDF pages
  → multimodal AI structured draft
  → schema validate / clamp
  → Admin review (Theme / Style / Template / Cover)
  → Approve → persist presets + approved assets
  → discard source upload

Estimate / Proposal UI
  → select Theme + Style + Template (or defaults / AI recommend)
  → resolve PresentationBundle
  → preview / export (locale from export selector, default header/document locale)
```

### Persistent draft model

Use a dedicated `presentation_preset_drafts` record rather than overloading inactive catalog rows:

- `id`, `status` (`draft` | `processing` | `ready` | `failed`), `source_locale`
- `theme_draft`, `style_draft`, `template_draft` JSONB
- target preset IDs for edits, generation metadata, warnings/errors
- `created_at`, `updated_at`, `expires_at`

Reference bytes are processed ephemerally and deleted after analysis. Candidate assets live under a temporary storage prefix until approval. A scheduled/idempotent cleanup removes draft rows and temporary assets 30 days after the last update; the UI displays the expiry. Approval creates/updates the three real catalog rows and promotes approved assets in one transaction-like service operation, with compensating storage cleanup if the database transaction fails.

### Cover model

Template config includes:

- `cover: boolean` — default include cover for this Template  
- `page: { size: "A4"|"A3"|"Letter"|"Legal", orientation: "portrait"|"landscape" }` — default A4 portrait  
- `cover_fields: [{ key, content: {_i18n: {en: {label, default_text?}, ja: {label, default_text?}}}, required, auto_fill?, emphasis, geometry?, style? }]` — stored/resolved through existing localization helpers; geometry/style follow the Cover canvas addendum  
- `cover_design: { background, alignment, padding, accent, typography, colors, assets[] }`  

Assets:

- Roles: `logo` | `background` | `decorative`  
- Placement: position selection and/or X/Y percentages; size/zoom; opacity; fit mode. Rotation is available for logo/decorative assets. Full-bleed backgrounds use crop/pan/zoom without rotation to avoid empty page corners.  
- Reuse `get_storage_backend()` and the existing Theme-logo storage pattern. Temporary candidates use `presentation-drafts/{draft_id}/...`; approved Cover assets use `presentation-assets/{template_id}/{asset_id}.{ext}`.  
- Only assets approved at save are promoted. Rejected candidates are deleted on approval/discard; stale draft cleanup removes abandoned candidates after 30 days. Replacing/deleting a Template asset removes the previous object after the database update succeeds.  

Per Estimate/Proposal document:

- `cover_values: { [fieldKey]: {_i18n: {en?: {value}, ja?: {value}}} }` — stored/resolved through existing localization helpers  
- Resolution order: user override → auto-fill from document facts → Template default → missing required flagged before export  
- Values for unknown keys (after Template switch) retained but not rendered  

Export screens may still allow overriding **whether** to include the cover for that specific export without changing the Template default. Cover **design** is not redesigned on Estimate/Proposal screens.

### Cover consistency recommendations

Whenever an admin changes material Cover design values—colors, typography, logo, background/artwork, alignment, spacing, or visual density—the editor runs a deterministic comparison against the currently paired Theme and Style. V1 does not make an additional AI call for consistency recommendations.

- Recommend Theme changes for colors, fonts, logo/branding, borders, and related visual tokens.
- Recommend Style changes for spacing, typography scale, margins, and density.
- Rule examples: Cover colors outside the Theme palette suggest the nearest/additional Theme token; Cover font mismatch suggests the Theme heading/body font; Cover padding/type scale outside configured tolerances suggests corresponding Style values.
- Rules use explicit tolerances and return stable suggestion IDs, confidence, and rationale so they are unit-testable.
- Show each suggestion as a before/after field-level diff with a short consistency rationale.
- Let the admin **apply all**, **apply selected**, or **dismiss**.
- Applying suggestions updates only the current draft preset set. Existing active presets and documents remain unchanged until the admin approves and activates the draft.
- Never silently mutate Theme or Style. Low-confidence or unsupported observations appear as warnings, not changes.
- Re-run the live preview after applied suggestions and allow reset to the pre-recommendation draft.
- AI-assisted aesthetic recommendations are deferred until deterministic rules prove insufficient.

### Presentation resolution

Existing Theme / Style / Template catalogs remain independent IDs. A shared generation/metadata id may record that three presets were created together; they remain selectable independently afterward.

Resolver (`PresentationBundle`) gains:

- Template page size/orientation  
- Cover design + assets URLs  
- Resolved cover field labels/values for the export locale  

Adapters (web preview, PDF, DOCX; MD/XLSX best-effort) consume the same bundle. Cover is first-class for PDF/DOCX/web; MD/XLSX get heading/metadata or summary-sheet equivalents.

## AI generation (hybrid)

1. Validate MIME, size, PDF page limit; reject encrypted/corrupt PDFs.  
2. Deterministic analyzer: color palette, approximate margins/geometry.  
3. Resolve the configured provider through `get_ai_provider()` and check an explicit vision-capability flag/model allowlist.  
4. When vision is supported, a new multimodal adapter receives signals + selected page images and returns strict JSON for Theme, Style, Template (incl. Cover + page setup + fields), suggested IDs/names/descriptions (current locale), confidence/warnings.  
5. When vision is unavailable or the multimodal call fails, keep the deterministic palette/geometry draft, show a localized warning, and let the admin complete unsupported fields manually. Upload analysis must not fail solely because vision is unavailable.  
6. Validators normalize unsupported values and clamp ranges; invalid output never partially activates presets.  
7. Admin can reset individual axes to the latest generated result before approve.

AI produces **configs and asset candidates**, not pixel-perfect clones of the reference.

## i18n (strict EN/JA)

- All Admin / Presentation UI strings use `en.json` / `ja.json` keys; locale = system header.  
- No language toggle inside the customization panel.  
- Preset names, descriptions, cover-field labels, and default texts store both `en` and `ja`.  
- Reuse `app.i18n.localized_content` (`store_localized_dict`, `resolve_localized_dict`, `has_localized_locale`) and its `_i18n` storage shape; do not introduce a second localization format.  
- Admin edits localized fields in the current header language; save auto-translates the other locale through the existing `get_ai_provider()` / narrative-translation pattern.  
- Before activate, show a compact bilingual review of the auto-translated fields (inline, not a panel language mode). Users may correct either locale there, or switch the system header and continue editing.  
- Preset cannot become **active** until both locales are present.  
- Estimate/Proposal export: explicit EN/JA selector; default = document/current locale.  
- Theme logo remains the brand logo for headers/branding; Cover may include its own logo/background/decorative slots and may default from the Theme logo.  
- Export labels, dates, paper metadata, validation errors, and filenames follow the selected export locale.  
- Theme visual tokens are language-neutral; fonts must support Japanese glyphs with locale-aware fallbacks.  
- Tests enforce translation-key parity and bilingual export/preview paths.

## Validation, errors, and safety

- Clamp dimensions, opacity, rotation, font sizes, and image positions to export-safe ranges.  
- AI or translation failure: keep draft or retry; never create partial active presets.  
- Temporary reference files and rejected extracted assets always deleted.  
- Cleanup is idempotent: approval/discard cleans immediate candidates, and a scheduled sweep removes drafts/assets stale for 30 days.  
- Preview and exports share one resolved presentation model.  
- Backward compatible: existing presets get defaults A4 portrait and current cover behavior.
- Test matrix: A4 portrait and landscape receive full web/PDF/DOCX coverage; Letter receives core adapter coverage; A3 and Legal are supported with dimension/orientation smoke tests to bound v1 test cost. MD/XLSX remain best-effort.

## Cover canvas addendum

Direct dragging, resizing, snapping, per-field typography, layer order, and the non-blocking disabled-Cover state are specified in `docs/superpowers/specs/2026-07-27-cover-canvas-editor-design.md`. That addendum supersedes the earlier fixed-region limitation while retaining ordered layout as the legacy fallback.

## Out of scope

- Pixel-perfect magazine/multi-page layout beyond the Cover canvas  
- Custom uploaded fonts as first-class Theme assets (logo/images only in this design)  
- Redesigning cover on Estimate/Proposal screens (selection + text/values + optional cover include override only)  
- Document export actions from Admin / Presentation  
- Per-user personal Themes  
- AI-driven Cover→Theme/Style aesthetic consistency recommendations (v1 uses deterministic rules)  

## Success criteria

1. Admin can create Theme/Style/Template(+Cover) from blank or from a reference file with AI drafts and approve/save.  
2. Cover supports assets, mixed controls, ordered bilingual fields, A4 default, portrait/landscape.  
3. Locale UI follows header; bilingual content is required before activate; exports support explicit EN/JA.  
4. Proposals consume the presets in Phase 1; Estimates consume the same resolver/presets after Phase 2.  
5. No language switcher or export action on Admin / Presentation.  
6. Source uploads are ephemeral; draft candidates expire; only approved assets persist beyond the draft lifecycle.
7. Material Cover changes produce optional, deterministic field-level Theme/Style consistency recommendations without automatic mutation.
8. Vision-unavailable providers still produce an editable deterministic draft instead of failing.
9. Drafts survive navigation/reload and stale drafts/candidate assets are cleaned after 30 days.
10. Phase 1 completion is measured against Proposals; Estimate integration is separately testable Phase 2 work using the same resolver.
11. Cover text/assets support direct drag/resize, optional snapping, synchronized values, and full per-field text styling.
