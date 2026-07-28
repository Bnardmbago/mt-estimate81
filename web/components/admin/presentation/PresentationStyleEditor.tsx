"use client";

import { useTranslations } from "next-intl";
import PresentationCatalogEditor from "./PresentationCatalogEditor";
import type { PresentationPresetDetail } from "@/lib/presentation";

const DEFAULT_STYLE = {
  margins: { top_mm: 18, right_mm: 16, bottom_mm: 18, left_mm: 16 },
  paragraph_spacing_em: 0.65,
  line_spacing: 1.4,
  base_font_size_pt: 10,
  heading_scale: { h1: 1.8, h2: 1.45, h3: 1.2 },
  list_indent_mm: 6,
  table_cell_padding_pt: 6,
  header_footer_font_size_pt: 9,
};

type Props = {
  presets: PresentationPresetDetail[];
  onChanged: () => Promise<void>;
};

export default function PresentationStyleEditor({ presets, onChanged }: Props) {
  const t = useTranslations("admin.presentation.fields");
  return (
    <PresentationCatalogEditor
      kind="styles"
      presets={presets}
      defaultConfig={DEFAULT_STYLE}
      onChanged={onChanged}
      fields={[
        { path: "margins.top_mm", label: t("marginTop"), type: "number", min: 0, step: 1 },
        { path: "margins.right_mm", label: t("marginRight"), type: "number", min: 0, step: 1 },
        { path: "margins.bottom_mm", label: t("marginBottom"), type: "number", min: 0, step: 1 },
        { path: "margins.left_mm", label: t("marginLeft"), type: "number", min: 0, step: 1 },
        {
          path: "paragraph_spacing_em",
          label: t("paragraphSpacing"),
          type: "number",
          min: 0,
          step: 0.05,
        },
        { path: "line_spacing", label: t("lineSpacing"), type: "number", min: 1, step: 0.05 },
        { path: "base_font_size_pt", label: t("baseFontSize"), type: "number", min: 6, step: 0.5 },
        { path: "heading_scale.h1", label: t("h1Scale"), type: "number", min: 1, step: 0.05 },
        { path: "heading_scale.h2", label: t("h2Scale"), type: "number", min: 1, step: 0.05 },
        { path: "heading_scale.h3", label: t("h3Scale"), type: "number", min: 1, step: 0.05 },
      ]}
    />
  );
}
