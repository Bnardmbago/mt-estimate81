"use client";

import { useTranslations } from "next-intl";
import type { CoverAsset } from "./PresentationCoverPreview";

type Props = {
  assets: CoverAsset[];
  busy: boolean;
  onUpload: (role: CoverAsset["role"], file: File) => Promise<void>;
  onChange: (role: CoverAsset["role"], patch: Partial<CoverAsset>) => void;
  onRemove: (role: CoverAsset["role"]) => void;
};

const ROLES: CoverAsset["role"][] = ["logo", "background", "decorative"];

export default function PresentationCoverAssetControls({
  assets,
  busy,
  onUpload,
  onChange,
  onRemove,
}: Props) {
  const t = useTranslations("admin.presentation.cover");

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
      <h3 className="text-sm font-semibold">{t("assets")}</h3>
      <div className="mt-3 space-y-4">
        {ROLES.map((role) => {
          const asset = assets.find((candidate) => candidate.role === role);
          return (
            <div key={role} className="rounded border border-slate-200 p-3 dark:border-slate-700">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="text-sm font-medium">{t(`assetRoles.${role}`)}</p>
                  <p className="text-xs text-slate-500">
                    {asset?.filename || (asset ? t("storedAsset") : t("noAsset"))}
                  </p>
                </div>
                <div className="flex gap-2">
                  <label className="header-btn cursor-pointer text-xs">
                    {asset ? t("replace") : t("upload")}
                    <input
                      className="hidden"
                      type="file"
                      accept="image/png,image/jpeg,image/webp,image/svg+xml"
                      disabled={busy}
                      onChange={(event) => {
                        const file = event.target.files?.[0];
                        if (file) void onUpload(role, file);
                        event.currentTarget.value = "";
                      }}
                    />
                  </label>
                  {asset ? (
                    <button
                      type="button"
                      className="header-btn text-xs text-red-700"
                      disabled={busy}
                      onClick={() => onRemove(role)}
                    >
                      {t("remove")}
                    </button>
                  ) : null}
                </div>
              </div>
              {asset ? (
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <SelectControl
                    label={t("position")}
                    value={asset.position || "custom"}
                    options={["custom", "top-left", "top-right", "center", "bottom-left", "bottom-right"]}
                    onChange={(position) => {
                      const coordinates = positionCoordinates(position);
                      onChange(role, { position, ...coordinates });
                    }}
                    translate={(value) => t(`positions.${value}`)}
                  />
                  {role === "background" ? (
                    <SelectControl
                      label={t("fit")}
                      value={asset.fit || "cover"}
                      options={["cover", "contain", "fill"]}
                      onChange={(fit) => onChange(role, { fit: fit as CoverAsset["fit"] })}
                      translate={(value) => t(`fitOptions.${value}`)}
                    />
                  ) : (
                    <RangeNumber
                      label={t("rotation")}
                      value={asset.rotation ?? 0}
                      min={-180}
                      max={180}
                      step={1}
                      unit="°"
                      onChange={(rotation) => onChange(role, { rotation })}
                    />
                  )}
                  <RangeNumber
                    label={t("xPosition")}
                    value={
                      asset.geometry
                        ? asset.geometry.x_pct + asset.geometry.width_pct / 2
                        : (asset.x ?? 50)
                    }
                    min={0}
                    max={100}
                    step={1}
                    unit="%"
                    onChange={(x) => onChange(role, { x, position: "custom" })}
                  />
                  <RangeNumber
                    label={t("yPosition")}
                    value={
                      asset.geometry
                        ? asset.geometry.y_pct + (asset.geometry.height_pct ?? 10) / 2
                        : (asset.y ?? 50)
                    }
                    min={0}
                    max={100}
                    step={1}
                    unit="%"
                    onChange={(y) => onChange(role, { y, position: "custom" })}
                  />
                  <RangeNumber
                    label={t("zoom")}
                    value={asset.zoom ?? 1}
                    min={0.1}
                    max={4}
                    step={0.1}
                    unit="×"
                    onChange={(zoom) => onChange(role, { zoom })}
                  />
                  <RangeNumber
                    label={t("opacity")}
                    value={asset.opacity ?? 1}
                    min={0}
                    max={1}
                    step={0.05}
                    unit=""
                    onChange={(opacity) => onChange(role, { opacity })}
                  />
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function RangeNumber({
  label,
  value,
  min,
  max,
  step,
  unit,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit: string;
  onChange: (value: number) => void;
}) {
  return (
    <label className="text-xs">
      <span className="mb-1 block font-medium">{label}</span>
      <div className="flex items-center gap-2">
        <input
          className="min-w-0 flex-1"
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(event) => onChange(Number(event.target.value))}
        />
        <input
          className="w-20 rounded border border-slate-300 px-2 py-1 dark:border-slate-600 dark:bg-slate-950"
          type="number"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(event) => onChange(Number(event.target.value))}
        />
        {unit ? <span className="w-4 text-slate-500">{unit}</span> : null}
      </div>
    </label>
  );
}

function SelectControl({
  label,
  value,
  options,
  onChange,
  translate,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
  translate: (value: string) => string;
}) {
  return (
    <label className="text-xs">
      <span className="mb-1 block font-medium">{label}</span>
      <select
        className="w-full rounded border border-slate-300 px-2 py-1.5 dark:border-slate-600 dark:bg-slate-950"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {options.map((option) => (
          <option key={option} value={option}>{translate(option)}</option>
        ))}
      </select>
    </label>
  );
}

function positionCoordinates(position: string): Pick<CoverAsset, "x" | "y"> {
  const positions: Record<string, [number, number]> = {
    "top-left": [15, 15],
    "top-right": [85, 15],
    center: [50, 50],
    "bottom-left": [15, 85],
    "bottom-right": [85, 85],
  };
  const [x, y] = positions[position] || [50, 50];
  return { x, y };
}
