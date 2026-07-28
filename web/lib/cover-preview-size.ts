/**
 * Page dimensions and preview-box sizing for the cover designer.
 *
 * The rendered preview box must always preserve the page aspect ratio while
 * respecting a maximum width (32rem) and a maximum height (68vh). Clamping
 * height independently of width breaks the aspect ratio on short laptop
 * viewports, so the width itself is capped by the height-derived limit.
 */

export type PageOrientation = "portrait" | "landscape";

/** Millimetre page sizes, matching the backend `PAGE_DIMENSIONS_MM`. */
export const COVER_PAGE_MM: Record<string, [number, number]> = {
  A3: [297, 420],
  A4: [210, 297],
  Letter: [215.9, 279.4],
  Legal: [215.9, 355.6],
};

export const COVER_PREVIEW_MAX_WIDTH_REM = 32;
export const COVER_PREVIEW_MAX_HEIGHT_VH = 68;

/** Resolve oriented page dimensions in millimetres. */
export function coverPageDimensions(
  size: string,
  orientation: PageOrientation,
): [number, number] {
  const base = COVER_PAGE_MM[size] || COVER_PAGE_MM.A4;
  return orientation === "landscape" ? [base[1], base[0]] : base;
}

/**
 * CSS width expression that keeps the box within 100% of its container, 32rem,
 * and the width implied by the 68vh height cap for the given page aspect. Paired
 * with `aspect-ratio`, the resulting height never exceeds 68vh.
 */
export function coverPreviewWidthCss(dimensions: readonly [number, number]): string {
  const ratio = dimensions[0] / dimensions[1];
  const heightCappedWidthVh = COVER_PREVIEW_MAX_HEIGHT_VH * ratio;
  return `min(100%, ${COVER_PREVIEW_MAX_WIDTH_REM}rem, ${formatNumber(heightCappedWidthVh)}vh)`;
}

export type CoverPreviewViewport = {
  containerWidthPx: number;
  viewportHeightPx: number;
  remPx?: number;
};

/**
 * Compute the actual rendered box size in pixels for a viewport. Mirrors the
 * CSS `min()` math so it can be asserted in tests: width is the smallest of the
 * container width, 32rem, and the height-derived width; height follows the page
 * aspect ratio and is therefore always <= 68vh.
 */
export function computeCoverPreviewBox(
  dimensions: readonly [number, number],
  viewport: CoverPreviewViewport,
): { widthPx: number; heightPx: number } {
  const ratio = dimensions[0] / dimensions[1];
  const rem = viewport.remPx ?? 16;
  const maxWidth = Math.min(
    viewport.containerWidthPx,
    COVER_PREVIEW_MAX_WIDTH_REM * rem,
  );
  const maxHeight = (viewport.viewportHeightPx * COVER_PREVIEW_MAX_HEIGHT_VH) / 100;
  const widthPx = Math.min(maxWidth, maxHeight * ratio);
  return { widthPx, heightPx: widthPx / ratio };
}

function formatNumber(value: number): string {
  if (Math.abs(value) < 0.0000005) return "0";
  return value.toFixed(6).replace(/\.?0+$/, "");
}
