"use client";

import type { ReactNode } from "react";
import { useTranslations } from "next-intl";
import {
  accentHexColor,
  coerceAccentShapes,
  legacyAccentToShape,
  type AccentPageDimensions,
  type AccentShape,
} from "@/lib/cover-accent-shapes";
import { coverPageDimensions } from "@/lib/cover-preview-size";
import type { PresentationDraft, PresentationLocale } from "@/lib/presentation";
import PresentationCoverPreview, {
  type CoverDesign,
  type CoverField,
  type CoverPage,
} from "./PresentationCoverPreview";

type Props = {
  draft: PresentationDraft | null;
  locale: PresentationLocale;
  onClose: () => void;
};

const DEFAULT_DESIGN: CoverDesign = {
  alignment: "left",
  padding_mm: 24,
  accent: { enabled: true, width_mm: 48 },
  typography: { title_pt: 30, metadata_pt: 10 },
  colors: {},
  assets: [],
};

const noop = () => {};

export default function PresentationPresetSetPreview({ draft, locale, onClose }: Props) {
  const t = useTranslations("admin.presentation");
  if (!draft) return null;

  const config = configOf(draft.template_draft);
  const page = pageOf(config.page);
  const design = designOf(config.cover_design);
  const fields = fieldsOf(config.cover_fields);
  const pageMm = pageDimensionsMm(page);
  const shapes = shapesOf(design, pageMm);
  const themeAccent = resolveThemeAccent(draft, design);
  const coverEnabled =
    typeof config.cover === "boolean" ? config.cover : Boolean(config.cover ?? true);
  const title =
    String(draft.theme_draft.name || draft.template_draft.name || t("untitledDraft"));
  const themeColors = colorsOf(draft.theme_draft);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="preset-set-preview-title"
    >
      <div className="max-h-[90vh] w-full max-w-5xl overflow-y-auto rounded-xl bg-white p-5 shadow-xl dark:bg-slate-900">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="preset-set-preview-title" className="text-lg font-semibold">
              {t("setPreviewTitle")}
            </h2>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
              {title}
              <span className="ml-2 rounded bg-slate-100 px-2 py-0.5 text-xs dark:bg-slate-800">
                {draft.status}
              </span>
            </p>
          </div>
          <button type="button" className="header-btn-icon" aria-label={t("cover.close")} onClick={onClose}>
            ×
          </button>
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_16rem]">
          <PresentationCoverPreview
            assetOwnerId={draft.id}
            assetOwnerKind="draft"
            enabled={coverEnabled}
            page={page}
            design={design}
            fields={fields}
            shapes={shapes}
            themeAccent={themeAccent}
            locale={locale}
            previewUrls={{}}
            selectedLayerId={null}
            snapEnabled={false}
            readOnly
            onSnapEnabledChange={noop}
            onSelectLayer={noop}
            onFieldGeometryChange={noop}
            onAssetGeometryChange={noop}
            onShapeGeometryChange={noop}
            onDeleteAsset={noop}
            onDeleteShape={noop}
            onLayerOrder={noop}
            onEnableCover={noop}
          />

          <aside className="space-y-4 text-sm">
            <AxisSummary
              label={t("tabs.theme")}
              name={String(draft.theme_draft.name || t("untitledDraft"))}
              description={String(draft.theme_draft.description || "")}
            >
              <div className="mt-2 flex flex-wrap gap-2">
                {(["primary", "accent", "surface", "text_body"] as const).map((key) => {
                  const value = themeColors[key];
                  if (!value) return null;
                  return (
                    <span key={key} className="inline-flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-300">
                      <span
                        className="h-4 w-4 rounded border border-slate-300 dark:border-slate-600"
                        style={{ backgroundColor: `#${value.replace("#", "")}` }}
                        aria-hidden
                      />
                      {value.replace("#", "").toUpperCase()}
                    </span>
                  );
                })}
              </div>
            </AxisSummary>
            <AxisSummary
              label={t("tabs.style")}
              name={String(draft.style_draft.name || t("untitledDraft"))}
              description={String(draft.style_draft.description || "")}
            />
            <AxisSummary
              label={t("tabs.template")}
              name={String(draft.template_draft.name || t("untitledDraft"))}
              description={String(draft.template_draft.description || "")}
            >
              <p className="mt-2 text-xs text-slate-500">
                {page.size} · {t(`cover.${page.orientation}`)}
                {" · "}
                {coverEnabled ? t("cover.enabled") : t("cover.disabled")}
              </p>
            </AxisSummary>
          </aside>
        </div>

        <div className="mt-5 flex justify-end">
          <button type="button" className="header-btn" onClick={onClose}>
            {t("cover.close")}
          </button>
        </div>
      </div>
    </div>
  );
}

function AxisSummary({
  label,
  name,
  description,
  children,
}: {
  label: string;
  name: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <section className="rounded border border-slate-200 p-3 dark:border-slate-700">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</h3>
      <p className="mt-1 font-medium">{name}</p>
      {description ? <p className="mt-1 text-xs text-slate-500">{description}</p> : null}
      {children}
    </section>
  );
}

function configOf(payload: Record<string, unknown>): Record<string, unknown> {
  const config = payload.config;
  return config && typeof config === "object" && !Array.isArray(config)
    ? (config as Record<string, unknown>)
    : {};
}

function pageOf(value: unknown): CoverPage {
  const page = value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
  return {
    size: String(page.size || "A4"),
    orientation: page.orientation === "landscape" ? "landscape" : "portrait",
  };
}

function designOf(value: unknown): CoverDesign {
  const design = value && typeof value === "object" && !Array.isArray(value)
    ? (value as CoverDesign)
    : {};
  return {
    ...DEFAULT_DESIGN,
    ...design,
    accent: { ...DEFAULT_DESIGN.accent, ...design.accent },
    typography: { ...DEFAULT_DESIGN.typography, ...design.typography },
    colors: { ...DEFAULT_DESIGN.colors, ...design.colors },
    assets: design.assets ?? DEFAULT_DESIGN.assets ?? [],
  };
}

function fieldsOf(value: unknown): CoverField[] {
  return Array.isArray(value)
    ? value.filter((field): field is CoverField => Boolean(field && typeof field === "object"))
    : [];
}

function colorsOf(payload: Record<string, unknown>): Record<string, string> {
  const config = configOf(payload);
  const colors = config.colors;
  if (!colors || typeof colors !== "object" || Array.isArray(colors)) return {};
  return Object.fromEntries(
    Object.entries(colors as Record<string, unknown>)
      .filter(([, value]) => typeof value === "string" && value)
      .map(([key, value]) => [key, String(value)]),
  );
}

function pageDimensionsMm(page: CoverPage): AccentPageDimensions {
  const [width_mm, height_mm] = coverPageDimensions(page.size, page.orientation);
  return { width_mm, height_mm };
}

function shapesOf(design: CoverDesign, page: AccentPageDimensions): AccentShape[] {
  if (Array.isArray(design.accent_shapes)) return coerceAccentShapes(design.accent_shapes);
  const legacy = legacyAccentToShape(design.accent, page);
  return legacy ? [legacy] : [];
}

function resolveThemeAccent(draft: PresentationDraft, design: CoverDesign): string {
  const themeColors = colorsOf(draft.theme_draft);
  return (
    accentHexColor(themeColors.accent) ||
    accentHexColor(design.colors?.accent) ||
    "#2563eb"
  );
}
