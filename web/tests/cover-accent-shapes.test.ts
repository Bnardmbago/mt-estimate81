import assert from "node:assert/strict";
import test from "node:test";

import {
  ACCENT_SHAPE_WARNING_THRESHOLD,
  accentDefinitions,
  accentHexColor,
  accentLineBorderUnderlay,
  accentShapeCountWarning,
  accentShapeSvgProps,
  accentShapeTransform,
  coerceAccentShapes,
  createAccentShape,
  createEdgeStripe,
  duplicateAccentShape,
  enforceCircleGeometry,
  isAccentShapeType,
  legacyAccentToShape,
  resolveAccentFill,
  type AccentFill,
  type AccentPageDimensions,
  type AccentShapeType,
} from "../lib/cover-accent-shapes";

const TYPES: AccentShapeType[] = [
  "rectangle",
  "line",
  "circle",
  "ellipse",
  "triangle",
  "polygon",
];

const A4_PORTRAIT: AccentPageDimensions = { width_mm: 210, height_mm: 297 };

test("createAccentShape creates all six defaults with unique IDs", () => {
  const shapes = TYPES.map((type) => createAccentShape(type, "#2563eb"));

  assert.deepEqual(shapes.map((shape) => shape.type), TYPES);
  assert.equal(new Set(shapes.map((shape) => shape.id)).size, TYPES.length);
  assert.ok(shapes.every((shape) => shape.fill.mode === "theme"));
  assert.equal(shapes.find((shape) => shape.type === "polygon")?.points?.length, 6);
  assert.equal(shapes.find((shape) => shape.type === "line")?.line?.cap, "butt");
});

test("createEdgeStripe converts a fixed physical thickness for every page edge", () => {
  const page = { width_mm: 200, height_mm: 100 };

  assert.deepEqual(createEdgeStripe("left", page).geometry, {
    x_pct: 0,
    y_pct: 0,
    width_pct: 6,
    height_pct: 100,
    rotation_deg: 0,
    z_index: 1,
  });
  assert.deepEqual(createEdgeStripe("right", page).geometry, {
    x_pct: 94,
    y_pct: 0,
    width_pct: 6,
    height_pct: 100,
    rotation_deg: 0,
    z_index: 1,
  });
  assert.deepEqual(createEdgeStripe("top", page).geometry, {
    x_pct: 0,
    y_pct: 0,
    width_pct: 100,
    height_pct: 12,
    rotation_deg: 0,
    z_index: 1,
  });
  assert.deepEqual(createEdgeStripe("bottom", page).geometry, {
    x_pct: 0,
    y_pct: 88,
    width_pct: 100,
    height_pct: 12,
    rotation_deg: 0,
    z_index: 1,
  });
});

test("duplicateAccentShape deeply copies a shape and assigns a new ID", () => {
  const source = createAccentShape("polygon", "#2563eb");
  const duplicate = duplicateAccentShape(source);

  assert.notEqual(duplicate.id, source.id);
  assert.equal(duplicate.name, `${source.name} copy`);
  assert.notEqual(duplicate.points, source.points);
  duplicate.points![0].x_pct = 99;
  assert.notEqual(source.points![0].x_pct, 99);
});

test("resolveAccentFill handles Theme, custom, linear, and radial fills", () => {
  const fills: AccentFill[] = [
    { mode: "theme", opacity: 0.8 },
    { mode: "custom", color: "#123456", opacity: 0.7 },
    {
      mode: "linear",
      start_color: "#111111",
      end_color: "#eeeeee",
      angle_deg: 30,
      opacity: 0.6,
    },
    {
      mode: "radial",
      start_color: "#222222",
      end_color: "#dddddd",
      center_x_pct: 40,
      center_y_pct: 60,
      opacity: 0.5,
    },
  ];

  assert.equal(resolveAccentFill(fills[0], "#2563eb", "shape-1"), "#2563eb");
  assert.equal(resolveAccentFill(fills[1], "#2563eb", "shape-1"), "#123456");
  assert.equal(
    resolveAccentFill(fills[2], "#2563eb", "shape-1"),
    "url(#accent-shape-1-linear)",
  );
  assert.equal(
    resolveAccentFill(fills[3], "#2563eb", "shape-1"),
    "url(#accent-shape-1-radial)",
  );
});

test("accent SVG props emit page-mm coordinates with pt->mm border and rotation", () => {
  const shape = createAccentShape("rectangle", "#2563eb");
  shape.id = "shape-1";
  shape.geometry.rotation_deg = 30;
  shape.fill = { mode: "custom", color: "#123456", opacity: 0.75 };
  shape.border = {
    enabled: true,
    color: "#abcdef",
    width_pt: 2,
    style: "dashed",
    radius_pct: 10,
  };
  shape.pattern = {
    type: "dots",
    color: "#ffffff",
    scale: 2,
    spacing: 3,
    opacity: 0.4,
  };

  // rectangle default geometry (20,20,60,40) on A4 portrait (210 x 297 mm).
  assert.deepEqual(accentShapeSvgProps(shape, "#2563eb", A4_PORTRAIT), {
    x: "42",
    y: "59.4",
    width: "126",
    height: "118.8",
    rx: "11.88",
    fill: "url(#accent-shape-1-pattern)",
    fillOpacity: 0.75,
    stroke: "#abcdef",
    strokeWidth: "0.705556",
    strokeDasharray: "6 4",
  });
  assert.equal(accentShapeTransform(shape, A4_PORTRAIT), "rotate(30 105 118.8)");
});

test("accent circle emits page-mm center and radius on A4 portrait", () => {
  const shape = createAccentShape("circle", "#2563eb");
  shape.id = "disc";

  // circle default geometry (30,25,40,40) on A4 portrait.
  assert.deepEqual(accentShapeSvgProps(shape, "#2563eb", A4_PORTRAIT), {
    cx: "105",
    cy: "133.65",
    r: "42",
    fill: "#2563eb",
    fillOpacity: 1,
  });
});

test("accent rotation transform centers on the page-mm bounding box", () => {
  const shape = createAccentShape("rectangle", "#2563eb");
  shape.geometry = {
    x_pct: 0,
    y_pct: 0,
    width_pct: 100,
    height_pct: 100,
    rotation_deg: 45,
    z_index: 1,
  };

  assert.equal(accentShapeTransform(shape, A4_PORTRAIT), "rotate(45 105 148.5)");
  const unrotated = createAccentShape("rectangle", "#2563eb");
  assert.equal(accentShapeTransform(unrotated, A4_PORTRAIT), undefined);
});

test("accent pattern tile uses scale*spacing in page-mm user units", () => {
  const shape = createAccentShape("rectangle", "#2563eb");
  shape.id = "tile";
  shape.pattern = { type: "grid", color: "#ffffff", scale: 2, spacing: 3, opacity: 0.25 };

  const definitions = accentDefinitions([shape], "#2563eb");
  const pattern = definitions.find((definition) => definition.kind === "pattern");
  assert.ok(pattern);
  assert.equal(pattern!.props.width, "6");
  assert.equal(pattern!.props.height, "6");
});

test("accent line thickness converts to page-mm and renders a border underlay", () => {
  const shape = createAccentShape("line", "#2563eb");
  shape.id = "rule";
  shape.line = { thickness_pct: 10, cap: "round" };
  shape.border = { enabled: true, color: "#abcdef", width_pt: 3, style: "dotted", radius_pct: 0 };

  // line default geometry (20,45,60,10) on A4 portrait: height_mm = 297*10/100 = 29.7.
  const props = accentShapeSvgProps(shape, "#2563eb", A4_PORTRAIT);
  assert.equal(props.fill, "none");
  assert.equal(props.stroke, "#2563eb");
  // main stroke width = height_mm * thickness_pct / 100 = 29.7 * 0.1 = 2.97
  assert.equal(props.strokeWidth, "2.97");
  assert.equal(props.strokeLinecap, "round");

  const underlay = accentLineBorderUnderlay(shape, A4_PORTRAIT);
  assert.ok(underlay);
  // underlay width = line_width + 2 * (3pt -> mm) = 2.97 + 2 * (3*25.4/72)
  const borderMm = (3 * 25.4) / 72;
  assert.equal(underlay!.stroke, "#abcdef");
  assert.equal(underlay!.strokeWidth, formatExpected(2.97 + 2 * borderMm));
  assert.equal(underlay!.strokeDasharray, "1 3");
  assert.equal(underlay!.strokeLinecap, "round");
});

test("enforceCircleGeometry equalizes width and height in percent", () => {
  const circle = createAccentShape("circle", "#2563eb");
  circle.geometry.width_pct = 60;
  circle.geometry.height_pct = 30;
  const fixed = enforceCircleGeometry(circle);
  assert.equal(fixed.geometry.width_pct, 30);
  assert.equal(fixed.geometry.height_pct, 30);

  const rect = createAccentShape("rectangle", "#2563eb");
  rect.geometry.width_pct = 60;
  rect.geometry.height_pct = 30;
  assert.equal(enforceCircleGeometry(rect), rect);
});

function formatExpected(value: number): string {
  if (Math.abs(value) < 0.0000005) return "0";
  return value.toFixed(6).replace(/\.?0+$/, "");
}

test("accentDefinitions returns deterministic gradient and pattern IDs", () => {
  const shape = createAccentShape("rectangle", "#2563eb");
  shape.id = "brand-mark";
  shape.fill = {
    mode: "linear",
    start_color: "#111111",
    end_color: "#eeeeee",
    angle_deg: 45,
    opacity: 1,
  };
  shape.pattern = {
    type: "grid",
    color: "#ffffff",
    scale: 2,
    spacing: 3,
    opacity: 0.25,
  };

  const first = accentDefinitions([shape], "#2563eb");
  assert.deepEqual(first, accentDefinitions([shape], "#2563eb"));
  assert.deepEqual(first.map((definition) => definition.id), [
    "accent-brand-mark-linear",
    "accent-brand-mark-pattern",
  ]);
  assert.equal(first[1].backgroundFill, "url(#accent-brand-mark-linear)");
});

test("accentShapeCountWarning appears only above fifty shapes", () => {
  const shape = createAccentShape("rectangle", "#2563eb");

  assert.equal(ACCENT_SHAPE_WARNING_THRESHOLD, 50);
  assert.equal(accentShapeCountWarning(Array(50).fill(shape)), null);
  assert.match(accentShapeCountWarning(Array(51).fill(shape)) ?? "", /50/);
});

test("accentHexColor normalizes safe hex and rejects unsafe input", () => {
  assert.equal(accentHexColor("2563EB"), "#2563eb");
  assert.equal(accentHexColor("#AbCdEf"), "#abcdef");
  assert.equal(accentHexColor("url(https://x)"), null);
  assert.equal(accentHexColor(123), null);
  assert.equal(accentHexColor(undefined), null);
});

test("isAccentShapeType guards the supported enum", () => {
  assert.ok(isAccentShapeType("polygon"));
  assert.equal(isAccentShapeType("star"), false);
  assert.equal(isAccentShapeType(null), false);
});

test("legacyAccentToShape converts the historical left stripe", () => {
  const shape = legacyAccentToShape(
    { enabled: true, width_mm: 21, opacity: 0.8 },
    { width_mm: 210, height_mm: 297 },
  );

  assert.ok(shape);
  assert.equal(shape!.id, "legacy-accent");
  assert.equal(shape!.type, "rectangle");
  assert.equal(shape!.geometry.width_pct, 10);
  assert.equal(shape!.geometry.height_pct, 100);
  assert.equal(shape!.fill.mode, "theme");
  assert.equal(shape!.fill.opacity, 0.8);
});

test("legacyAccentToShape returns null when the accent is disabled", () => {
  assert.equal(
    legacyAccentToShape({ enabled: false }, { width_mm: 210, height_mm: 297 }),
    null,
  );
});

test("coerceAccentShapes keeps valid shapes and drops malformed ones", () => {
  const valid = createAccentShape("circle", "#2563eb");
  const shapes = coerceAccentShapes([
    JSON.parse(JSON.stringify(valid)),
    { type: "star" },
    null,
    "nope",
    { type: "rectangle" },
  ]);

  assert.equal(shapes.length, 2);
  assert.equal(shapes[0].type, "circle");
  assert.equal(shapes[0].id, valid.id);
  assert.equal(shapes[1].type, "rectangle");
  assert.equal(shapes[1].fill.mode, "theme");
  assert.equal(shapes[1].border.enabled, false);
});

test("coerceAccentShapes hardens unsafe nested values", () => {
  const [shape] = coerceAccentShapes([
    {
      type: "rectangle",
      id: "shape-x",
      fill: { mode: "custom", color: "url(https://x)", opacity: 5 },
      border: { enabled: true, color: "not-a-color", width_pt: 999, style: "wavy" },
      pattern: { type: "spiral", color: "#zzzzzz", scale: 999 },
    },
  ]);

  assert.equal(shape.fill.mode, "custom");
  assert.equal((shape.fill as { color: string }).color, "#000000");
  assert.equal(shape.fill.opacity, 1);
  assert.equal(shape.border.color, "#000000");
  assert.equal(shape.border.width_pt, 72);
  assert.equal(shape.border.style, "solid");
  assert.equal(shape.pattern.type, "none");
  assert.equal(shape.pattern.scale, 10);
});

test("coerceAccentShapes deduplicates repeated IDs and enforces circle geometry", () => {
  const shapes = coerceAccentShapes([
    { type: "rectangle", id: "dup" },
    { type: "rectangle", id: "dup" },
    { type: "circle", id: "circle-1", geometry: { width_pct: 60, height_pct: 20 } },
  ]);

  assert.equal(shapes.length, 3);
  assert.equal(shapes[0].id, "dup");
  assert.equal(shapes[1].id, "dup-2");
  assert.equal(new Set(shapes.map((shape) => shape.id)).size, 3);
  assert.equal(shapes[2].geometry.width_pct, 20);
  assert.equal(shapes[2].geometry.height_pct, 20);
});

test("coerceAccentShapes regenerates duplicate IDs deterministically", () => {
  const input = [
    { type: "rectangle", id: "dup" },
    { type: "rectangle", id: "dup" },
    { type: "rectangle", id: "dup" },
  ];
  const first = coerceAccentShapes(input).map((shape) => shape.id);
  const second = coerceAccentShapes(input).map((shape) => shape.id);

  assert.deepEqual(first, ["dup", "dup-2", "dup-3"]);
  assert.deepEqual(first, second);
});
