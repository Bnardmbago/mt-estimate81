import type { CSSProperties } from "react";

export type CoverBackgroundFit = "cover" | "contain" | "fill";

export type CoverBackgroundControls = {
  x?: number;
  y?: number;
  zoom?: number;
  fit?: CoverBackgroundFit | string;
  opacity?: number;
};

/**
 * Full-bleed background pan/zoom styles.
 *
 * Uses focal-point anchoring (`left`/`top` + matching negative translate) with
 * min/max sizing from zoom. Unlike `object-position` + `object-fit: cover`,
 * raising zoom creates overflow on both axes so horizontal and vertical pan
 * both work for portrait and landscape images.
 */
export function coverBackgroundImageStyle(
  controls: CoverBackgroundControls,
): CSSProperties {
  const x = clamp(controls.x ?? 50, 0, 100);
  const y = clamp(controls.y ?? 50, 0, 100);
  const zoom = clamp(controls.zoom ?? 1, 0.1, 4);
  const fit = normalizeFit(controls.fit);
  const opacity = clamp(controls.opacity ?? 1, 0, 1);
  const size = formatPercent(zoom * 100);
  const xPct = formatPercent(x);
  const yPct = formatPercent(y);

  const anchored: CSSProperties = {
    position: "absolute",
    left: `${xPct}%`,
    top: `${yPct}%`,
    transform: `translate(${formatTranslate(-x)}%, ${formatTranslate(-y)}%)`,
    opacity,
  };

  if (fit === "fill") {
    return {
      ...anchored,
      width: `${size}%`,
      height: `${size}%`,
      maxWidth: "none",
      objectFit: "fill",
    };
  }

  if (fit === "contain") {
    return {
      ...anchored,
      width: "auto",
      height: "auto",
      maxWidth: `${size}%`,
      maxHeight: `${size}%`,
      objectFit: "contain",
    };
  }

  return {
    ...anchored,
    width: "auto",
    height: "auto",
    maxWidth: "none",
    minWidth: `${size}%`,
    minHeight: `${size}%`,
    objectFit: "cover",
  };
}

/** Compact inline CSS for PDF/HTML export templates. */
export function coverBackgroundInlineCss(controls: CoverBackgroundControls): string {
  const style = coverBackgroundImageStyle(controls);
  const parts: string[] = [];
  const push = (key: string, value: string | number | undefined) => {
    if (value === undefined || value === "") return;
    parts.push(`${key}:${value}`);
  };

  push("position", style.position as string | undefined);
  push("left", style.left as string | undefined);
  push("top", style.top as string | undefined);
  push("width", style.width as string | undefined);
  push("height", style.height as string | undefined);
  push("min-width", style.minWidth as string | undefined);
  push("min-height", style.minHeight as string | undefined);
  push("max-width", style.maxWidth as string | undefined);
  push("max-height", style.maxHeight as string | undefined);
  push("transform", style.transform as string | undefined);
  push("object-fit", style.objectFit as string | undefined);
  push("opacity", style.opacity === undefined ? undefined : String(style.opacity));
  push("right", "auto");
  push("bottom", "auto");
  return parts.join(";");
}

function normalizeFit(fit: CoverBackgroundControls["fit"]): CoverBackgroundFit {
  if (fit === "contain" || fit === "fill") return fit;
  return "cover";
}

function clamp(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min;
  return Math.min(max, Math.max(min, value));
}

function formatPercent(value: number): string {
  if (Number.isInteger(value)) return String(value);
  return String(Number(value.toFixed(4)));
}

function formatTranslate(value: number): string {
  if (Object.is(value, -0) || value === 0) return "0";
  return formatPercent(value);
}
