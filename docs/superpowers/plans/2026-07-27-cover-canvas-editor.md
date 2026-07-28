# Cover Canvas Drag, Resize & Text Styling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans task-by-task. Steps use checkbox syntax.

**Goal:** Add direct drag/resize interaction, optional snapping, synchronized geometry values, full per-field text styling, and a non-blocking disabled-Cover state to Admin / Presentation.

**Architecture:** Store normalized geometry and text style inside existing Template `cover_fields` and asset JSON. Use pure TypeScript geometry functions for pointer math and snapping, native pointer events for the editor, and extend backend resolution/rendering so PDF/web honor the same geometry. Legacy fields without geometry retain ordered layout.

**Tech Stack:** Next.js/React pointer events, TypeScript, Node test runner via `tsx`, FastAPI/Python validation, Jinja/WeasyPrint, python-docx.

## Global constraints

- Native pointer events; no drag/resize UI dependency.
- Movement is free by default; Snap is optional.
- Coordinates are normalized percentages and clamped to page bounds.
- Background remains pan/zoom/fit controlled and is not freely rotated.
- Full per-field text style set; Japanese-safe font fallbacks required.
- Disabled Cover remains editable but excluded from exports.
- Existing fields/assets remain backward compatible.
- No in-panel language selector; strict EN/JA key parity.
- Do not commit unless explicitly requested.
- Follow safe import-edit rules.

---

### Task 1: Backend geometry/style normalization and resolution

**Files:**
- Modify: `api/app/presentation/validators.py`
- Modify: `api/app/presentation/cover.py`
- Modify: `api/tests/unit/test_presentation_validators.py`
- Modify: `api/tests/unit/test_presentation_cover_resolver.py`

**Produces:**
- `normalize_cover_geometry(value) -> dict | None`
- `normalize_cover_text_style(value) -> dict`
- resolved Cover fields preserve normalized `geometry` and `style`

- [x] Write failing tests for finite-value checks, percent clamping, font/style clamping, legacy fields without geometry, and resolved geometry/style passthrough.
- [x] Run targeted tests and confirm failure.
- [x] Implement normalization:

```python
geometry = {
    "x_pct": clamp(x, 0, 100),
    "y_pct": clamp(y, 0, 100),
    "width_pct": clamp(width, 1, 100),
    "height_pct": clamp(height, 1, 100) if present,
    "z_index": clamp_int(z, 0, 999),
}
```

Text style clamps font size, weight, line height, letter spacing, opacity, padding, color, alignment.
- [x] Run tests and confirm pass.

---

### Task 2: Pure frontend geometry engine with TDD

**Files:**
- Create: `web/lib/cover-geometry.ts`
- Create: `web/tests/cover-geometry.test.ts`
- Modify: `web/package.json`
- Modify: `web/package-lock.json`

**Produces:**
- `pointToPercent`
- `moveGeometry`
- `resizeGeometry`
- `snapGeometry`
- `keyboardMove`
- `normalizeGeometry`

- [x] Install the current `tsx` dev dependency using npm and add `test:cover`.
- [x] Write failing Node tests for conversion, boundary clamp, free movement, 2% grid snapping, center/edge guides, resize math, and keyboard increments.
- [x] Run `npm run test:cover` and confirm failure.
- [x] Implement pure functions without DOM dependencies.
- [x] Run `npm run test:cover` and confirm pass.

---

### Task 3: Direct-manipulation preview canvas

**Files:**
- Modify: `web/components/admin/presentation/PresentationCoverPreview.tsx`
- Modify: `web/components/admin/presentation/PresentationCoverDesigner.tsx`
- Modify: `web/app/globals.css`

**Interfaces:**
- Preview receives selected layer ID, snap state, and callbacks for geometry updates.
- Designer owns selection and persists updated fields/assets.

- [x] Add selectable layer model for positioned text fields, logo, and decorative image.
- [x] Implement pointer capture drag:
  - capture start geometry and page bounds;
  - convert pointer delta to percentages;
  - optionally snap;
  - update state continuously.
- [x] Add eight resize handles and synchronized HUD (`X`, `Y`, `W`, `H`).
- [x] Add visible snap guides and a Snap toggle.
- [x] Add keyboard movement and Escape clear-selection behavior.
- [x] Add z-order actions in selected-layer controls.
- [x] Preserve automatic stacked rendering for fields without geometry.
- [x] Run `npm run test:cover` and `npm run build`.

---

### Task 4: Full per-field text styling controls

**Files:**
- Modify: `web/components/admin/presentation/PresentationCoverPreview.tsx`
- Modify: `web/components/admin/presentation/PresentationCoverFieldList.tsx`
- Create: `web/components/admin/presentation/PresentationTextStyleControls.tsx`
- Modify: `web/components/admin/presentation/PresentationCoverDesigner.tsx`
- Modify: `web/messages/en.json`
- Modify: `web/messages/ja.json`

**Per-field controls:**
- font family, size, weight, italic
- color, alignment
- line height, letter spacing, opacity
- geometry values and z-index
- optional background color and padding

- [x] Extend `CoverField` TypeScript type with geometry/style.
- [x] Add selected-field side panel and synchronized values.
- [x] Render per-field styles in preview.
- [x] Treat Proposal title as the first standard Cover field with the same controls.
- [x] Add “Reset to automatic layout”.
- [x] Add EN/JA keys with parity.
- [x] Run test/build.

---

### Task 5: Disabled Cover preview behavior

**Files:**
- Modify: `web/components/admin/presentation/PresentationCoverPreview.tsx`
- Modify: `web/components/admin/presentation/PresentationCoverDesigner.tsx`
- Modify: `web/messages/en.json`
- Modify: `web/messages/ja.json`

- [x] Remove blocking disabled overlay.
- [x] Show non-blocking badge above preview: “Disabled — not included in exports”.
- [x] Add Enable cover action.
- [x] Keep canvas interactive while disabled.
- [x] Verify export inclusion remains controlled by existing Template/default/override logic.
- [x] Run web test/build.

---

### Task 6: PDF/DOCX geometry and text-style rendering

**Files:**
- Modify: `api/app/exports/templates/proposal_pack.html.j2`
- Modify: `api/app/proposals/export_formats.py`
- Modify: `api/tests/unit/test_proposal_export_formats.py`
- Modify Estimate templates/export adapters only where they consume the shared Cover model.

- [x] Write failing tests asserting positioned field CSS and field-specific typography.
- [x] Update Jinja:

```jinja2
{% if field.geometry %}
style="position:absolute;
 left:{{ field.geometry.x_pct }}%;
 top:{{ field.geometry.y_pct }}%;
 width:{{ field.geometry.width_pct }}%;
 z-index:{{ field.geometry.z_index }};"
{% endif %}
```

- [x] Apply font family/size/weight/italic/color/alignment/line-height/letter-spacing/opacity/background/padding.
- [x] Keep legacy ordered `.cover-content` output for fields without geometry.
- [x] Map closest supported styles/positioning in DOCX and add warning metadata where exact layout is unavailable.
- [x] Run proposal and Estimate export tests.

---

### Task 7: Verification

- [x] `cd web && npm run test:cover`
- [x] `cd web && npm run build`
- [x] Run focused API tests:

```bash
docker compose run --rm -v "$(pwd)/api:/app" api pytest \
  tests/unit/test_presentation_validators.py \
  tests/unit/test_presentation_cover_resolver.py \
  tests/unit/test_proposal_export_formats.py \
  tests/unit/test_export_pdf.py -v
```

- [x] Verify EN/JA presentation-key parity.
- [x] Check IDE lints for edited files.
- [x] Manually smoke: disabled Cover stays editable; drag with Snap off/on; resize; change per-field font/style; save/reload; PDF preview.
