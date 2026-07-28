# Cover Accent Shapes and Document Theme Accents Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Replace the broken single Cover accent stripe with editable SVG-compatible shape layers and apply Theme accent consistently throughout Proposal and Estimate exports.

**Architecture:** A validated dictionary model represents accent shapes across the API, Admin canvas, HTML/PDF, and DOCX. Backend code normalizes shapes, converts legacy stripes, resolves Theme-linked colors, and produces deterministic safe SVG. The frontend uses the existing normalized geometry engine and native pointer interactions, while export templates consume the shared rendered SVG.

**Tech Stack:** FastAPI/Python, Jinja2, WeasyPrint, CairoSVG, python-docx, Next.js/React, TypeScript, native pointer events, SVG, next-intl, pytest, Node test runner with `tsx`.

## Global Constraints

- Supported shapes: rectangle, line, circle, ellipse, triangle, polygon.
- Supported fills: Theme accent, custom solid, linear gradient, radial gradient.
- Supported patterns: none, stripes, dots, grid, diagonal hatch.
- No raw SVG, HTML, CSS, script, URL, or event-handler input.
- Theme-linked shape colors update with Theme accent; custom colors remain independent.
- No fixed shape-count limit; warn after 50 shapes.
- Legacy `cover_design.accent` remains readable and becomes a left-edge rectangle.
- PDF is the exact-layout reference; DOCX degrades without failing export.
- Strict English/Japanese key parity.
- No in-panel locale selector.
- Do not commit unless explicitly requested.
- Follow safe import-edit rules.

---

### Task 1: Backend accent-shape normalization and legacy conversion

**Files:**
- Create: `api/app/presentation/accent_shapes.py`
- Modify: `api/app/presentation/validators.py`
- Modify: `api/app/presentation/resolver.py`
- Modify: `api/app/presentation/seeds.py`
- Create: `api/tests/unit/test_presentation_accent_shapes.py`
- Modify: `api/tests/unit/test_presentation_validators.py`
- Modify: `api/tests/unit/test_presentation_resolver.py`

**Interfaces:**
- Produces: `normalize_accent_shape(value: Any, seen_ids: set[str]) -> tuple[dict | None, list[str]]`
- Produces: `normalize_accent_shapes(values: Any) -> tuple[list[dict], list[str]]`
- Produces: `legacy_accent_shape(design: dict, page: dict) -> dict | None`
- Produces: `resolve_accent_shapes(design: dict, page: dict) -> tuple[list[dict], list[str]]`
- Extends: `PresentationBundle.accent_warnings: list[str]`

- [x] **Step 1: Write failing normalization tests**

```python
def test_normalize_accent_shape_rejects_raw_markup_and_clamps_values():
    shape, warnings = normalize_accent_shape({
        "id": "shape-1",
        "type": "rectangle",
        "geometry": {"x_pct": -4, "y_pct": 90, "width_pct": 30, "height_pct": 30,
                     "rotation_deg": 999, "z_index": 2000},
        "fill": {"mode": "custom", "color": "url(https://invalid)", "opacity": 2},
    }, set())
    assert shape["geometry"] == {
        "x_pct": 0.0, "y_pct": 90.0, "width_pct": 30.0,
        "height_pct": 10.0, "rotation_deg": 180.0, "z_index": 999,
    }
    assert shape["fill"]["mode"] == "theme"
    assert warnings
```

Cover valid/invalid enums, safe hex colors, finite numbers, duplicate IDs, polygon 3–12 point limits, hidden/locked flags, gradients, borders, and patterns.

- [x] **Step 2: Write failing legacy conversion tests**

```python
def test_legacy_accent_width_becomes_left_rectangle():
    shape = legacy_accent_shape(
        {"accent": {"enabled": True, "width_mm": 21, "opacity": .8}},
        {"size": "A4", "orientation": "portrait"},
    )
    assert shape["type"] == "rectangle"
    assert shape["geometry"]["width_pct"] == 10
    assert shape["geometry"]["height_pct"] == 100
    assert shape["fill"]["mode"] == "theme"
```

- [x] **Step 3: Run tests and confirm RED**

Run:

```bash
docker compose run --rm -v "$PWD/api:/app" api pytest \
  tests/unit/test_presentation_accent_shapes.py \
  tests/unit/test_presentation_validators.py \
  tests/unit/test_presentation_resolver.py -v
```

Expected: import/function failures for the new accent-shape interfaces.

- [x] **Step 4: Implement strict shape normalization**

Use explicit allowlists and safe defaults:

```python
SHAPE_TYPES = {"rectangle", "line", "circle", "ellipse", "triangle", "polygon"}
FILL_MODES = {"theme", "custom", "linear", "radial"}
PATTERN_TYPES = {"none", "stripes", "dots", "grid", "diagonal_hatch"}
BORDER_STYLES = {"solid", "dashed", "dotted"}
```

Normalize each nested structure without preserving unknown keys. Generate a UUID for missing/duplicate unsafe IDs. Preserve `locked`; omit `visible: false` only during export, not draft storage.

- [x] **Step 5: Integrate normalization and legacy resolution**

`clamp_cover_design` normalizes explicit `accent_shapes`. `resolve_presentation` resolves legacy data only when `accent_shapes` is absent, stores canonical shapes in `cover_design["accent_shapes"]`, and carries warnings in `PresentationBundle.accent_warnings`.

- [x] **Step 6: Run focused tests and confirm GREEN**

Expected: all focused tests pass.

---

### Task 2: Deterministic safe SVG renderer

**Files:**
- Modify: `api/app/presentation/accent_shapes.py`
- Create: `api/tests/unit/test_presentation_accent_svg.py`

**Interfaces:**
- Consumes: normalized shapes from Task 1
- Produces: `render_accent_svg(shapes: list[dict], *, theme_accent: str, width_mm: float, height_mm: float) -> str`
- Produces: `visible_accent_shapes(shapes: list[dict]) -> list[dict]`

- [x] **Step 1: Write failing SVG tests**

Assert deterministic `<rect>`, `<line>`, `<circle>`, `<ellipse>`, `<polygon>`, scoped gradient/pattern definitions, center rotation, border styles, layer ordering, hidden omission, and XML escaping.

```python
def test_render_svg_uses_theme_color_and_rotation():
    svg = render_accent_svg([SHAPE], theme_accent="#2563eb", width_mm=210, height_mm=297)
    assert 'fill="#2563eb"' in svg
    assert 'transform="rotate(30 ' in svg
    assert "<script" not in svg
```

- [x] **Step 2: Run test and confirm RED**

Expected: missing renderer failure.

- [x] **Step 3: Implement SVG primitives and generated definitions**

Build XML from validated numeric values using `xml.etree.ElementTree`; never concatenate unvalidated markup. Namespace gradient and pattern IDs with a renderer-level UUID-free deterministic prefix plus escaped shape ID.

- [x] **Step 4: Run SVG and normalization tests**

Expected: all tests pass and repeated renders are byte-identical.

---

### Task 3: Proposal and Estimate HTML/PDF Cover parity

**Files:**
- Modify: `api/app/proposals/export_context.py`
- Modify: `api/app/exports/report_context.py`
- Create: `api/app/exports/templates/_cover_accent_svg.html.j2`
- Modify: `api/app/exports/templates/proposal_pack.html.j2`
- Modify: `api/app/exports/templates/_pdf_base.css.j2`
- Modify: `api/app/exports/templates/estimate_report.html.j2`
- Modify: `api/app/exports/templates/estimate_quotation_formal.html.j2`
- Modify: `api/tests/unit/test_proposal_export_formats.py`
- Modify: `api/tests/unit/test_export_pdf.py`

**Interfaces:**
- Context adds: `cover.accent_svg: str`
- Context adds: `cover.background_color: str`
- Context appends: `PresentationBundle.accent_warnings` to `cover.warnings`

- [x] **Step 1: Write failing Proposal/Estimate HTML tests**

```python
assert 'class="cover-accent-art"' in html
assert 'fill="#2563eb"' in html
assert "background: #f8fafc" in html
```

Cover each shape type, disabled/hidden omission, z-order, safe background fallback, A4/A3/Letter/Legal, and portrait/landscape.

- [x] **Step 2: Run focused export tests and confirm RED**

- [x] **Step 3: Render SVG and safe background in both contexts**

Resolve page dimensions from normalized page settings, pass the presentation Theme accent to `render_accent_svg`, and use safe normalized `colors.background` with Theme primary fallback.

- [x] **Step 4: Add the shared template layer**

```jinja2
{% if ctx.cover.accent_svg %}
<div class="cover-accent-art" aria-hidden="true">{{ ctx.cover.accent_svg | safe }}</div>
{% endif %}
```

The value is marked safe only because it is generated exclusively by Task 2.

- [x] **Step 5: Set consistent layer order**

Background color/image < accent SVG < decorative assets/logo < Cover fields. Ensure SVG occupies the complete printable Cover page.

- [x] **Step 6: Run Proposal and Estimate PDF tests**

Expected: focused suites pass with no layout regressions.

---

### Task 4: DOCX accent rasterization and graceful fallback

**Files:**
- Modify: `api/app/proposals/export_formats.py`
- Modify: `api/app/exports/docx.py`
- Modify: `api/app/proposals/svg_raster.py` only if transparent-page sizing needs a backward-compatible option
- Modify: `api/tests/unit/test_proposal_export_formats.py`
- Modify: `api/tests/unit/test_export_docx.py`

**Interfaces:**
- Consumes: `ctx["cover"]["accent_svg"]`
- Reuses: `svg_to_png_bytes(svg: str, *, scale: float = 1.5) -> bytes | None`

- [x] **Step 1: Write failing DOCX tests**

Verify an accent SVG invokes rasterization, embeds a PNG before Cover text, and rasterization failure still returns a valid DOCX with a warning.

- [x] **Step 2: Run tests and confirm RED**

- [x] **Step 3: Add transparent accent PNG to Proposal and Estimate Cover generation**

Use selected page dimensions and preserve transparency. Do not duplicate SVG interpretation in python-docx.

- [x] **Step 4: Implement fallback**

If rasterization returns `None`, omit decoration, preserve Cover content, and append the existing layout-fidelity warning.

- [x] **Step 5: Run DOCX export tests**

Expected: valid ZIP/DOCX bytes in success and fallback paths.

---

### Task 5: Frontend accent model, geometry, and SVG renderer

**Files:**
- Create: `web/lib/cover-accent-shapes.ts`
- Modify: `web/lib/cover-geometry.ts`
- Create: `web/tests/cover-accent-shapes.test.ts`
- Modify: `web/tests/cover-geometry.test.ts`
- Modify: `web/package.json`

**Interfaces:**
- Produces: `AccentShape`, `AccentFill`, `AccentBorder`, `AccentPattern`
- Produces: `createAccentShape(type, themeAccent)`, `createEdgeStripe(edge, page)`, `duplicateAccentShape(shape)`
- Produces: `accentShapeSvgProps(shape, themeAccent)`, `accentDefinitions(shapes, themeAccent)`
- Extends: `CoverGeometry.rotation_deg`
- Produces: `rotateGeometry(geometry, pointer, bounds)`

- [x] **Step 1: Write failing model/geometry tests**

Cover unique IDs, edge stripe conversion, Theme/custom fills, gradient/pattern IDs, rotation clamping, Shift proportional resize, Alt center resize, and warning threshold.

- [x] **Step 2: Run `npm run test:cover` and confirm RED**

- [x] **Step 3: Implement pure model and geometry helpers**

Keep DOM-free functions in `web/lib` so all behavior is unit-testable.

- [x] **Step 4: Add accent tests to `test:cover`**

```json
"test:cover": "tsx --test tests/cover-geometry.test.ts tests/cover-accent-shapes.test.ts"
```

- [x] **Step 5: Run tests and confirm GREEN**

---

### Task 6: Admin accent-shape panel and canvas interactions

**Files:**
- Create: `web/components/admin/presentation/PresentationAccentShapesPanel.tsx`
- Create: `web/components/admin/presentation/PresentationAccentShapeStyleControls.tsx`
- Create: `web/components/admin/presentation/PresentationAccentShapeSvg.tsx`
- Modify: `web/components/admin/presentation/PresentationCoverDesigner.tsx`
- Modify: `web/components/admin/presentation/PresentationCoverPreview.tsx`
- Modify: `web/app/globals.css`
- Modify: `web/messages/en.json`
- Modify: `web/messages/ja.json`

**Interfaces:**
- Panel consumes `shapes`, selected ID, Theme accent, page, and immutable update callbacks.
- Preview treats `shape:{id}` as a normal selectable layer.
- SVG component renders one validated frontend shape plus generated definitions.

- [x] **Step 1: Replace the legacy accent controls**

Add shape/edge-stripe menus, layer list, name, visibility, lock, duplicate, delete, and reorder controls. Show a non-blocking warning when `shapes.length > 50`.

- [x] **Step 2: Add appearance controls**

Implement Theme/custom/linear/radial fill modes; gradient angle/center/colors; pattern type/color/scale/spacing/opacity; border controls; opacity; radius; reset actions.

- [x] **Step 3: Integrate canvas rendering**

Render shapes as SVG between background and assets. Hidden shapes are absent. Locked shapes render but cannot start pointer or keyboard edits.

- [x] **Step 4: Integrate manipulation**

Reuse drag, resize, snap, keyboard, and z-order paths. Add rotation handle/numeric rotation. Honor Shift proportional resize and Alt center resize.

- [x] **Step 5: Add strict EN/JA keys**

Include shape names, fill modes, pattern names, actions, warnings, controls, and accessible labels.

- [x] **Step 6: Run tests, parity check, and build**

```bash
cd web
npm run test:cover
npm run build
```

Expected: tests and production build pass; EN/JA keys match.

---

### Task 7: Document-wide Theme accent consistency

**Files:**
- Modify: `api/app/presentation/resolver.py`
- Modify: `api/app/exports/templates/proposal_pack.html.j2`
- Modify: `api/app/exports/templates/_export_theme.css.j2`
- Modify: `api/app/exports/templates/_pdf_base.css.j2`
- Modify: `api/app/exports/gantt_svg.py`
- Modify: `api/app/proposals/export_context.py`
- Modify: `api/app/exports/report_context.py`
- Modify: `api/tests/unit/test_export_theme.py`
- Modify: `api/tests/unit/test_gantt_svg.py`
- Modify: `api/tests/unit/test_proposal_ai_and_theme.py`
- Modify focused Proposal/Estimate export tests

**Interfaces:**
- `theme_color_map()["accent"]` is the canonical document accent.
- `chart`, `callout`, and table-highlight tokens fall back to canonical accent when not explicitly configured.

- [x] **Step 1: Write failing Theme accent tests**

Assert Theme accent controls section rules, callout bars, table highlight details, chart highlights, and TOC markers in Proposal and Estimate outputs.

- [x] **Step 2: Run tests and confirm RED**

- [x] **Step 3: Normalize Theme fallback semantics**

Preserve explicit specialized tokens; otherwise derive chart/callout/table-highlight values from Theme accent.

- [x] **Step 4: Update CSS and chart rendering**

Use `--accent` / `--export-accent` for the approved targets without changing body text, primary brand color, or custom shape fills. Pass the resolved accent into Gantt/chart rendering instead of using a module constant.

- [x] **Step 5: Run Theme and export tests**

Expected: all focused tests pass.

---

### Task 8: Full verification and review

**Files:**
- Modify this plan to mark completed tasks.

- [x] **Step 1: Run complete frontend verification**

```bash
cd web
npm run test:cover
npm run build
```

- [x] **Step 2: Run focused API verification**

```bash
docker compose run --rm -v "$PWD/api:/app" api pytest \
  tests/unit/test_presentation_accent_shapes.py \
  tests/unit/test_presentation_accent_svg.py \
  tests/unit/test_presentation_validators.py \
  tests/unit/test_presentation_resolver.py \
  tests/unit/test_proposal_export_formats.py \
  tests/unit/test_export_pdf.py \
  tests/unit/test_export_theme.py \
  tests/unit/test_proposal_ai_and_theme.py -v
```

- [x] **Step 3: Run presentation integration tests**

```bash
docker compose run --rm -v "$PWD/api:/app" api pytest \
  tests/integration/test_presentation_admin.py \
  tests/integration/test_proposal_cover_export.py -v
```

- [x] **Step 4: Verify EN/JA parity and IDE lints**

Expected: no missing keys and no new diagnostics.

- [x] **Step 5: Review the combined implementation**

Review security, malformed shape handling, legacy compatibility, preview/export parity, stale selection, locking/visibility, unlimited shape performance, and DOCX fallback. Fix all Critical and Important findings, then rerun affected tests.

- [x] **Step 6: Manual smoke checklist**

- Create each shape type.
- Add all four edge-stripe presets.
- Drag, resize, rotate, snap, reorder, lock, hide, duplicate, and delete.
- Apply Theme, custom, linear, radial, border, and each pattern.
- Change Theme accent and confirm linked-only updates.
- Save/reload the draft.
- Export Proposal and Estimate PDF/DOCX.
- Confirm the disabled Cover remains excluded from export.
