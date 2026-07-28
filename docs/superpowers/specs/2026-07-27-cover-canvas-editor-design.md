# Cover Canvas Drag, Resize & Text Styling — Design

**Date:** 2026-07-27  
**Status:** Approved

## Goal

Upgrade Admin / Presentation → Cover design from slider-only asset placement and fixed text regions to a direct-manipulation canvas. Admins can freely drag and resize logos, images, the Proposal title, and custom text fields while exact values remain visible and editable.

## Decisions (locked)

| Decision | Choice |
|----------|--------|
| Interaction | Native pointer events; no drag/resize dependency |
| Movement | Free movement with an optional Snap toggle |
| Snapping | Light grid plus page-edge, center, and peer-element alignment guides |
| Resize | Direct resize handles for text boxes, logos, and images |
| Coordinates | Normalized page percentages (`x`, `y`, `width`, `height`) |
| Values | Side-panel inputs and a compact selection HUD update during drag/resize |
| Text styling | Full per-field controls |
| Disabled Cover | Editable preview remains visible; non-blocking disabled badge replaces overlay |
| Backward compatibility | Fields without geometry retain the current ordered stacked layout |
| Export fidelity | Web/PDF exact; DOCX closest supported approximation with warning |

## Current behavior and root cause

- Assets currently expose X/Y, zoom, opacity, rotation, fit, and position controls, but `PresentationCoverPreview` has no pointer handlers. The preview cannot drag or resize elements.
- Cover text fields currently store only localized label/default text, required state, and auto-fill. Typography is global (`title_pt`, `metadata_pt`), and text geometry is fixed.
- “Cover disabled” is rendered as a blocking preview overlay whenever the selected Template resolves `cover: false`. The design still renders underneath.

## Element model

Every movable Cover item is a layer:

```ts
type CoverGeometry = {
  x_pct: number;
  y_pct: number;
  width_pct: number;
  height_pct?: number;
  z_index: number;
};

type CoverTextStyle = {
  font_family?: string;
  font_size_pt: number;
  font_weight: 300 | 400 | 500 | 600 | 700 | 800 | 900;
  italic?: boolean;
  color: string;
  text_align: "left" | "center" | "right";
  line_height: number;
  letter_spacing_em: number;
  opacity: number;
  background_color?: string;
  padding_mm?: number;
};
```

Each `cover_fields[]` entry gains:

```ts
{
  key,
  content: {_i18n: {...}},
  required,
  auto_fill,
  geometry?: CoverGeometry,
  style?: CoverTextStyle
}
```

Assets use equivalent normalized geometry. Background images keep their existing pan/zoom/fit model and do not become freely rotated page layers.

## Interaction model

### Selection

- Clicking an element selects it and shows a bounding box, corner/edge resize handles, and a small HUD.
- Clicking empty canvas or pressing Escape clears selection.
- The side panel switches to controls for the selected layer.

### Dragging

- Pointer down captures the pointer; movement is converted from preview pixels into page percentages.
- X/Y values update continuously in both HUD and side panel.
- Elements are clamped within page bounds.
- Arrow keys move by 0.25%; Shift+Arrow moves by 1%.

### Resizing

- Corner handles resize proportionally by default for assets.
- Shift permits free aspect ratio for non-background assets.
- Text boxes resize width/height without changing font size.
- Width/height values update continuously.

### Snapping

- Snap is an editor toggle and does not affect exports directly.
- When enabled, movement snaps to a 2% grid and to page/element guides within a small threshold.
- Final normalized coordinates are stored; the toggle itself is local editor preference.
- Visible guides disappear when the interaction ends.

### Layer operations

- Bring forward, send backward, bring to front, and send to back update `z_index`.
- Delete/Backspace removes selected logo/decorative image; text-field deletion requires confirmation.
- Proposal title is a standard Cover field and uses the same interaction/style model.

## Per-field text controls

The selected text field exposes:

- Font family and locale-safe fallback
- Font size (pt)
- Weight and italic
- Text color
- Left/center/right alignment
- Line height
- Letter spacing
- Opacity
- X/Y/width/height
- Layer order
- Optional background color and padding

All controls update the preview immediately. Japanese-capable fallback fonts remain mandatory.

## Disabled Cover behavior

- Remove the blocking “Cover disabled” overlay.
- Keep the design fully visible and editable.
- Show a small badge above the preview: **Disabled — not included in exports**.
- Show an **Enable cover** action beside the badge.
- Disabling controls export inclusion only and never deletes Cover design data.
- Preserve the three states: Template default, explicitly enabled, explicitly disabled.

## Backward compatibility

- Existing fields with no `geometry` continue rendering in the current ordered stacked content region.
- Once a field is dragged/resized, geometry is created and that field becomes an absolute-position layer.
- Existing asset `x`/`y`/`zoom` values are normalized into geometry at editor load without requiring a migration.
- A reset action can return a field to automatic ordered layout.

## Rendering

- Admin preview and Proposal web preview use the same normalized geometry and style mapping.
- PDF converts normalized percentages to CSS absolute positioning within the selected page size.
- DOCX maps styles and uses the closest available positioning primitives; exact-parity limitations are added to export warnings.
- MD/XLSX remain ordered metadata equivalents.
- Page-size/orientation changes preserve normalized placement.

## Validation and testing

- Clamp coordinates, dimensions, opacity, font sizes, line height, letter spacing, and layer order.
- Reject non-finite values.
- Test pure geometry functions: pixel→percent conversion, clamping, snapping, resize math, z-order.
- Test backward fallback for fields without geometry.
- Test disabled Cover preview remains editable while export excludes it.
- Test PDF absolute position/style output and A4 portrait/landscape scaling.
- Run strict EN/JA key parity and production web build.

## Success criteria

1. Admin can drag and resize text, logos, and decorative images directly.
2. Optional snapping provides grid and alignment guides.
3. Numeric geometry values remain synchronized during interaction.
4. Each text field supports the full approved style set.
5. Disabled Cover no longer blocks editing and remains excluded from exports.
6. Existing Cover configurations render unchanged until directly positioned.
7. Web/PDF honor normalized geometry across supported paper sizes.
