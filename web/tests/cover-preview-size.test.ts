import assert from "node:assert/strict";
import test from "node:test";

import {
  COVER_PAGE_MM,
  COVER_PREVIEW_MAX_HEIGHT_VH,
  COVER_PREVIEW_MAX_WIDTH_REM,
  computeCoverPreviewBox,
  coverPageDimensions,
  coverPreviewWidthCss,
} from "../lib/cover-preview-size";

const A4_PORTRAIT = coverPageDimensions("A4", "portrait");
const A4_LANDSCAPE = coverPageDimensions("A4", "landscape");

// Representative short laptop viewports (CSS px). Container width is generous so
// the height cap is the binding constraint for portrait pages.
const VIEWPORTS = [
  { label: "1366x768", width: 1366, height: 768 },
  { label: "1536x864", width: 1536, height: 864 },
  { label: "1440x900", width: 1440, height: 900 },
];

function ratio(dimensions: readonly [number, number]): number {
  return dimensions[0] / dimensions[1];
}

test("Letter and Legal use 215.9 mm width to match the backend", () => {
  assert.deepEqual(COVER_PAGE_MM.Letter, [215.9, 279.4]);
  assert.deepEqual(COVER_PAGE_MM.Legal, [215.9, 355.6]);
});

test("coverPageDimensions swaps width and height for landscape", () => {
  assert.deepEqual(coverPageDimensions("A4", "portrait"), [210, 297]);
  assert.deepEqual(coverPageDimensions("A4", "landscape"), [297, 210]);
  assert.deepEqual(coverPageDimensions("unknown", "portrait"), [210, 297]);
});

test("preview box preserves portrait aspect ratio on short viewports", () => {
  for (const viewport of VIEWPORTS) {
    const box = computeCoverPreviewBox(A4_PORTRAIT, {
      containerWidthPx: 640,
      viewportHeightPx: viewport.height,
    });
    const maxHeight = (viewport.height * COVER_PREVIEW_MAX_HEIGHT_VH) / 100;
    assert.ok(
      Math.abs(box.widthPx / box.heightPx - ratio(A4_PORTRAIT)) < 1e-9,
      `${viewport.label} portrait aspect preserved`,
    );
    assert.ok(box.heightPx <= maxHeight + 1e-9, `${viewport.label} within 68vh`);
    assert.ok(box.widthPx <= COVER_PREVIEW_MAX_WIDTH_REM * 16 + 1e-9, `${viewport.label} within 32rem`);
    // On these short viewports the height cap binds, so width shrinks below 32rem.
    assert.ok(box.widthPx < COVER_PREVIEW_MAX_WIDTH_REM * 16, `${viewport.label} width shrank`);
  }
});

test("preview box preserves landscape aspect ratio and caps width at 32rem", () => {
  for (const viewport of VIEWPORTS) {
    const box = computeCoverPreviewBox(A4_LANDSCAPE, {
      containerWidthPx: 640,
      viewportHeightPx: viewport.height,
    });
    const maxHeight = (viewport.height * COVER_PREVIEW_MAX_HEIGHT_VH) / 100;
    assert.ok(
      Math.abs(box.widthPx / box.heightPx - ratio(A4_LANDSCAPE)) < 1e-9,
      `${viewport.label} landscape aspect preserved`,
    );
    assert.ok(box.heightPx <= maxHeight + 1e-9, `${viewport.label} within 68vh`);
    assert.equal(box.widthPx, COVER_PREVIEW_MAX_WIDTH_REM * 16);
  }
});

test("preview box is limited by container width when narrow", () => {
  const box = computeCoverPreviewBox(A4_PORTRAIT, {
    containerWidthPx: 240,
    viewportHeightPx: 900,
  });
  assert.equal(box.widthPx, 240);
  assert.ok(Math.abs(box.widthPx / box.heightPx - ratio(A4_PORTRAIT)) < 1e-9);
});

test("coverPreviewWidthCss caps width by 100%, 32rem, and the 68vh height limit", () => {
  assert.equal(
    coverPreviewWidthCss(A4_PORTRAIT),
    "min(100%, 32rem, 48.080808vh)",
  );
  // Landscape ratio > 1 so the vh-derived cap exceeds 68vh, letting 32rem bind.
  assert.equal(
    coverPreviewWidthCss(A4_LANDSCAPE),
    "min(100%, 32rem, 96.171429vh)",
  );
});
