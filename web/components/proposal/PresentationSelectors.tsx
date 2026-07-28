"use client";

import { useTranslations } from "next-intl";
import type { PresentationPresetSummary } from "@/lib/presentation";

export const NO_COVER_PRESET = "";

type PresentationSelectorsProps = {
  themes: PresentationPresetSummary[];
  styles: PresentationPresetSummary[];
  templates: PresentationPresetSummary[];
  themeId: string;
  styleId: string;
  templateId: string;
  coverPresetId?: string;
  onThemeChange: (id: string) => void;
  onStyleChange: (id: string) => void;
  onTemplateChange: (id: string) => void;
  onCoverPresetChange?: (id: string) => void;
  disabled?: boolean;
  compact?: boolean;
  showCoverPreset?: boolean;
};

function optionLabel(row: PresentationPresetSummary): string {
  return row.is_default ? `${row.name} (Default)` : row.name;
}

export function templateHasCover(row: PresentationPresetSummary): boolean {
  return Boolean(row.preview?.has_cover);
}

export default function PresentationSelectors({
  themes,
  styles,
  templates,
  themeId,
  styleId,
  templateId,
  coverPresetId = NO_COVER_PRESET,
  onThemeChange,
  onStyleChange,
  onTemplateChange,
  onCoverPresetChange,
  disabled = false,
  compact = false,
  showCoverPreset = false,
}: PresentationSelectorsProps) {
  const t = useTranslations("proposal.presentation");
  const coverPresets = templates.filter(templateHasCover);

  const selectClass =
    "w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-950";

  return (
    <div
      className={
        showCoverPreset
          ? compact
            ? "grid gap-2 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4"
            : "grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4"
          : compact
            ? "grid gap-2 md:grid-cols-3"
            : "grid gap-3 md:grid-cols-3"
      }
    >
      <label className="text-sm">
        <span className="mb-1 block text-slate-600 dark:text-slate-300">{t("theme")}</span>
        <select
          className={selectClass}
          value={themeId}
          disabled={disabled}
          onChange={(e) => onThemeChange(e.target.value)}
        >
          {themes.map((row) => (
            <option key={row.id} value={row.id}>
              {optionLabel(row)}
            </option>
          ))}
        </select>
        <span className="mt-1 block text-xs text-slate-500">{t("themeHelp")}</span>
      </label>
      <label className="text-sm">
        <span className="mb-1 block text-slate-600 dark:text-slate-300">{t("style")}</span>
        <select
          className={selectClass}
          value={styleId}
          disabled={disabled}
          onChange={(e) => onStyleChange(e.target.value)}
        >
          {styles.map((row) => (
            <option key={row.id} value={row.id}>
              {optionLabel(row)}
            </option>
          ))}
        </select>
        <span className="mt-1 block text-xs text-slate-500">{t("styleHelp")}</span>
      </label>
      <label className="text-sm">
        <span className="mb-1 block text-slate-600 dark:text-slate-300">{t("template")}</span>
        <select
          className={selectClass}
          value={templateId}
          disabled={disabled}
          onChange={(e) => onTemplateChange(e.target.value)}
        >
          {templates.map((row) => (
            <option key={row.id} value={row.id}>
              {optionLabel(row)}
            </option>
          ))}
        </select>
        <span className="mt-1 block text-xs text-slate-500">{t("templateHelp")}</span>
      </label>
      {showCoverPreset && onCoverPresetChange ? (
        <label className="text-sm">
          <span className="mb-1 block text-slate-600 dark:text-slate-300">{t("coverPreset")}</span>
          <select
            className={selectClass}
            value={coverPresetId}
            disabled={disabled}
            onChange={(e) => onCoverPresetChange(e.target.value)}
          >
            <option value={NO_COVER_PRESET}>{t("noCover")}</option>
            {coverPresets.map((row) => (
              <option key={row.id} value={row.id}>
                {optionLabel(row)}
              </option>
            ))}
          </select>
          <span className="mt-1 block text-xs text-slate-500">{t("coverPresetHelp")}</span>
        </label>
      ) : null}
    </div>
  );
}
