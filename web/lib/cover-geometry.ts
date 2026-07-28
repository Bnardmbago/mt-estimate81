export type CoverGeometry = {
  x_pct: number;
  y_pct: number;
  width_pct: number;
  height_pct?: number;
  rotation_deg?: number;
  z_index: number;
};

export type PercentPoint = {
  x_pct: number;
  y_pct: number;
};

export type CanvasPoint = {
  x: number;
  y: number;
};

export type CanvasBounds = {
  left: number;
  top: number;
  width: number;
  height: number;
};

export type ResizeHandle =
  | "north"
  | "north-east"
  | "east"
  | "south-east"
  | "south"
  | "south-west"
  | "west"
  | "north-west";

export type ResizeOptions = {
  lockAspectRatio?: boolean;
  fromCenter?: boolean;
};

export type KeyboardDirection =
  | "up"
  | "right"
  | "down"
  | "left"
  | "ArrowUp"
  | "ArrowRight"
  | "ArrowDown"
  | "ArrowLeft";

export type SnapGuide = {
  axis: "x" | "y";
  value_pct: number;
  source: "page" | "peer";
};

export type PeerGuide = Pick<SnapGuide, "axis" | "value_pct">;

export type SnapOptions = {
  grid_size_pct?: number;
  threshold_pct?: number;
  peer_guides?: readonly PeerGuide[];
};

export type SnapResult = {
  geometry: CoverGeometry;
  guides: SnapGuide[];
};

const MIN_SIZE_PCT = 1;
const MAX_Z_INDEX = 999;

const clamp = (value: number, minimum: number, maximum: number): number =>
  Math.min(Math.max(value, minimum), maximum);

const finiteOr = (value: unknown, fallback: number): number =>
  typeof value === "number" && Number.isFinite(value) ? value : fallback;

export function normalizeGeometry(
  value: Partial<CoverGeometry> | null | undefined,
): CoverGeometry {
  const width = clamp(
    finiteOr(value?.width_pct, MIN_SIZE_PCT),
    MIN_SIZE_PCT,
    100,
  );
  const hasHeight = value?.height_pct !== undefined;
  const height = hasHeight
    ? clamp(
        finiteOr(value.height_pct, MIN_SIZE_PCT),
        MIN_SIZE_PCT,
        100,
      )
    : undefined;

  return {
    x_pct: clamp(finiteOr(value?.x_pct, 0), 0, 100 - width),
    y_pct: clamp(
      finiteOr(value?.y_pct, 0),
      0,
      height === undefined ? 100 : 100 - height,
    ),
    width_pct: width,
    ...(height === undefined ? {} : { height_pct: height }),
    ...(value?.rotation_deg === undefined
      ? {}
      : {
          rotation_deg: clamp(
            finiteOr(value.rotation_deg, 0),
            -180,
            180,
          ),
        }),
    z_index: clamp(
      Math.round(finiteOr(value?.z_index, 0)),
      0,
      MAX_Z_INDEX,
    ),
  };
}

export function pointToPercent(
  point: CanvasPoint,
  bounds: CanvasBounds,
): PercentPoint {
  const width = finiteOr(bounds.width, 0);
  const height = finiteOr(bounds.height, 0);
  const x = finiteOr(point.x, finiteOr(bounds.left, 0));
  const y = finiteOr(point.y, finiteOr(bounds.top, 0));
  const left = finiteOr(bounds.left, 0);
  const top = finiteOr(bounds.top, 0);

  return {
    x_pct:
      width > 0 ? clamp(((x - left) / width) * 100, 0, 100) : 0,
    y_pct:
      height > 0 ? clamp(((y - top) / height) * 100, 0, 100) : 0,
  };
}

export function moveGeometry(
  geometry: CoverGeometry,
  delta: PercentPoint,
): CoverGeometry {
  const normalized = normalizeGeometry(geometry);
  return normalizeGeometry({
    ...normalized,
    x_pct: normalized.x_pct + finiteOr(delta.x_pct, 0),
    y_pct: normalized.y_pct + finiteOr(delta.y_pct, 0),
  });
}

export function resizeGeometry(
  geometry: CoverGeometry,
  handle: ResizeHandle,
  delta: PercentPoint,
  options: ResizeOptions = {},
): CoverGeometry {
  const normalized = normalizeGeometry(geometry);
  const dx = finiteOr(delta.x_pct, 0);
  const dy = finiteOr(delta.y_pct, 0);
  let left = normalized.x_pct;
  let top = normalized.y_pct;
  let right = left + normalized.width_pct;
  let bottom = top + (normalized.height_pct ?? MIN_SIZE_PCT);

  if (options.fromCenter && (handle.includes("west") || handle.includes("east"))) {
    const center = left + normalized.width_pct / 2;
    const widthDelta = handle.includes("east") ? dx * 2 : -dx * 2;
    const maximumWidth = 2 * Math.min(center, 100 - center);
    const width = clamp(
      normalized.width_pct + widthDelta,
      MIN_SIZE_PCT,
      maximumWidth,
    );
    left = center - width / 2;
    right = center + width / 2;
  } else if (handle.includes("west")) {
    left = clamp(left + dx, 0, right - MIN_SIZE_PCT);
  } else if (handle.includes("east")) {
    right = clamp(right + dx, left + MIN_SIZE_PCT, 100);
  }

  if (options.fromCenter && (handle.includes("north") || handle.includes("south"))) {
    const center = top + (normalized.height_pct ?? MIN_SIZE_PCT) / 2;
    const heightDelta = handle.includes("south") ? dy * 2 : -dy * 2;
    const maximumHeight = 2 * Math.min(center, 100 - center);
    const height = clamp(
      (normalized.height_pct ?? MIN_SIZE_PCT) + heightDelta,
      MIN_SIZE_PCT,
      maximumHeight,
    );
    top = center - height / 2;
    bottom = center + height / 2;
  } else if (handle.includes("north")) {
    top = clamp(top + dy, 0, bottom - MIN_SIZE_PCT);
  } else if (handle.includes("south")) {
    bottom = clamp(bottom + dy, top + MIN_SIZE_PCT, 100);
  }

  const changesHeight =
    normalized.height_pct !== undefined ||
    handle.includes("north") ||
    handle.includes("south");

  if (options.lockAspectRatio && normalized.height_pct !== undefined) {
    const originalWidth = normalized.width_pct;
    const originalHeight = normalized.height_pct;
    const aspectRatio = originalWidth / originalHeight;
    const changesWidth = handle.includes("west") || handle.includes("east");
    const changesVertical = handle.includes("north") || handle.includes("south");
    const freeWidth = right - left;
    const freeHeight = bottom - top;
    let targetWidth: number;
    let targetHeight: number;

    if (changesWidth && changesVertical) {
      const widthChange = Math.abs(freeWidth - originalWidth) / originalWidth;
      const heightChange = Math.abs(freeHeight - originalHeight) / originalHeight;
      if (heightChange > widthChange) {
        targetHeight = freeHeight;
        targetWidth = targetHeight * aspectRatio;
      } else {
        targetWidth = freeWidth;
        targetHeight = targetWidth / aspectRatio;
      }
    } else if (changesWidth) {
      targetWidth = freeWidth;
      targetHeight = targetWidth / aspectRatio;
    } else {
      targetHeight = freeHeight;
      targetWidth = targetHeight * aspectRatio;
    }

    const minimumScale = Math.max(
      1,
      MIN_SIZE_PCT / targetWidth,
      MIN_SIZE_PCT / targetHeight,
    );
    targetWidth *= minimumScale;
    targetHeight *= minimumScale;

    const horizontalAnchor = options.fromCenter
      ? normalized.x_pct + originalWidth / 2
      : handle.includes("west")
        ? normalized.x_pct + originalWidth
        : handle.includes("east")
          ? normalized.x_pct
          : normalized.x_pct + originalWidth / 2;
    const verticalAnchor = options.fromCenter
      ? normalized.y_pct + originalHeight / 2
      : handle.includes("north")
        ? normalized.y_pct + originalHeight
        : handle.includes("south")
          ? normalized.y_pct
          : normalized.y_pct + originalHeight / 2;
    const maxWidth = options.fromCenter
      ? 2 * Math.min(horizontalAnchor, 100 - horizontalAnchor)
      : changesWidth
      ? handle.includes("west") ? horizontalAnchor : 100 - horizontalAnchor
      : 2 * Math.min(horizontalAnchor, 100 - horizontalAnchor);
    const maxHeight = options.fromCenter
      ? 2 * Math.min(verticalAnchor, 100 - verticalAnchor)
      : changesVertical
      ? handle.includes("north") ? verticalAnchor : 100 - verticalAnchor
      : 2 * Math.min(verticalAnchor, 100 - verticalAnchor);
    const scale = Math.min(1, maxWidth / targetWidth, maxHeight / targetHeight);
    targetWidth *= scale;
    targetHeight *= scale;

    left = options.fromCenter
      ? horizontalAnchor - targetWidth / 2
      : handle.includes("west")
        ? horizontalAnchor - targetWidth
        : handle.includes("east")
          ? horizontalAnchor
          : horizontalAnchor - targetWidth / 2;
    top = options.fromCenter
      ? verticalAnchor - targetHeight / 2
      : handle.includes("north")
        ? verticalAnchor - targetHeight
        : handle.includes("south")
          ? verticalAnchor
          : verticalAnchor - targetHeight / 2;
    right = left + targetWidth;
    bottom = top + targetHeight;
  }

  return normalizeGeometry({
    ...normalized,
    x_pct: left,
    y_pct: top,
    width_pct: right - left,
    ...(changesHeight ? { height_pct: bottom - top } : {}),
  });
}

export function rotateGeometry(
  geometry: CoverGeometry,
  pointer: CanvasPoint,
  bounds: CanvasBounds,
): CoverGeometry {
  const normalized = normalizeGeometry(geometry);
  const centerX =
    finiteOr(bounds.left, 0) +
    ((normalized.x_pct + normalized.width_pct / 2) / 100) *
      finiteOr(bounds.width, 0);
  const centerY =
    finiteOr(bounds.top, 0) +
    ((normalized.y_pct + (normalized.height_pct ?? MIN_SIZE_PCT) / 2) / 100) *
      finiteOr(bounds.height, 0);
  const pointerX = finiteOr(pointer.x, centerX);
  const pointerY = finiteOr(pointer.y, centerY);
  const angle = (Math.atan2(pointerY - centerY, pointerX - centerX) * 180) /
    Math.PI + 90;
  const normalizedAngle = angle > 180 ? angle - 360 : angle;

  return normalizeGeometry({
    ...normalized,
    rotation_deg: clamp(normalizedAngle, -180, 180),
  });
}

type AxisCandidate = {
  position: number;
  guide: SnapGuide;
  distance: number;
};

function guideCandidate(
  axis: "x" | "y",
  start: number,
  size: number,
  guides: readonly SnapGuide[],
  threshold: number,
): AxisCandidate | undefined {
  const anchors = [
    { value: start, offset: 0 },
    { value: start + size / 2, offset: size / 2 },
    { value: start + size, offset: size },
  ];
  let best: AxisCandidate | undefined;

  for (const guide of guides) {
    if (guide.axis !== axis) continue;
    for (const anchor of anchors) {
      const distance = Math.abs(anchor.value - guide.value_pct);
      if (distance <= threshold && (!best || distance < best.distance)) {
        best = {
          position: guide.value_pct - anchor.offset,
          guide,
          distance,
        };
      }
    }
  }

  return best;
}

export function snapGeometry(
  geometry: CoverGeometry,
  options: SnapOptions = {},
): SnapResult {
  const normalized = normalizeGeometry(geometry);
  const gridSize = finiteOr(options.grid_size_pct, 2);
  const usableGridSize = gridSize > 0 ? gridSize : 2;
  const threshold = Math.max(0, finiteOr(options.threshold_pct, 0.75));
  const height = normalized.height_pct ?? MIN_SIZE_PCT;
  const pageGuides: SnapGuide[] = [
    { axis: "x", value_pct: 0, source: "page" },
    { axis: "x", value_pct: 50, source: "page" },
    { axis: "x", value_pct: 100, source: "page" },
    { axis: "y", value_pct: 0, source: "page" },
    { axis: "y", value_pct: 50, source: "page" },
    { axis: "y", value_pct: 100, source: "page" },
  ];
  const peerGuides: SnapGuide[] = (options.peer_guides ?? [])
    .filter(
      (guide) =>
        (guide.axis === "x" || guide.axis === "y") &&
        Number.isFinite(guide.value_pct),
    )
    .map((guide) => ({ ...guide, source: "peer" }));
  const candidates = [...peerGuides, ...pageGuides];
  const xCandidate = guideCandidate(
    "x",
    normalized.x_pct,
    normalized.width_pct,
    candidates,
    threshold,
  );
  const yCandidate = guideCandidate(
    "y",
    normalized.y_pct,
    height,
    candidates,
    threshold,
  );

  const snapped = normalizeGeometry({
    ...normalized,
    x_pct:
      xCandidate?.position ??
      Math.round(normalized.x_pct / usableGridSize) * usableGridSize,
    y_pct:
      yCandidate?.position ??
      Math.round(normalized.y_pct / usableGridSize) * usableGridSize,
  });

  return {
    geometry: snapped,
    guides: [
      ...(xCandidate ? [xCandidate.guide] : []),
      ...(yCandidate ? [yCandidate.guide] : []),
    ],
  };
}

export function keyboardMove(
  geometry: CoverGeometry,
  direction: KeyboardDirection,
  shiftKey = false,
): CoverGeometry {
  const step = shiftKey ? 1 : 0.25;
  const delta: PercentPoint = { x_pct: 0, y_pct: 0 };

  if (direction === "left" || direction === "ArrowLeft") {
    delta.x_pct = -step;
  } else if (direction === "right" || direction === "ArrowRight") {
    delta.x_pct = step;
  } else if (direction === "up" || direction === "ArrowUp") {
    delta.y_pct = -step;
  } else if (direction === "down" || direction === "ArrowDown") {
    delta.y_pct = step;
  }

  return moveGeometry(geometry, delta);
}
