# Presentation Presets & Cover Design — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver unified Admin / Presentation (Theme, Style, Template, Cover), reference-to-draft AI generation, persistent drafts, bilingual activation, Cover→Theme/Style consistency recommendations, and Proposal preview/export consumption with A4-default page setup.

**Architecture:** Extend the existing Theme/Style/Template catalogs and `PresentationBundle` resolver. Add a draft lifecycle table for AI/manual preset sets, store Cover design on Template config, resolve Cover fields/values through `_i18n`, and render rich covers in Proposal PDF/DOCX/web. Estimates remain Phase 2.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, OpenAI/Anthropic multimodal, WeasyPrint/Jinja, python-docx, Next.js, next-intl, existing `localized_content` + storage backend.

## Global Constraints

- Paper size default is **A4**; orientation Portrait/Landscape; also support A3, Letter, Legal.
- Cover design, assets, page setup, and ordered fields live on **Template**.
- Theme supplies brand tokens; Style supplies spacing/density; Cover may inherit Theme tokens.
- Source uploads are ephemeral; draft candidate assets expire after 30 days; only approved assets persist.
- UI locale follows system header JA/EN; no language switcher inside Admin / Presentation.
- Preset bilingual content uses `app.i18n.localized_content` `_i18n` shape; auto-translate on save; both locales required before activate.
- Cover→Theme/Style consistency is **deterministic** in v1; suggestions never auto-apply.
- If vision is unavailable, keep deterministic extraction draft and allow manual completion.
- No document export actions on Admin / Presentation.
- Safe import edits: never remove unrelated imports when adding modules.
- Do **not** commit unless the user explicitly asks.
- Phase 1 completion is measured against Proposals only.

---

### Task 1: Draft model + cover schema migration

**Files:**
- Create: `api/alembic/versions/039_presentation_drafts_and_cover.py`
- Modify: `api/app/models/presentation.py`
- Create: `api/app/models/presentation_draft.py`
- Modify: `api/app/models/__init__.py`
- Modify: `api/app/models/proposal.py`
- Modify: `api/app/presentation/seeds.py`
- Test: `api/tests/unit/test_presentation_draft_model.py`

**Interfaces:**
- Consumes: existing `038_restore_oauth_destinations` migration head; existing presentation models
- Produces: `PresentationPresetDraft` model; `proposals.cover_values` JSONB; Template seed defaults for `page`, `cover_fields`, `cover_design`

- [ ] **Step 1: Write the failing model/import test**

```python
# api/tests/unit/test_presentation_draft_model.py
from app.models.presentation_draft import PresentationPresetDraft
from app.presentation.seeds import CLASSIC_LINEAR_TEMPLATE

def test_seed_template_has_page_and_cover_defaults():
    assert CLASSIC_LINEAR_TEMPLATE["page"] == {"size": "A4", "orientation": "portrait"}
    assert "cover_fields" in CLASSIC_LINEAR_TEMPLATE
    assert "cover_design" in CLASSIC_LINEAR_TEMPLATE

def test_draft_model_tablename():
    assert PresentationPresetDraft.__tablename__ == "presentation_preset_drafts"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd api && pytest tests/unit/test_presentation_draft_model.py -v`  
Expected: FAIL (module/attrs missing)

- [ ] **Step 3: Implement migration, model, seed defaults**

Migration `039` must:
- `down_revision = "038_restore_oauth_destinations"`
- create `presentation_preset_drafts` with columns: `id` (UUID PK), `status`, `source_locale`, `theme_draft`, `style_draft`, `template_draft`, `target_theme_id`, `target_style_id`, `target_template_id`, `generation_meta`, `errors`, `created_at`, `updated_at`, `expires_at`
- add `proposals.cover_values` JSONB nullable/default `{}`
- optionally backfill existing template configs with page/cover defaults via SQL UPDATE JSON merge

Seed defaults:

```python
DEFAULT_PAGE = {"size": "A4", "orientation": "portrait"}
DEFAULT_COVER_DESIGN = {
    "alignment": "left",
    "padding_mm": 24,
    "accent": {"enabled": True, "width_mm": 48},
    "typography": {"title_pt": 30, "metadata_pt": 10},
    "colors": {},
    "assets": [],
}
# Merge into CLASSIC_LINEAR_TEMPLATE / EXECUTIVE_COVER_TEMPLATE / TWO_COLUMN_SUMMARY_TEMPLATE
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd api && pytest tests/unit/test_presentation_draft_model.py -v`  
Expected: PASS

- [ ] **Step 5: Apply migration locally**

Run: `cd api && python -m alembic upgrade head`  
Expected: heads at `039_...`

---

### Task 2: Validators, cover resolver, consistency rules

**Files:**
- Create: `api/app/presentation/validators.py`
- Create: `api/app/presentation/cover.py`
- Create: `api/app/presentation/consistency.py`
- Create: `api/tests/unit/test_presentation_validators.py`
- Create: `api/tests/unit/test_presentation_cover_resolver.py`
- Create: `api/tests/unit/test_presentation_consistency.py`

**Interfaces:**
- Consumes: `_i18n` helpers from `app.i18n.localized_content`
- Produces:
  - `normalize_page(page: dict) -> dict`
  - `clamp_cover_design(design: dict) -> dict`
  - `resolve_cover_fields(template_fields, cover_values, *, display_locale, fallback_locale, document_facts) -> tuple[list[dict], list[str]]`
  - `recommend_consistency(*, cover_design, theme_draft, style_draft) -> list[dict]`

- [ ] **Step 1: Write failing unit tests for normalize/clamp/resolve/consistency**

Include cases:
- missing page → A4 portrait
- opacity 1.4 → 1.0; background rotation stripped
- cover value override beats auto-fill beats template default
- unknown cover value keys retained but not rendered
- cover title color outside theme palette yields Theme suggestion with stable `id`

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd api && pytest tests/unit/test_presentation_validators.py tests/unit/test_presentation_cover_resolver.py tests/unit/test_presentation_consistency.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement pure functions**

Keep consistency deterministic: no AI calls. Suggestion shape:

```python
{
  "id": "theme.colors.primary",
  "target": "theme",
  "field_path": "colors.primary",
  "before": "1E3A5F",
  "after": "17365D",
  "confidence": 0.9,
  "rationale": "Cover title color is outside Theme palette",
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd api && pytest tests/unit/test_presentation_validators.py tests/unit/test_presentation_cover_resolver.py tests/unit/test_presentation_consistency.py -v`  
Expected: PASS

---

### Task 3: Extend PresentationBundle resolver

**Files:**
- Modify: `api/app/presentation/resolver.py`
- Modify: `api/tests/unit/test_presentation_resolver.py`

**Interfaces:**
- Consumes: validators + cover helpers
- Produces: `PresentationBundle` with `page`, `cover_design`, `cover_fields`, `cover_assets`, helpers for CSS page size

- [ ] **Step 1: Extend resolver tests for legacy templates lacking page/cover_design**

Assert soft defaults to A4 portrait and empty cover fields/assets; executive-cover keeps `cover=True`.

- [ ] **Step 2: Run failing/updated tests**

Run: `cd api && pytest tests/unit/test_presentation_resolver.py -v`

- [ ] **Step 3: Implement resolver extensions via deep-merge defaults**

- [ ] **Step 4: Confirm existing soft-fallback tests still pass**

Run: `cd api && pytest tests/unit/test_presentation_resolver.py -v`  
Expected: PASS

---

### Task 4: Draft service, storage prefixes, cleanup

**Files:**
- Create: `api/app/presentation/drafts.py`
- Create: `api/app/presentation/cleanup.py`
- Modify: `api/app/storage/base.py`
- Modify: `api/app/storage/local.py`
- Modify: `api/app/presentation/service.py`
- Create: `api/tests/unit/test_presentation_drafts.py`

**Interfaces:**
- Consumes: storage backend, draft model, validators
- Produces:
  - `create_blank_draft(...)`
  - `update_draft_axis(...)`
  - `approve_draft(...) -> dict[str,str]`
  - `discard_draft(...)`
  - `cleanup_stale_presentation_drafts(db) -> int`
  - storage `list_prefix` / `delete_prefix`

Storage paths:
- draft candidates: `presentation-drafts/{draft_id}/{asset_id}.{ext}`
- approved assets: `presentation-assets/{template_id}/{asset_id}.{ext}`

- [ ] **Step 1: Write failing draft lifecycle tests** (blank → patch → approve creates 3 presets; discard deletes candidates; expired cleanup removes draft)

- [ ] **Step 2: Run tests expecting FAIL**

- [ ] **Step 3: Implement draft service + storage prefix helpers + cleanup**

Approval must be transactional for DB rows; if DB commit fails after promoting assets, delete newly written approved assets. Rejected candidates deleted on approve/discard.

- [ ] **Step 4: Run tests expecting PASS**

---

### Task 5: Reference analyzer + vision-capable AI draft generation

**Files:**
- Create: `api/app/presentation/reference_analyzer.py`
- Create: `api/app/presentation/generate.py`
- Create: `api/app/ai/schemas_presentation.py`
- Modify: `api/app/ai/provider.py`
- Modify: `api/app/ai/openai_adapter.py`
- Modify: `api/app/ai/anthropic_adapter.py`
- Modify: `api/app/ai/factory.py`
- Create: `api/tests/unit/test_presentation_reference_analyzer.py`

**Interfaces:**
- Consumes: `get_ai_provider`, rate-limit retry, instruction resolver patterns
- Produces:
  - `analyze_reference(content: bytes, filename: str | None, content_type: str | None) -> dict`
  - `provider.supports_vision() -> bool`
  - `provider.generate_presentation_draft(*, source_locale, signals, page_images, ...) -> PresentationDraftAI`
  - `run_reference_generation(draft_id: str) -> None` background entrypoint

- [ ] **Step 1: Write analyzer tests** (JPEG/PNG accepted; empty rejected; corrupt PDF rejected; palette keys present)

- [ ] **Step 2: Run FAIL then implement deterministic analyzer**

Use Pillow if available, otherwise a minimal PNG/JPEG color sampling path. For PDF, use a limited page rasterization path (pypdfium2 or convert via existing stack if available); if PDF rasterization unavailable, extract text/page count only and still return geometry defaults.

- [ ] **Step 3: Add vision capability helpers + multimodal draft schema**

If `supports_vision()` is False or multimodal call fails: persist deterministic draft + warning; never fail solely for missing vision.

- [ ] **Step 4: Unit-test no-vision fallback with a stub provider**

Run: `cd api && pytest tests/unit/test_presentation_reference_analyzer.py -v`  
Expected: PASS

---

### Task 6: Bilingual translate-on-save for presets/drafts

**Files:**
- Create: `api/app/presentation/translate.py`
- Modify: `api/app/presentation/drafts.py` (approve gate)
- Create: `api/tests/unit/test_presentation_translate.py`

**Interfaces:**
- Consumes: `store_localized_dict`, `has_localized_locale`, `get_ai_provider().translate_export_narrative`
- Produces: `ensure_preset_bilingual(db, payload, *, content_locale) -> dict`

- [ ] **Step 1: Write failing tests** for missing locale auto-fill and activate blocked when translation fails

- [ ] **Step 2: Implement translate helper mirroring `narrative_translate.py`**

- [ ] **Step 3: Gate `approve_draft` until both locales present for names/descriptions/cover field labels**

- [ ] **Step 4: Run tests PASS**

---

### Task 7: Admin draft/cover API routes + schemas

**Files:**
- Create: `api/app/schemas/presentation_draft.py`
- Modify: `api/app/schemas/presentation.py`
- Modify: `api/app/admin/presentation.py`
- Create: `api/tests/integration/test_presentation_admin.py`

**Interfaces:**
- Routes under `/admin/presentation/drafts...` as mapped in backend exploration
- No export endpoints on admin presentation router

- [ ] **Step 1: Write integration test** blank draft → patch cover → consistency → translate → approve → public catalog contains new presets

- [ ] **Step 2: Implement schemas + routes**

- [ ] **Step 3: Run integration test PASS**

Run: `cd api && pytest tests/integration/test_presentation_admin.py -v`

---

### Task 8: Proposal cover_values + export include_cover + locale

**Files:**
- Modify: `api/app/schemas/proposal.py`
- Modify: `api/app/proposals/service.py`
- Modify: `api/app/proposals/router.py`
- Modify: `api/app/proposals/export_service.py`
- Modify: `api/app/proposals/export_context.py`
- Modify: `api/app/proposals/export_formats.py`
- Modify: `api/app/exports/templates/proposal_pack.html.j2`
- Modify: `api/tests/unit/test_proposal_export_formats.py`
- Modify: `api/tests/integration/test_proposals.py`
- Create: `api/tests/integration/test_proposal_cover_export.py`

**Interfaces:**
- `PATCH /proposals/{id}/cover-values`
- `POST /proposals/{id}/export` accepts `include_cover?: bool`, `locale`, presentation IDs, optional cover_values override for that export request
- Export context includes resolved cover fields/assets/page CSS

- [ ] **Step 1: Write export format tests** for A4 portrait/landscape cover rendering and Letter core smoke

- [ ] **Step 2: Implement cover-aware PDF/DOCX and `@page` size/orientation**

- [ ] **Step 3: Integration test export with cover on/off override**

- [ ] **Step 4: Run targeted proposal/presentation tests PASS**

```bash
cd api && pytest tests/unit/test_presentation_resolver.py \
  tests/unit/test_proposal_export_formats.py \
  tests/integration/test_proposals.py \
  tests/integration/test_proposal_cover_export.py -v
```

---

### Task 9: Frontend presentation API client + admin shell

**Files:**
- Modify: `web/lib/presentation.ts`
- Create: `web/components/admin/presentation/PresentationAdminShell.tsx`
- Create: `web/components/admin/presentation/PresentationOverviewTab.tsx`
- Create: `web/components/admin/presentation/PresentationDefaultsSection.tsx`
- Create: `web/components/admin/presentation/PresentationThemeEditor.tsx`
- Create: `web/components/admin/presentation/PresentationStyleEditor.tsx`
- Create: `web/components/admin/presentation/PresentationTemplateEditor.tsx`
- Modify: `web/components/admin/PresentationSettingsPanel.tsx` (thin wrapper)
- Modify: `web/messages/en.json`
- Modify: `web/messages/ja.json`

**Interfaces:**
- Client helpers for drafts/reference/assets/consistency/approve
- Shell tabs: Overview / Theme / Style / Template / Cover / Defaults
- Header locale drives UI strings via `useTranslations`; no in-panel language switcher

- [ ] **Step 1: Extend `web/lib/presentation.ts` types and API functions**

- [ ] **Step 2: Build tabbed shell and migrate defaults/theme/style/template editors from JSON CRUD**

Keep advanced JSON edit as optional collapse if useful, but primary UX is form controls.

- [ ] **Step 3: Add EN/JA message keys with strict parity**

- [ ] **Step 4: `cd web && npm run build`** Expected: PASS

---

### Task 10: Cover designer UI + consistency + bilingual review

**Files:**
- Create: `web/components/admin/presentation/PresentationCoverDesigner.tsx`
- Create: `web/components/admin/presentation/PresentationCoverPreview.tsx`
- Create: `web/components/admin/presentation/PresentationCoverAssetControls.tsx`
- Create: `web/components/admin/presentation/PresentationCoverFieldList.tsx`
- Create: `web/components/admin/presentation/PresentationConsistencyPanel.tsx`
- Create: `web/components/admin/presentation/PresentationBilingualReview.tsx`
- Modify: `web/app/globals.css`
- Modify: `web/messages/en.json`
- Modify: `web/messages/ja.json`

**Interfaces:**
- Mixed controls: selection for position/alignment; slider+number for X/Y/zoom/opacity; number+unit for padding/fonts; color picker+hex
- Background: pan/zoom/opacity/fit, no rotation
- Consistency panel: apply all / selected / dismiss / reset
- Bilingual review before activate

- [ ] **Step 1: Implement Cover designer + live preview**

- [ ] **Step 2: Wire consistency recommendations and bilingual review into approve flow**

- [ ] **Step 3: Build and smoke-check admin presentation tab**

Run: `cd web && npm run build`

---

### Task 11: Proposal UI cover values + export locale/include cover

**Files:**
- Create: `web/components/proposal/ProposalCoverFields.tsx`
- Create: `web/components/proposal/ProposalCoverIncludeToggle.tsx`
- Create: `web/components/proposal/ProposalExportLocaleSelector.tsx`
- Modify: `web/components/proposal/ProposalPageClient.tsx`
- Modify: `web/components/proposal/ProposalExportPanel.tsx`
- Modify: `web/lib/proposal.ts`
- Modify: `web/lib/proposal-types.ts`
- Modify: `web/messages/en.json`
- Modify: `web/messages/ja.json`

**Interfaces:**
- Mirror Estimate `ExportPanel` locale selector pattern
- Export body includes `locale`, `include_cover`, presentation IDs, cover values as needed

- [ ] **Step 1: Add types/API helpers**

- [ ] **Step 2: Wire cover fields on Proposal page + export panel controls**

- [ ] **Step 3: Build web + run proposal integration tests**

```bash
cd web && npm run build
cd ../api && pytest tests/integration/test_proposals.py tests/integration/test_proposal_cover_export.py -v
```

---

### Task 12: Phase 1 verification sweep

**Files:** none new

- [ ] **Step 1: Run full Phase 1 API verification**

```bash
cd api && pytest tests/unit/test_presentation_resolver.py \
  tests/unit/test_presentation_draft_model.py \
  tests/unit/test_presentation_validators.py \
  tests/unit/test_presentation_cover_resolver.py \
  tests/unit/test_presentation_consistency.py \
  tests/unit/test_presentation_drafts.py \
  tests/unit/test_presentation_reference_analyzer.py \
  tests/unit/test_presentation_translate.py \
  tests/unit/test_proposal_export_formats.py \
  tests/integration/test_presentation_admin.py \
  tests/integration/test_proposals.py \
  tests/integration/test_proposal_cover_export.py -v
```

- [ ] **Step 2: Run web build**

```bash
cd web && npm run build
```

- [ ] **Step 3: Confirm i18n key parity for `admin.presentation` and `proposal` cover keys**

```bash
python - <<'PY'
import json
from pathlib import Path
en=json.loads(Path('web/messages/en.json').read_text())
ja=json.loads(Path('web/messages/ja.json').read_text())

def paths(obj, prefix=''):
    if isinstance(obj, dict):
        for k,v in obj.items():
            yield from paths(v, f'{prefix}.{k}' if prefix else k)
    else:
        yield prefix
en_keys={p for p in paths(en) if p.startswith('admin.presentation') or p.startswith('proposal.')}
ja_keys={p for p in paths(ja) if p.startswith('admin.presentation') or p.startswith('proposal.')}
print('missing in ja', sorted(en_keys-ja_keys)[:50])
print('missing in en', sorted(ja_keys-en_keys)[:50])
assert en_keys==ja_keys
print('parity ok', len(en_keys))
PY
```

---

## Spec coverage checklist

| Spec requirement | Task |
|------------------|------|
| Unified Admin / Presentation | 9, 10 |
| AI reference generation + vision fallback | 5, 7 |
| Persistent drafts + 30-day cleanup | 1, 4 |
| Cover on Template + assets/controls | 1, 2, 10 |
| A4 default page setup | 1, 3, 8 |
| Header-driven locale / bilingual activate | 6, 9, 10 |
| Deterministic consistency recommendations | 2, 10 |
| Proposal consumption + export cover/locale | 8, 11 |
| No admin export actions | 7, 9 |
| Phase 1 excludes Estimates | all tasks |

## Out of this plan (Phase 2)

Estimate report/quotation/dossier/spreadsheet presentation wiring — see `docs/superpowers/plans/2026-07-26-presentation-presets-cover-phase2.md`.
