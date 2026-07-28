"use client";

import { useTranslations } from "next-intl";
import {
  createAccentShape,
  type AccentBorder,
  type AccentFill,
  type AccentPattern,
  type AccentShape,
} from "@/lib/cover-accent-shapes";

type Props = {
  shape: AccentShape;
  themeAccent: string;
  onChange: (patch: Partial<AccentShape>) => void;
  onResetStyle: () => void;
  onResetGeometry: () => void;
};

const FILL_MODES: AccentFill["mode"][] = ["theme", "custom", "linear", "radial"];
const PATTERN_TYPES: AccentPattern["type"][] = [
  "none",
  "stripes",
  "dots",
  "grid",
  "diagonal_hatch",
];
const BORDER_STYLES: AccentBorder["style"][] = ["solid", "dashed", "dotted"];
const LINE_CAPS = ["butt", "round", "square"] as const;

export default function PresentationAccentShapeStyleControls({
  shape,
  themeAccent,
  onChange,
  onResetStyle,
  onResetGeometry,
}: Props) {
  const t = useTranslations("admin.presentation.cover");
  const fill = shape.fill;

  function changeFillMode(mode: AccentFill["mode"]) {
    if (mode === fill.mode) return;
    const opacity = fill.opacity;
    const start = "start_color" in fill ? fill.start_color : themeAccent;
    const end = "end_color" in fill ? fill.end_color : "#ffffff";
    const custom = fill.mode === "custom" ? fill.color : themeAccent;
    if (mode === "theme") onChange({ fill: { mode: "theme", opacity } });
    else if (mode === "custom") onChange({ fill: { mode: "custom", color: custom, opacity } });
    else if (mode === "linear") {
      onChange({
        fill: { mode: "linear", start_color: start, end_color: end, angle_deg: 0, opacity },
      });
    } else {
      onChange({
        fill: {
          mode: "radial",
          start_color: start,
          end_color: end,
          center_x_pct: 50,
          center_y_pct: 50,
          opacity,
        },
      });
    }
  }

  function patchFill(patch: Partial<Record<string, number | string>>) {
    onChange({ fill: { ...fill, ...patch } as AccentFill });
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">{t("accent.appearance")}</h3>
        <span className="text-xs text-slate-500">{shape.name}</span>
      </div>

      <div className="mt-3 space-y-3">
        <Select
          label={t("accent.fillMode")}
          value={fill.mode}
          options={FILL_MODES}
          labelFor={(value) => t(`accent.fillModes.${value}`)}
          onChange={(value) => changeFillMode(value as AccentFill["mode"])}
        />

        {fill.mode === "custom" ? (
          <HexColor label={t("accent.fillColor")} value={fill.color} onChange={(color) => patchFill({ color })} />
        ) : null}

        {fill.mode === "linear" || fill.mode === "radial" ? (
          <div className="grid gap-3 sm:grid-cols-2">
            <HexColor label={t("accent.gradientStart")} value={fill.start_color} onChange={(start_color) => patchFill({ start_color })} />
            <HexColor label={t("accent.gradientEnd")} value={fill.end_color} onChange={(end_color) => patchFill({ end_color })} />
            {fill.mode === "linear" ? (
              <NumberField label={t("accent.gradientAngle")} value={fill.angle_deg} min={-180} max={180} step={1} onChange={(angle_deg) => patchFill({ angle_deg })} />
            ) : (
              <>
                <NumberField label={t("accent.gradientCenterX")} value={fill.center_x_pct} min={0} max={100} step={1} onChange={(center_x_pct) => patchFill({ center_x_pct })} />
                <NumberField label={t("accent.gradientCenterY")} value={fill.center_y_pct} min={0} max={100} step={1} onChange={(center_y_pct) => patchFill({ center_y_pct })} />
              </>
            )}
          </div>
        ) : null}

        <RangeField label={t("accent.opacity")} value={fill.opacity} min={0} max={1} step={0.05} onChange={(opacity) => patchFill({ opacity })} />
      </div>

      <div className="mt-4 space-y-3 border-t border-slate-200 pt-3 dark:border-slate-700">
        <Select
          label={t("accent.pattern")}
          value={shape.pattern.type}
          options={PATTERN_TYPES}
          labelFor={(value) => t(`accent.patternTypes.${value}`)}
          onChange={(value) => onChange({ pattern: { ...shape.pattern, type: value as AccentPattern["type"] } })}
        />
        {shape.pattern.type !== "none" ? (
          <div className="grid gap-3 sm:grid-cols-2">
            <HexColor label={t("accent.patternColor")} value={shape.pattern.color} onChange={(color) => onChange({ pattern: { ...shape.pattern, color } })} />
            <NumberField label={t("accent.patternScale")} value={shape.pattern.scale} min={0.1} max={10} step={0.1} onChange={(scale) => onChange({ pattern: { ...shape.pattern, scale } })} />
            <NumberField label={t("accent.patternSpacing")} value={shape.pattern.spacing} min={0.1} max={100} step={0.1} onChange={(spacing) => onChange({ pattern: { ...shape.pattern, spacing } })} />
            <RangeField label={t("accent.patternOpacity")} value={shape.pattern.opacity} min={0} max={1} step={0.05} onChange={(opacity) => onChange({ pattern: { ...shape.pattern, opacity } })} />
          </div>
        ) : null}
      </div>

      <div className="mt-4 space-y-3 border-t border-slate-200 pt-3 dark:border-slate-700">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={shape.border.enabled}
            onChange={(event) => onChange({ border: { ...shape.border, enabled: event.target.checked } })}
          />
          {t("accent.borderEnabled")}
        </label>
        {shape.border.enabled ? (
          <div className="grid gap-3 sm:grid-cols-2">
            <HexColor label={t("accent.borderColor")} value={shape.border.color} onChange={(color) => onChange({ border: { ...shape.border, color } })} />
            <NumberField label={t("accent.borderWidth")} value={shape.border.width_pt} min={0} max={72} step={0.5} onChange={(width_pt) => onChange({ border: { ...shape.border, width_pt } })} />
            <Select
              label={t("accent.borderStyle")}
              value={shape.border.style}
              options={BORDER_STYLES}
              labelFor={(value) => t(`accent.borderStyles.${value}`)}
              onChange={(value) => onChange({ border: { ...shape.border, style: value as AccentBorder["style"] } })}
            />
            {shape.type === "rectangle" ? (
              <NumberField label={t("accent.borderRadius")} value={shape.border.radius_pct} min={0} max={50} step={1} onChange={(radius_pct) => onChange({ border: { ...shape.border, radius_pct } })} />
            ) : null}
          </div>
        ) : null}
      </div>

      <div className="mt-4 grid gap-3 border-t border-slate-200 pt-3 sm:grid-cols-2 dark:border-slate-700">
        <NumberField
          label={t("accent.rotation")}
          value={shape.geometry.rotation_deg}
          min={-180}
          max={180}
          step={1}
          onChange={(rotation_deg) => onChange({ geometry: { ...shape.geometry, rotation_deg } })}
        />
        {shape.type === "line" ? (
          <>
            <NumberField label={t("accent.lineThickness")} value={shape.line?.thickness_pct ?? 10} min={0.1} max={100} step={0.5} onChange={(thickness_pct) => onChange({ line: { thickness_pct, cap: shape.line?.cap ?? "butt" } })} />
            <Select
              label={t("accent.lineCap")}
              value={shape.line?.cap ?? "butt"}
              options={[...LINE_CAPS]}
              labelFor={(value) => t(`accent.lineCaps.${value}`)}
              onChange={(value) => onChange({ line: { thickness_pct: shape.line?.thickness_pct ?? 10, cap: value as "butt" | "round" | "square" } })}
            />
          </>
        ) : null}
      </div>

      <div className="mt-4 flex flex-wrap gap-2 border-t border-slate-200 pt-3 dark:border-slate-700">
        <button type="button" className="header-btn text-xs" onClick={onResetStyle}>{t("accent.resetStyle")}</button>
        <button type="button" className="header-btn text-xs" onClick={onResetGeometry}>{t("accent.resetGeometry")}</button>
      </div>
    </section>
  );
}

export function defaultAccentStyle(type: AccentShape["type"], themeAccent: string) {
  const base = createAccentShape(type, themeAccent);
  return { fill: base.fill, border: base.border, pattern: base.pattern };
}

export function defaultAccentGeometry(type: AccentShape["type"]) {
  return createAccentShape(type, "#000000").geometry;
}

function Select({
  label,
  value,
  options,
  labelFor,
  onChange,
}: {
  label: string;
  value: string;
  options: readonly string[];
  labelFor: (value: string) => string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="text-sm">
      <span className="mb-1 block">{label}</span>
      <select
        className="w-full rounded border border-slate-300 px-3 py-2 dark:border-slate-600 dark:bg-slate-950"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {options.map((option) => (
          <option key={option} value={option}>{labelFor(option)}</option>
        ))}
      </select>
    </label>
  );
}

function NumberField({
  label,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="text-sm">
      <span className="mb-1 block">{label}</span>
      <input
        type="number"
        className="w-full rounded border border-slate-300 px-3 py-2 dark:border-slate-600 dark:bg-slate-950"
        value={Number.isFinite(value) ? value : 0}
        min={min}
        max={max}
        step={step}
        onChange={(event) => {
          const next = Number(event.target.value);
          onChange(Number.isFinite(next) ? Math.min(max, Math.max(min, next)) : min);
        }}
      />
    </label>
  );
}

function RangeField({
  label,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="text-sm">
      <span className="mb-1 flex items-center justify-between">
        <span>{label}</span>
        <span className="font-mono text-xs text-slate-500">{Math.round(value * 100)}%</span>
      </span>
      <input
        type="range"
        className="w-full"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}

function HexColor({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const normalized = value.replace("#", "").toLowerCase();
  const picker = /^[0-9a-f]{6}$/.test(normalized) ? `#${normalized}` : "#000000";
  return (
    <label className="text-sm">
      <span className="mb-1 block">{label}</span>
      <span className="flex gap-2">
        <input
          type="color"
          className="h-10 w-12 rounded border border-slate-300"
          value={picker}
          onChange={(event) => onChange(event.target.value.toLowerCase())}
        />
        <input
          className="min-w-0 flex-1 rounded border border-slate-300 px-3 py-2 font-mono dark:border-slate-600 dark:bg-slate-950"
          value={normalized}
          maxLength={6}
          onChange={(event) => {
            const hex = event.target.value.replace("#", "").toLowerCase();
            if (/^[0-9a-f]{0,6}$/.test(hex)) {
              onChange(hex.length === 6 ? `#${hex}` : value);
            }
          }}
        />
      </span>
    </label>
  );
}
