import type { CoverGeometry } from "./cover-geometry";

export type AccentShapeType =
  | "rectangle"
  | "line"
  | "circle"
  | "ellipse"
  | "triangle"
  | "polygon";

export type AccentFill =
  | { mode: "theme"; opacity: number }
  | { mode: "custom"; color: string; opacity: number }
  | {
      mode: "linear";
      start_color: string;
      end_color: string;
      angle_deg: number;
      opacity: number;
    }
  | {
      mode: "radial";
      start_color: string;
      end_color: string;
      center_x_pct: number;
      center_y_pct: number;
      opacity: number;
    };

export type AccentBorder = {
  enabled: boolean;
  color: string;
  width_pt: number;
  style: "solid" | "dashed" | "dotted";
  radius_pct: number;
};

export type AccentPattern = {
  type: "none" | "stripes" | "dots" | "grid" | "diagonal_hatch";
  color: string;
  scale: number;
  spacing: number;
  opacity: number;
};

export type AccentPoint = {
  x_pct: number;
  y_pct: number;
};

export type AccentShape = {
  id: string;
  name: string;
  type: AccentShapeType;
  visible: boolean;
  locked: boolean;
  geometry: CoverGeometry & {
    height_pct: number;
    rotation_deg: number;
  };
  fill: AccentFill;
  border: AccentBorder;
  pattern: AccentPattern;
  points?: AccentPoint[];
  line?: {
    thickness_pct: number;
    cap: "butt" | "round" | "square";
  };
};

export type AccentEdge = "left" | "right" | "top" | "bottom";

export type AccentPageDimensions = {
  width_mm: number;
  height_mm: number;
};

export type AccentSvgProps = Record<string, string | number>;

export type AccentDefinition = {
  id: string;
  kind: "linearGradient" | "radialGradient" | "pattern";
  props: AccentSvgProps;
  stops?: Array<{ offset: string; color: string }>;
  backgroundFill?: string;
  patternType?: Exclude<AccentPattern["type"], "none">;
  decoration?: {
    color: string;
    scale: number;
    spacing: number;
    opacity: number;
  };
};

export const ACCENT_SHAPE_WARNING_THRESHOLD = 50;
export const EDGE_STRIPE_THICKNESS_MM = 12;

const SHAPE_NAMES: Record<AccentShapeType, string> = {
  rectangle: "Rectangle",
  line: "Line",
  circle: "Circle",
  ellipse: "Ellipse",
  triangle: "Triangle",
  polygon: "Polygon",
};

const DEFAULT_GEOMETRY: Record<
  AccentShapeType,
  AccentShape["geometry"]
> = {
  rectangle: geometry(20, 20, 60, 40),
  line: geometry(20, 45, 60, 10),
  circle: geometry(30, 25, 40, 40),
  ellipse: geometry(20, 30, 60, 30),
  triangle: geometry(25, 20, 50, 50),
  polygon: geometry(25, 20, 50, 50),
};

function geometry(
  x_pct: number,
  y_pct: number,
  width_pct: number,
  height_pct: number,
): AccentShape["geometry"] {
  return {
    x_pct,
    y_pct,
    width_pct,
    height_pct,
    rotation_deg: 0,
    z_index: 1,
  };
}

function uniqueAccentId(): string {
  return `accent-${globalThis.crypto.randomUUID()}`;
}

function defaultBorder(themeAccent: string): AccentBorder {
  return {
    enabled: false,
    color: themeAccent,
    width_pt: 0,
    style: "solid",
    radius_pct: 0,
  };
}

function defaultPattern(): AccentPattern {
  return {
    type: "none",
    color: "#ffffff",
    scale: 1,
    spacing: 1,
    opacity: 0.25,
  };
}

function polygonPoints(): AccentPoint[] {
  return [
    { x_pct: 50, y_pct: 0 },
    { x_pct: 93.3, y_pct: 25 },
    { x_pct: 93.3, y_pct: 75 },
    { x_pct: 50, y_pct: 100 },
    { x_pct: 6.7, y_pct: 75 },
    { x_pct: 6.7, y_pct: 25 },
  ];
}

export function createAccentShape(
  type: AccentShapeType,
  themeAccent: string,
): AccentShape {
  return {
    id: uniqueAccentId(),
    name: SHAPE_NAMES[type],
    type,
    visible: true,
    locked: false,
    geometry: { ...DEFAULT_GEOMETRY[type] },
    fill: { mode: "theme", opacity: 1 },
    border: defaultBorder(themeAccent),
    pattern: defaultPattern(),
    ...(type === "polygon" ? { points: polygonPoints() } : {}),
    ...(type === "line"
      ? { line: { thickness_pct: 10, cap: "butt" as const } }
      : {}),
  };
}

export function createEdgeStripe(
  edge: AccentEdge,
  page: AccentPageDimensions,
): AccentShape {
  const width = positiveFinite(page.width_mm, 210);
  const height = positiveFinite(page.height_mm, 297);
  const horizontal = edge === "top" || edge === "bottom";
  const thickness = clamp(
    EDGE_STRIPE_THICKNESS_MM / (horizontal ? height : width) * 100,
    0.1,
    100,
  );
  const shape = createAccentShape("rectangle", "#000000");
  shape.name = `${edge[0].toUpperCase()}${edge.slice(1)} stripe`;
  shape.geometry = horizontal
    ? geometry(0, edge === "bottom" ? 100 - thickness : 0, 100, thickness)
    : geometry(edge === "right" ? 100 - thickness : 0, 0, thickness, 100);
  return shape;
}

export function duplicateAccentShape(shape: AccentShape): AccentShape {
  return {
    ...shape,
    id: uniqueAccentId(),
    name: `${shape.name} copy`,
    geometry: { ...shape.geometry },
    fill: { ...shape.fill },
    border: { ...shape.border },
    pattern: { ...shape.pattern },
    ...(shape.points
      ? { points: shape.points.map((point) => ({ ...point })) }
      : {}),
    ...(shape.line ? { line: { ...shape.line } } : {}),
  };
}

export function accentShapeCountWarning(
  shapes: readonly AccentShape[],
): string | null {
  return shapes.length > ACCENT_SHAPE_WARNING_THRESHOLD
    ? `More than ${ACCENT_SHAPE_WARNING_THRESHOLD} accent shapes may reduce editing and export performance`
    : null;
}

const SHAPE_TYPE_SET: ReadonlySet<AccentShapeType> = new Set<AccentShapeType>([
  "rectangle",
  "line",
  "circle",
  "ellipse",
  "triangle",
  "polygon",
]);

export function isAccentShapeType(value: unknown): value is AccentShapeType {
  return typeof value === "string" && SHAPE_TYPE_SET.has(value as AccentShapeType);
}

/** Normalize a color to lowercase `#rrggbb`, or `null` when unsafe. */
export function accentHexColor(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const hex = value.trim().replace(/^#/, "");
  return /^[0-9a-fA-F]{6}$/.test(hex) ? `#${hex.toLowerCase()}` : null;
}

type LegacyAccent = {
  enabled?: boolean;
  width_mm?: number;
  opacity?: number;
} | null | undefined;

/** Convert the historical single left-edge stripe into a canonical shape. */
export function legacyAccentToShape(
  accent: LegacyAccent,
  page: AccentPageDimensions,
): AccentShape | null {
  if (!accent || accent.enabled === false) return null;
  const pageWidth = positiveFinite(page.width_mm, 210);
  const widthMm = positiveFinite(
    typeof accent.width_mm === "number" ? accent.width_mm : 0,
    12,
  );
  const widthPct = clamp((widthMm / pageWidth) * 100, 0.1, 100);
  const opacity = clamp(
    typeof accent.opacity === "number" && Number.isFinite(accent.opacity)
      ? accent.opacity
      : 0.9,
    0,
    1,
  );
  return {
    id: "legacy-accent",
    name: "Left stripe",
    type: "rectangle",
    visible: true,
    locked: false,
    geometry: geometry(0, 0, widthPct, 100),
    fill: { mode: "theme", opacity },
    border: defaultBorder("#000000"),
    pattern: defaultPattern(),
  };
}

/** Enforce equal width/height (in percent) for circles, matching the backend. */
export function enforceCircleGeometry(shape: AccentShape): AccentShape {
  if (shape.type !== "circle") return shape;
  const diameter = Math.min(shape.geometry.width_pct, shape.geometry.height_pct);
  if (
    shape.geometry.width_pct === diameter &&
    shape.geometry.height_pct === diameter
  ) {
    return shape;
  }
  return {
    ...shape,
    geometry: { ...shape.geometry, width_pct: diameter, height_pct: diameter },
  };
}

/** Defensively read stored JSON into safe, renderable accent shapes. */
export function coerceAccentShapes(value: unknown): AccentShape[] {
  if (!Array.isArray(value)) return [];
  const shapes: AccentShape[] = [];
  const seen = new Set<string>();
  for (const item of value) {
    let shape = coerceAccentShape(item);
    if (!shape) continue;
    if (seen.has(shape.id)) {
      // Deterministic suffix so duplicate IDs stay stable across renders
      // instead of regenerating a fresh random ID every read.
      let suffix = 2;
      let candidate = `${shape.id}-${suffix}`;
      while (seen.has(candidate)) {
        suffix += 1;
        candidate = `${shape.id}-${suffix}`;
      }
      shape = { ...shape, id: candidate };
    }
    seen.add(shape.id);
    shapes.push(enforceCircleGeometry(shape));
  }
  return shapes;
}

export function coerceAccentShape(value: unknown): AccentShape | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const record = value as Record<string, unknown>;
  if (!isAccentShapeType(record.type)) return null;
  const type = record.type;
  const defaults = createAccentShape(type, "#000000");
  const shape: AccentShape = {
    ...defaults,
    id: typeof record.id === "string" && record.id ? record.id : defaults.id,
    name:
      typeof record.name === "string" && record.name.trim()
        ? record.name
        : defaults.name,
    type,
    visible: typeof record.visible === "boolean" ? record.visible : true,
    locked: typeof record.locked === "boolean" ? record.locked : false,
    geometry: coerceGeometry(record.geometry, defaults.geometry),
    fill: coerceFill(record.fill) ?? defaults.fill,
    border: coerceBorder(record.border, defaults.border),
    pattern: coercePattern(record.pattern, defaults.pattern),
  };
  if (type === "polygon") {
    shape.points = coercePoints(record.points) ?? defaults.points;
  }
  if (type === "line") {
    shape.line = coerceLine(record.line) ?? defaults.line;
  }
  return shape;
}

function coerceGeometry(
  value: unknown,
  fallback: AccentShape["geometry"],
): AccentShape["geometry"] {
  const box =
    value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  return {
    x_pct: finite(box.x_pct, fallback.x_pct),
    y_pct: finite(box.y_pct, fallback.y_pct),
    width_pct: finite(box.width_pct, fallback.width_pct),
    height_pct: finite(box.height_pct, fallback.height_pct),
    rotation_deg: finite(box.rotation_deg, fallback.rotation_deg),
    z_index: finite(box.z_index, fallback.z_index),
  };
}

function coerceFill(value: unknown): AccentFill | null {
  if (!value || typeof value !== "object") return null;
  const fill = value as Record<string, unknown>;
  const opacity = clamp(finite(fill.opacity, 1), 0, 1);
  if (fill.mode === "theme") return { mode: "theme", opacity };
  if (fill.mode === "custom") {
    return { mode: "custom", color: accentHexColor(fill.color) ?? "#000000", opacity };
  }
  if (fill.mode === "linear") {
    return {
      mode: "linear",
      start_color: accentHexColor(fill.start_color) ?? "#000000",
      end_color: accentHexColor(fill.end_color) ?? "#ffffff",
      angle_deg: clamp(finite(fill.angle_deg, 0), -180, 180),
      opacity,
    };
  }
  if (fill.mode === "radial") {
    return {
      mode: "radial",
      start_color: accentHexColor(fill.start_color) ?? "#000000",
      end_color: accentHexColor(fill.end_color) ?? "#ffffff",
      center_x_pct: clamp(finite(fill.center_x_pct, 50), 0, 100),
      center_y_pct: clamp(finite(fill.center_y_pct, 50), 0, 100),
      opacity,
    };
  }
  return null;
}

function coerceBorder(value: unknown, fallback: AccentBorder): AccentBorder {
  const border =
    value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  const style = border.style;
  return {
    enabled: typeof border.enabled === "boolean" ? border.enabled : fallback.enabled,
    color: accentHexColor(border.color) ?? fallback.color,
    width_pt: clamp(finite(border.width_pt, fallback.width_pt), 0, 72),
    style:
      style === "solid" || style === "dashed" || style === "dotted"
        ? style
        : fallback.style,
    radius_pct: clamp(finite(border.radius_pct, fallback.radius_pct), 0, 50),
  };
}

function coercePattern(value: unknown, fallback: AccentPattern): AccentPattern {
  const pattern =
    value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  const type = pattern.type;
  const valid: AccentPattern["type"][] = [
    "none",
    "stripes",
    "dots",
    "grid",
    "diagonal_hatch",
  ];
  return {
    type: valid.includes(type as AccentPattern["type"])
      ? (type as AccentPattern["type"])
      : fallback.type,
    color: accentHexColor(pattern.color) ?? fallback.color,
    scale: clamp(finite(pattern.scale, fallback.scale), 0.1, 10),
    spacing: clamp(finite(pattern.spacing, fallback.spacing), 0.1, 100),
    opacity: clamp(finite(pattern.opacity, fallback.opacity), 0, 1),
  };
}

function coercePoints(value: unknown): AccentPoint[] | null {
  if (!Array.isArray(value) || value.length < 3 || value.length > 12) return null;
  const points: AccentPoint[] = [];
  for (const point of value) {
    if (!point || typeof point !== "object") return null;
    const record = point as Record<string, unknown>;
    if (
      typeof record.x_pct !== "number" ||
      typeof record.y_pct !== "number" ||
      !Number.isFinite(record.x_pct) ||
      !Number.isFinite(record.y_pct)
    ) {
      return null;
    }
    points.push({
      x_pct: clamp(record.x_pct, 0, 100),
      y_pct: clamp(record.y_pct, 0, 100),
    });
  }
  return points;
}

function coerceLine(value: unknown): AccentShape["line"] | null {
  if (!value || typeof value !== "object") return null;
  const line = value as Record<string, unknown>;
  const cap = line.cap;
  return {
    thickness_pct: clamp(finite(line.thickness_pct, 10), 0.1, 100),
    cap: cap === "round" || cap === "square" ? cap : "butt",
  };
}

function finite(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

export function resolveAccentFill(
  fill: AccentFill,
  themeAccent: string,
  shapeId: string,
): string {
  if (fill.mode === "theme") return themeAccent;
  if (fill.mode === "custom") return fill.color;
  return `url(#${definitionId(shapeId, fill.mode)})`;
}

function pxBox(shape: AccentShape, page: AccentPageDimensions) {
  const box = shape.geometry;
  const x = (page.width_mm * box.x_pct) / 100;
  const y = (page.height_mm * box.y_pct) / 100;
  const width = (page.width_mm * box.width_pct) / 100;
  const height = (page.height_mm * box.height_pct) / 100;
  return { x, y, width, height };
}

function ptToMm(pt: number): number {
  return (pt * 25.4) / 72;
}

function applyDashStyle(props: AccentSvgProps, style: AccentBorder["style"]) {
  if (style === "dashed") props.strokeDasharray = "6 4";
  if (style === "dotted") {
    props.strokeDasharray = "1 3";
    props.strokeLinecap = "round";
  }
}

/**
 * Emit page-mm SVG attributes for one shape, matching the backend renderer so
 * the admin preview and the exported PDF stay pixel-identical. Coordinates are
 * expressed in the same user units as the preview SVG viewBox (page mm).
 */
export function accentShapeSvgProps(
  shape: AccentShape,
  themeAccent: string,
  page: AccentPageDimensions,
): AccentSvgProps {
  const { x, y, width, height } = pxBox(shape, page);
  const props = primitiveProps(shape, x, y, width, height);
  const baseFill = resolveAccentFill(shape.fill, themeAccent, shape.id);
  const paint = shape.pattern.type === "none"
    ? baseFill
    : `url(#${definitionId(shape.id, "pattern")})`;

  if (shape.type === "line") {
    const lineWidth = (height * (shape.line?.thickness_pct ?? 1)) / 100;
    props.fill = "none";
    props.stroke = paint;
    props.strokeWidth = formatNumber(Math.max(0, lineWidth));
    props.strokeLinecap = shape.line?.cap ?? "butt";
    props.strokeOpacity = shape.fill.opacity;
  } else {
    props.fill = paint;
    props.fillOpacity = shape.fill.opacity;
    if (shape.border.enabled && shape.border.width_pt > 0) {
      props.stroke = shape.border.color;
      props.strokeWidth = formatNumber(ptToMm(shape.border.width_pt));
      applyDashStyle(props, shape.border.style);
    }
  }

  return props;
}

/** Page-mm center rotation transform, or undefined when the shape is unrotated. */
export function accentShapeTransform(
  shape: AccentShape,
  page: AccentPageDimensions,
): string | undefined {
  if (!shape.geometry.rotation_deg) return undefined;
  const { x, y, width, height } = pxBox(shape, page);
  const centerX = x + width / 2;
  const centerY = y + height / 2;
  return `rotate(${formatNumber(shape.geometry.rotation_deg)} ${formatNumber(centerX)} ${formatNumber(centerY)})`;
}

/**
 * Border underlay stroke for line shapes, matching the backend which draws a
 * wider line beneath the main stroke. Returns null when no underlay is needed.
 */
export function accentLineBorderUnderlay(
  shape: AccentShape,
  page: AccentPageDimensions,
): AccentSvgProps | null {
  if (shape.type !== "line" || !shape.border.enabled || shape.border.width_pt <= 0) {
    return null;
  }
  const { x, y, width, height } = pxBox(shape, page);
  const centerY = y + height / 2;
  const lineWidth = (height * (shape.line?.thickness_pct ?? 1)) / 100;
  const borderWidth = ptToMm(shape.border.width_pt);
  const props: AccentSvgProps = {
    x1: formatNumber(x),
    y1: formatNumber(centerY),
    x2: formatNumber(x + width),
    y2: formatNumber(centerY),
    fill: "none",
    stroke: shape.border.color,
    strokeWidth: formatNumber(lineWidth + 2 * borderWidth),
    strokeLinecap: shape.line?.cap ?? "butt",
  };
  applyDashStyle(props, shape.border.style);
  return props;
}

export function accentDefinitions(
  shapes: readonly AccentShape[],
  themeAccent: string,
): AccentDefinition[] {
  const definitions: AccentDefinition[] = [];
  for (const shape of shapes) {
    if (!shape.visible) continue;
    const fill = shape.fill;
    if (fill.mode === "linear") {
      const radians = fill.angle_deg * Math.PI / 180;
      const xOffset = 50 * Math.cos(radians);
      const yOffset = 50 * Math.sin(radians);
      definitions.push({
        id: definitionId(shape.id, "linear"),
        kind: "linearGradient",
        props: {
          x1: `${formatNumber(50 - xOffset)}%`,
          y1: `${formatNumber(50 - yOffset)}%`,
          x2: `${formatNumber(50 + xOffset)}%`,
          y2: `${formatNumber(50 + yOffset)}%`,
        },
        stops: [
          { offset: "0%", color: fill.start_color },
          { offset: "100%", color: fill.end_color },
        ],
      });
    } else if (fill.mode === "radial") {
      definitions.push({
        id: definitionId(shape.id, "radial"),
        kind: "radialGradient",
        props: {
          cx: `${formatNumber(fill.center_x_pct)}%`,
          cy: `${formatNumber(fill.center_y_pct)}%`,
          r: "70.710678%",
        },
        stops: [
          { offset: "0%", color: fill.start_color },
          { offset: "100%", color: fill.end_color },
        ],
      });
    }

    if (shape.pattern.type !== "none") {
      const pattern = shape.pattern;
      const tileSize = pattern.scale * pattern.spacing;
      definitions.push({
        id: definitionId(shape.id, "pattern"),
        kind: "pattern",
        props: {
          patternUnits: "userSpaceOnUse",
          width: formatNumber(tileSize),
          height: formatNumber(tileSize),
        },
        backgroundFill: resolveAccentFill(fill, themeAccent, shape.id),
        patternType: pattern.type as Exclude<AccentPattern["type"], "none">,
        decoration: {
          color: pattern.color,
          scale: pattern.scale,
          spacing: pattern.spacing,
          opacity: pattern.opacity,
        },
      });
    }
  }
  return definitions;
}

function primitiveProps(
  shape: AccentShape,
  x: number,
  y: number,
  width: number,
  height: number,
): AccentSvgProps {
  if (shape.type === "rectangle") {
    const radius = (Math.min(width, height) * shape.border.radius_pct) / 100;
    return {
      x: formatNumber(x),
      y: formatNumber(y),
      width: formatNumber(width),
      height: formatNumber(height),
      ...(radius > 0 ? { rx: formatNumber(radius) } : {}),
    };
  }
  if (shape.type === "line") {
    const centerY = y + height / 2;
    return {
      x1: formatNumber(x),
      y1: formatNumber(centerY),
      x2: formatNumber(x + width),
      y2: formatNumber(centerY),
    };
  }
  if (shape.type === "circle") {
    return {
      cx: formatNumber(x + width / 2),
      cy: formatNumber(y + height / 2),
      r: formatNumber(Math.min(width, height) / 2),
    };
  }
  if (shape.type === "ellipse") {
    return {
      cx: formatNumber(x + width / 2),
      cy: formatNumber(y + height / 2),
      rx: formatNumber(width / 2),
      ry: formatNumber(height / 2),
    };
  }

  const points = shape.type === "triangle"
    ? [
        { x_pct: 50, y_pct: 0 },
        { x_pct: 100, y_pct: 100 },
        { x_pct: 0, y_pct: 100 },
      ]
    : shape.points ?? polygonPoints();
  return {
    points: points
      .map((point) =>
        `${formatNumber(x + width * point.x_pct / 100)},${formatNumber(y + height * point.y_pct / 100)}`)
      .join(" "),
  };
}

function definitionId(shapeId: string, suffix: "linear" | "radial" | "pattern"): string {
  const safeId = shapeId.replace(/[^A-Za-z0-9_-]/g, "-");
  return `accent-${safeId}-${suffix}`;
}

function formatNumber(value: number): string {
  if (Math.abs(value) < 0.0000005) return "0";
  return value.toFixed(6).replace(/\.?0+$/, "");
}

function positiveFinite(value: number, fallback: number): number {
  return Number.isFinite(value) && value > 0 ? value : fallback;
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(Math.max(value, minimum), maximum);
}
