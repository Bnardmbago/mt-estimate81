# Cover Accent Shapes and Document Theme Accents Design

## Goal

Replace the broken single Cover stripe with a reusable decorative shape system. Shapes must be directly editable on the Cover canvas, render consistently in Proposal and Estimate exports, and inherit the Theme accent color by default. The Theme accent must also have consistent meaning throughout exported documents.

## Current Problems

1. The preview computes accent width as `max(1, width / pageWidth) * 100`, which forces ordinary values to 100% and makes Accent color look like Background color.
2. Proposal PDF export does not render the Cover accent.
3. Proposal PDF export ignores `cover_design.colors.background`.
4. Estimate Cover exports use a separate legacy background property.
5. The backend does not normalize the existing accent configuration.
6. One fixed stripe cannot represent common branded Cover decorations.
7. Theme accent usage differs between export formats and document sections.

## Scope

This release includes:

- Multiple Cover accent shapes with no fixed count limit.
- Rectangle, line, circle, ellipse, triangle, and polygon shapes.
- Direct drag, resize, rotation, snapping, ordering, visibility, locking, duplication, and deletion.
- Solid, linear-gradient, and radial-gradient fills.
- Borders and built-in stripes, dots, grid, and diagonal-hatch patterns.
- Theme-linked colors with per-shape overrides.
- Legacy edge stripe conversion.
- Proposal and Estimate preview/PDF/DOCX rendering.
- Consistent Theme accent use for section rules, callouts, table highlights, chart accents, and TOC markers.

Raw SVG uploads and arbitrary CSS are not supported.

## Architecture

### Unified shape model

Accent shapes are first-class Cover canvas layers alongside text and image layers. The existing geometry engine remains responsible for normalized page coordinates, snapping, keyboard movement, resizing, and z-order.

Shape appearance is represented as validated data and rendered through one SVG-compatible model:

- React renders the model in the Admin preview.
- Jinja exports equivalent inline SVG for HTML/PDF.
- DOCX rasterizes the same SVG decoration layer to a transparent PNG when exact native drawing placement is unavailable.

This avoids separate visual implementations for every shape and export format.

### Canonical configuration

```json
{
  "colors": {
    "background": "#ffffff",
    "accent": "#2563eb"
  },
  "accent_shapes": [
    {
      "id": "accent-uuid",
      "name": "Left stripe",
      "type": "rectangle",
      "visible": true,
      "locked": false,
      "geometry": {
        "x_pct": 0,
        "y_pct": 0,
        "width_pct": 12,
        "height_pct": 100,
        "rotation_deg": 0,
        "z_index": 1
      },
      "fill": {
        "mode": "theme",
        "color": null,
        "opacity": 0.9
      },
      "border": {
        "enabled": false,
        "color": "#2563eb",
        "width_pt": 0,
        "style": "solid",
        "radius_pct": 0
      },
      "pattern": {
        "type": "none",
        "color": "#ffffff",
        "scale": 1,
        "spacing": 1,
        "opacity": 0.25
      }
    }
  ]
}
```

### Shape-specific data

- `line`: line thickness and optional end-cap style.
- `circle`: equal width and height enforced by default.
- `ellipse`: independent width and height.
- `triangle`: normalized three-point path.
- `polygon`: validated normalized point list with 3–12 vertices.
- `rectangle`: optional corner radius.

All shape types share geometry, fill, border, pattern, visibility, locking, and layer-order behavior.

## Backward Compatibility

Existing `cover_design.accent` data is converted at resolution time when `accent_shapes` is absent:

- `enabled: false` produces no shape.
- `width_mm` or `thickness_mm` becomes the width of a left-edge rectangle.
- Legacy color resolves from `colors.accent`, then Theme accent.
- Legacy opacity defaults to `0.9`.
- Existing presets remain readable without a database migration because Template configuration is JSON.
- Saving an edited legacy Cover writes canonical `accent_shapes`.

The original width-calculation bug is removed as part of conversion.

## Admin User Experience

### Accent shapes panel

The Cover designer adds an **Accent shapes** panel:

- **Add shape**: Rectangle, Line, Circle, Ellipse, Triangle, Polygon.
- **Add edge stripe**: Left, Right, Top, Bottom presets.
- Layer list with editable name, visibility, lock, duplicate, delete, and drag-to-reorder.
- A soft performance warning appears after 50 shapes; there is no hard limit.

Selecting a row selects the matching canvas layer and vice versa.

### Direct manipulation

Unlocked, visible shapes support:

- Drag to move.
- Eight resize handles.
- A rotation handle plus numeric rotation input.
- Optional snapping and visible guides.
- Live X, Y, width, height, and rotation values.
- Shift-resize to preserve proportions.
- Alt-resize from the center.
- Arrow movement of 0.25%; Shift+Arrow movement of 1%.
- Bring forward, send backward, bring to front, and send to back.

Locked shapes remain visible and export normally but cannot be changed until unlocked. Hidden shapes are omitted from preview output and exports.

### Appearance controls

Selected-shape controls include:

- Fill mode: Theme accent, custom solid, linear gradient, radial gradient.
- Linear/radial gradient start and end colors.
- Linear gradient angle.
- Radial gradient center.
- Pattern: None, Stripes, Dots, Grid, Diagonal hatch.
- Pattern color, scale, spacing, and opacity.
- Border enabled, color, width, and solid/dashed/dotted style.
- Shape opacity.
- Corner radius where applicable.
- Reset style and reset geometry.

Theme-linked shapes update immediately when the Theme accent changes. Applying a custom fill detaches only that shape from Theme color updates.

## Cover Rendering

### Layer order

Default order is:

1. Cover background color.
2. Cover background image.
3. Accent shapes, ordered by `z_index`.
4. Decorative image and logo layers.
5. Cover text fields.
6. Editor-only selection controls and guides.

Users may change z-order across editable Cover layers, while the page background remains fixed.

### SVG rendering

Each shape maps to safe SVG primitives:

- Rectangle: `<rect>`
- Line: `<line>`
- Circle: `<circle>`
- Ellipse: `<ellipse>`
- Triangle and polygon: `<polygon>`

Gradients and patterns use generated, shape-ID-scoped `<defs>`. Rotation is applied around the shape center. The renderer receives normalized, validated values only.

## Export Rendering

### HTML/PDF

Proposal and Estimate Cover templates:

- Use `cover_design.colors.background`, falling back to Theme primary.
- Render a full-page accent SVG behind Cover content.
- Use the same geometry, fill, gradients, patterns, borders, rotation, opacity, visibility, and z-order as the Admin preview.
- Render foreground assets and Cover fields above the decoration SVG.

PDF is the exact-layout reference format.

### DOCX

The accent renderer creates a transparent PNG from the shared SVG model using the existing SVG rasterization support. The PNG is sized to the selected page and placed as the Cover decoration layer where the document library supports it.

If background placement is not stable in a supported DOCX environment, the export uses a full-page decoration image within the Cover flow and emits the existing layout-fidelity warning. Content and export generation must not fail solely because accent rasterization fails.

## Document-Wide Theme Accent

Theme accent remains a Theme token, separate from per-Cover shape overrides. Proposal and Estimate exports use it consistently for:

- Section heading rules.
- Callout borders or highlight bars.
- Table header/highlight details.
- Chart series highlights.
- Table-of-contents markers.

Changing Theme accent updates these document elements and all Theme-linked Cover shapes. It does not change Background, body text, primary brand color, or custom-colored shapes.

## Validation and Security

Backend normalization:

- Requires a stable safe ID and supported shape type.
- Validates finite geometry and clamps coordinates, dimensions, rotation, and z-index.
- Accepts only safe hexadecimal colors.
- Accepts only supported fill, border, and pattern enums.
- Clamps opacity, border width, radius, gradient positions, pattern scale, and spacing.
- Validates polygon points and limits each polygon to 3–12 vertices.
- Omits malformed shapes and returns non-blocking warnings.
- Excludes hidden shapes from export output.
- Does not accept raw SVG, HTML, CSS, URLs, external paint servers, scripts, or event handlers.

Generated SVG identifiers are escaped and namespaced per export to prevent collisions.

## Internationalization

All new UI labels, messages, shape names, position names, pattern names, fill modes, actions, warnings, and accessibility labels require matching English and Japanese keys. Locale selection remains in the global header.

## Error Handling

- Invalid individual shapes are omitted; valid shapes continue rendering.
- Rasterization failure falls back to a Cover without the decoration layer and adds an export warning.
- Unsupported legacy accent values fall back to a left Theme-accent stripe.
- Empty shape arrays render only the Cover background and other Cover layers.
- Duplicate IDs are regenerated when a shape is duplicated or normalized.

## Testing

### Frontend

- Shape creation, duplication, deletion, visibility, locking, and ordering.
- Drag, resize, proportional resize, center resize, rotation, snapping, and keyboard movement.
- All SVG primitive mappings.
- Solid, Theme-linked, linear, and radial fills.
- All supported patterns and border styles.
- Legacy stripe conversion and corrected thickness calculation.
- Theme color updates versus custom overrides.
- Soft performance warning.
- EN/JA key parity and production build.

### Backend

- Shape normalization, finite-number handling, bounds, enums, safe colors, polygon limits, and duplicate IDs.
- Legacy accent conversion.
- Hidden/malformed shape omission and warnings.
- Safe deterministic SVG generation without raw markup injection.

### Exports

- Proposal and Estimate HTML/PDF shape parity for every type.
- Gradients, patterns, borders, rotation, opacity, and layer order.
- Cover background parity.
- DOCX SVG rasterization and fallback.
- Document-wide Theme accent targets.
- Existing presentation and export regression suites.
