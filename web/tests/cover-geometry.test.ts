import assert from "node:assert/strict";
import test from "node:test";

import {
  keyboardMove,
  moveGeometry,
  normalizeGeometry,
  pointToPercent,
  resizeGeometry,
  rotateGeometry,
  snapGeometry,
  type CoverGeometry,
} from "../lib/cover-geometry";

const geometry = (
  overrides: Partial<CoverGeometry> = {},
): CoverGeometry => ({
  x_pct: 10,
  y_pct: 20,
  width_pct: 30,
  height_pct: 20,
  z_index: 2,
  ...overrides,
});

test("pointToPercent converts canvas coordinates and clamps to the page", () => {
  assert.deepEqual(
    pointToPercent(
      { x: 250, y: 350 },
      { left: 50, top: 150, width: 400, height: 400 },
    ),
    { x_pct: 50, y_pct: 50 },
  );
  assert.deepEqual(
    pointToPercent(
      { x: 500, y: 100 },
      { left: 50, top: 150, width: 400, height: 400 },
    ),
    { x_pct: 100, y_pct: 0 },
  );
});

test("normalizeGeometry rejects non-finite values and clamps inside the page", () => {
  assert.deepEqual(
    normalizeGeometry({
      x_pct: Number.NaN,
      y_pct: Number.NEGATIVE_INFINITY,
      width_pct: Number.POSITIVE_INFINITY,
      height_pct: -4,
      z_index: Number.NaN,
    }),
    {
      x_pct: 0,
      y_pct: 0,
      width_pct: 1,
      height_pct: 1,
      z_index: 0,
    },
  );
  assert.deepEqual(
    normalizeGeometry({
      x_pct: 95,
      y_pct: 90,
      width_pct: 20,
      height_pct: 30,
      z_index: 1200,
    }),
    {
      x_pct: 80,
      y_pct: 70,
      width_pct: 20,
      height_pct: 30,
      z_index: 999,
    },
  );
});

test("normalizeGeometry clamps rotation without changing unrotated geometry", () => {
  assert.deepEqual(normalizeGeometry(geometry()), geometry());
  assert.equal(
    normalizeGeometry(geometry({ rotation_deg: 999 })).rotation_deg,
    180,
  );
  assert.equal(
    normalizeGeometry(geometry({ rotation_deg: -999 })).rotation_deg,
    -180,
  );
});

test("moveGeometry moves freely in percentages and clamps at page edges", () => {
  assert.deepEqual(
    moveGeometry(geometry(), { x_pct: 1.3, y_pct: -2.7 }),
    geometry({ x_pct: 11.3, y_pct: 17.3 }),
  );
  assert.deepEqual(
    moveGeometry(geometry(), { x_pct: 90, y_pct: 90 }),
    geometry({ x_pct: 70, y_pct: 80 }),
  );
});

test("resizeGeometry applies corner and edge deltas with a one-percent minimum", () => {
  assert.deepEqual(
    resizeGeometry(geometry(), "south-east", {
      x_pct: 5,
      y_pct: 10,
    }),
    geometry({ width_pct: 35, height_pct: 30 }),
  );
  assert.deepEqual(
    resizeGeometry(geometry(), "north-west", {
      x_pct: 5,
      y_pct: -5,
    }),
    geometry({ x_pct: 15, y_pct: 15, width_pct: 25, height_pct: 25 }),
  );
  assert.deepEqual(
    resizeGeometry(geometry(), "west", {
      x_pct: 50,
      y_pct: 0,
    }),
    geometry({ x_pct: 39, width_pct: 1 }),
  );
});

test("resizeGeometry preserves the original aspect ratio when locked", () => {
  assert.deepEqual(
    resizeGeometry(
      geometry(),
      "south-east",
      { x_pct: 5, y_pct: 10 },
      { lockAspectRatio: true },
    ),
    geometry({ width_pct: 45, height_pct: 30 }),
  );
});

test("resizeGeometry resizes from the center when requested", () => {
  assert.deepEqual(
    resizeGeometry(
      geometry(),
      "south-east",
      { x_pct: 5, y_pct: 10 },
      { fromCenter: true },
    ),
    geometry({
      x_pct: 5,
      y_pct: 10,
      width_pct: 40,
      height_pct: 40,
    }),
  );
});

test("resizeGeometry combines center and proportional resizing", () => {
  assert.deepEqual(
    resizeGeometry(
      geometry({ x_pct: 30, y_pct: 30 }),
      "south-east",
      { x_pct: 5, y_pct: 10 },
      { fromCenter: true, lockAspectRatio: true },
    ),
    geometry({
      x_pct: 15,
      y_pct: 20,
      width_pct: 60,
      height_pct: 40,
    }),
  );
});

test("rotateGeometry measures the pointer around the shape center and clamps", () => {
  const bounds = { left: 0, top: 0, width: 200, height: 100 };

  assert.equal(
    rotateGeometry(geometry(), { x: 50, y: 10 }, bounds).rotation_deg,
    0,
  );
  assert.equal(
    rotateGeometry(geometry(), { x: 100, y: 30 }, bounds).rotation_deg,
    90,
  );
  assert.equal(
    rotateGeometry(geometry(), { x: 50, y: 90 }, bounds).rotation_deg,
    180,
  );
  assert.equal(
    rotateGeometry(geometry(), { x: 0, y: 30 }, bounds).rotation_deg,
    -90,
  );
});

test("resizeGeometry preserves a locked aspect ratio at minimum size", () => {
  assert.deepEqual(
    resizeGeometry(
      geometry(),
      "south-east",
      { x_pct: -100, y_pct: -100 },
      { lockAspectRatio: true },
    ),
    geometry({ width_pct: 1.5, height_pct: 1 }),
  );
});

test("resizeGeometry permits free resizing when aspect ratio is unlocked", () => {
  assert.deepEqual(
    resizeGeometry(
      geometry(),
      "south-east",
      { x_pct: 5, y_pct: 10 },
      { lockAspectRatio: false },
    ),
    geometry({ width_pct: 35, height_pct: 30 }),
  );
});

test("snapGeometry snaps to a two-percent grid", () => {
  const result = snapGeometry(
    geometry({ x_pct: 11.1, y_pct: 23.2 }),
  );

  assert.deepEqual(result.geometry, geometry({ x_pct: 12, y_pct: 24 }));
  assert.deepEqual(result.guides, []);
});

test("snapGeometry aligns page centers and edges and reports guides", () => {
  const centered = snapGeometry(
    geometry({ x_pct: 39.4, y_pct: 39.6, width_pct: 20 }),
    { threshold_pct: 0.75 },
  );
  assert.deepEqual(centered.geometry, geometry({
    x_pct: 40,
    y_pct: 40,
    width_pct: 20,
  }));
  assert.deepEqual(centered.guides, [
    { axis: "x", value_pct: 50, source: "page" },
    { axis: "y", value_pct: 50, source: "page" },
  ]);

  const edged = snapGeometry(
    geometry({ x_pct: 79.5, y_pct: 0.4, width_pct: 20 }),
  );
  assert.deepEqual(edged.geometry, geometry({
    x_pct: 80,
    y_pct: 0,
    width_pct: 20,
  }));
  assert.deepEqual(edged.guides, [
    { axis: "x", value_pct: 100, source: "page" },
    { axis: "y", value_pct: 0, source: "page" },
  ]);
});

test("snapGeometry aligns to optional peer guides before the grid", () => {
  const result = snapGeometry(
    geometry({ x_pct: 30.6, y_pct: 20.6 }),
    {
      peer_guides: [
        { axis: "x", value_pct: 31 },
        { axis: "y", value_pct: 21 },
      ],
    },
  );

  assert.deepEqual(result.geometry, geometry({ x_pct: 31, y_pct: 21 }));
  assert.deepEqual(result.guides, [
    { axis: "x", value_pct: 31, source: "peer" },
    { axis: "y", value_pct: 21, source: "peer" },
  ]);
});

test("keyboardMove uses quarter-percent steps and one-percent Shift steps", () => {
  assert.deepEqual(
    keyboardMove(geometry(), "right"),
    geometry({ x_pct: 10.25 }),
  );
  assert.deepEqual(
    keyboardMove(geometry(), "up", true),
    geometry({ y_pct: 19 }),
  );
});
