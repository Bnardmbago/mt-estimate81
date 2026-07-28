"use client";

import { useTranslations } from "next-intl";
import PresentationCatalogEditor from "./PresentationCatalogEditor";
import type { PresentationPresetDetail } from "@/lib/presentation";

const DEFAULT_THEME = {
  colors: {
    primary: "1E3A5F",
    primary_light: "E8EEF4",
    surface: "F8FAFC",
    border: "E2E8F0",
    text_body: "1E293B",
    text_muted: "64748B",
    accent: "2563EB",
    text_on_primary: "FFFFFF",
  },
  fonts: {
    heading: "Noto Sans JP, Helvetica, Arial, sans-serif",
    body: "Noto Sans JP, Helvetica, Arial, sans-serif",
  },
  watermark: false,
};

type Props = {
  presets: PresentationPresetDetail[];
  onChanged: () => Promise<void>;
};

export default function PresentationThemeEditor({ presets, onChanged }: Props) {
  const t = useTranslations("admin.presentation.fields");
  return (
    <PresentationCatalogEditor
      kind="themes"
      presets={presets}
      defaultConfig={DEFAULT_THEME}
      onChanged={onChanged}
      showLogo
      fields={[
        { path: "colors.primary", label: t("primaryColor"), type: "color" },
        { path: "colors.accent", label: t("accentColor"), type: "color" },
        { path: "colors.surface", label: t("surfaceColor"), type: "color" },
        { path: "colors.text_body", label: t("bodyColor"), type: "color" },
        { path: "fonts.heading", label: t("headingFont") },
        { path: "fonts.body", label: t("bodyFont") },
        { path: "watermark", label: t("watermark"), type: "checkbox" },
      ]}
    />
  );
}
