"use client";

import { useTranslations } from "next-intl";
import type {
  CoverField,
  CoverTextStyle,
} from "./PresentationCoverPreview";

type Props = {
  field: CoverField;
  onChange: (patch: Partial<CoverField>) => void;
  onResetGeometry: () => void;
  onCreateGeometry: () => void;
};

export default function PresentationTextStyleControls({
  field,
  onChange,
  onResetGeometry,
  onCreateGeometry,
}: Props) {
  const t = useTranslations("admin.presentation.cover");
  const style = field.style || {};
  const geometry = field.geometry;

  function updateStyle(patch: Partial<CoverTextStyle>) {
    const next = Object.fromEntries(
      Object.entries({ ...style, ...patch }).filter(([, value]) => value !== undefined),
    ) as CoverTextStyle;
    onChange({ style: Object.keys(next).length > 0 ? next : undefined });
  }

  function updateGeometry(name: string, value: number) {
    if (!geometry || !Number.isFinite(value)) return;
    onChange({ geometry: { ...geometry, [name]: value } });
  }

  return (
    <div className="mt-3 space-y-4 border-t border-slate-200 pt-3 dark:border-slate-700">
      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t("textStyle")}
        </h4>
        <div className="mt-2 grid gap-3 sm:grid-cols-2">
          <TextControl
            label={t("fontFamily")}
            value={style.font_family || ""}
            placeholder={t("fontFamilyPlaceholder")}
            onChange={(font_family) => updateStyle({ font_family: font_family || undefined })}
          />
          <NumberControl label={t("fontSize")} value={style.font_size_pt ?? 12} min={6} max={144} step={0.5} unit="pt" onChange={(font_size_pt) => updateStyle({ font_size_pt })} />
          <SelectControl
            label={t("fontWeight")}
            value={String(style.font_weight ?? 400)}
            options={["100", "200", "300", "400", "500", "600", "700", "800", "900"]}
            onChange={(value) => updateStyle({ font_weight: Number(value) })}
          />
          <SelectControl
            label={t("textAlignment")}
            value={style.text_align || "left"}
            options={["left", "center", "right"]}
            translate={(value) => t(`alignments.${value}`)}
            onChange={(text_align) => updateStyle({ text_align: text_align as CoverTextStyle["text_align"] })}
          />
          <ColorControl label={t("textColor")} value={style.color || "#000000"} onChange={(color) => updateStyle({ color })} />
          <NumberControl label={t("lineHeight")} value={style.line_height ?? 1.2} min={0.5} max={3} step={0.05} onChange={(line_height) => updateStyle({ line_height })} />
          <NumberControl label={t("letterSpacing")} value={style.letter_spacing_em ?? 0} min={-0.2} max={1} step={0.01} unit="em" onChange={(letter_spacing_em) => updateStyle({ letter_spacing_em })} />
          <NumberControl label={t("fieldOpacity")} value={style.opacity ?? 1} min={0} max={1} step={0.05} onChange={(opacity) => updateStyle({ opacity })} />
          <label className="flex items-center gap-2 self-end pb-2 text-xs">
            <input type="checkbox" checked={Boolean(style.italic)} onChange={(event) => updateStyle({ italic: event.target.checked })} />
            {t("italic")}
          </label>
          <label className="flex items-center gap-2 self-end pb-2 text-xs">
            <input
              type="checkbox"
              checked={Boolean(style.background_color)}
              onChange={(event) => updateStyle({ background_color: event.target.checked ? "#FFFFFF" : undefined })}
            />
            {t("fieldBackground")}
          </label>
          {style.background_color ? (
            <ColorControl label={t("backgroundColor")} value={style.background_color} onChange={(background_color) => updateStyle({ background_color })} />
          ) : null}
          <NumberControl label={t("fieldPadding")} value={style.padding_mm ?? 0} min={0} max={40} step={0.5} unit="mm" onChange={(padding_mm) => updateStyle({ padding_mm })} />
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between gap-2">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t("geometry")}
          </h4>
          {geometry ? (
            <button type="button" className="header-btn text-xs" onClick={onResetGeometry}>
              {t("resetAutomaticLayout")}
            </button>
          ) : (
            <button type="button" className="header-btn text-xs" onClick={onCreateGeometry}>
              {t("positionManually")}
            </button>
          )}
        </div>
        {geometry ? (
          <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-5">
            <NumberControl label="X" value={geometry.x_pct} min={0} max={100} step={0.25} unit="%" onChange={(value) => updateGeometry("x_pct", value)} />
            <NumberControl label="Y" value={geometry.y_pct} min={0} max={100} step={0.25} unit="%" onChange={(value) => updateGeometry("y_pct", value)} />
            <NumberControl label="W" value={geometry.width_pct} min={1} max={100} step={0.25} unit="%" onChange={(value) => updateGeometry("width_pct", value)} />
            <NumberControl label="H" value={geometry.height_pct ?? 10} min={1} max={100} step={0.25} unit="%" onChange={(value) => updateGeometry("height_pct", value)} />
            <NumberControl label={t("zIndex")} value={geometry.z_index} min={0} max={999} step={1} onChange={(value) => updateGeometry("z_index", value)} />
          </div>
        ) : (
          <p className="mt-2 text-xs text-slate-500">{t("automaticLayoutHint")}</p>
        )}
      </div>
    </div>
  );
}

function TextControl({ label, value, placeholder, onChange }: { label: string; value: string; placeholder?: string; onChange: (value: string) => void }) {
  return (
    <label className="text-xs">
      <span className="mb-1 block font-medium">{label}</span>
      <input className="w-full rounded border border-slate-300 px-2 py-1.5 dark:border-slate-600 dark:bg-slate-950" value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function NumberControl({ label, value, min, max, step, unit, onChange }: { label: string; value: number; min: number; max: number; step: number; unit?: string; onChange: (value: number) => void }) {
  return (
    <label className="text-xs">
      <span className="mb-1 block font-medium">{label}</span>
      <span className="flex">
        <input className="min-w-0 flex-1 rounded-l border border-slate-300 px-2 py-1.5 dark:border-slate-600 dark:bg-slate-950" type="number" value={value} min={min} max={max} step={step} onChange={(event) => onChange(Number(event.target.value))} />
        {unit ? <span className="flex items-center rounded-r border border-l-0 border-slate-300 bg-slate-100 px-2 text-[10px] dark:border-slate-600 dark:bg-slate-800">{unit}</span> : null}
      </span>
    </label>
  );
}

function SelectControl({ label, value, options, translate = (option) => option, onChange }: { label: string; value: string; options: string[]; translate?: (value: string) => string; onChange: (value: string) => void }) {
  return (
    <label className="text-xs">
      <span className="mb-1 block font-medium">{label}</span>
      <select className="w-full rounded border border-slate-300 px-2 py-1.5 dark:border-slate-600 dark:bg-slate-950" value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => <option key={option} value={option}>{translate(option)}</option>)}
      </select>
    </label>
  );
}

function ColorControl({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  const normalized = /^#[0-9a-f]{6}$/i.test(value) ? value : "#000000";
  return (
    <label className="text-xs">
      <span className="mb-1 block font-medium">{label}</span>
      <span className="flex gap-2">
        <input type="color" className="h-8 w-10 rounded border border-slate-300" value={normalized} onChange={(event) => onChange(event.target.value.toUpperCase())} />
        <input className="min-w-0 flex-1 rounded border border-slate-300 px-2 py-1 font-mono dark:border-slate-600 dark:bg-slate-950" value={value} onChange={(event) => onChange(event.target.value)} />
      </span>
    </label>
  );
}
