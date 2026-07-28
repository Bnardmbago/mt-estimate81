"use client";

import { useTranslations } from "next-intl";
import PresentationCatalogEditor from "./PresentationCatalogEditor";
import type { PresentationPresetDetail } from "@/lib/presentation";

const DEFAULT_TEMPLATE = {
  layout: "linear",
  cover: false,
  toc_style: "simple",
  section_chrome: "ruled",
  columns: 1,
  header_slot: "title",
  footer_slot: "page_number",
  page: { size: "A4", orientation: "portrait" },
  cover_fields: [],
  cover_design: {},
};

type Props = {
  presets: PresentationPresetDetail[];
  onChanged: () => Promise<void>;
};

export default function PresentationTemplateEditor({ presets, onChanged }: Props) {
  const t = useTranslations("admin.presentation.fields");
  return (
    <PresentationCatalogEditor
      kind="templates"
      presets={presets}
      defaultConfig={DEFAULT_TEMPLATE}
      onChanged={onChanged}
      fields={[
        {
          path: "layout",
          label: t("layout"),
          type: "select",
          options: [
            { value: "linear", label: t("layoutLinear") },
            { value: "executive", label: t("layoutExecutive") },
            { value: "two-column", label: t("layoutTwoColumn") },
          ],
        },
        { path: "cover", label: t("coverEnabled"), type: "checkbox" },
        {
          path: "section_chrome",
          label: t("sectionChrome"),
          type: "select",
          options: [
            { value: "none", label: t("chromeNone") },
            { value: "ruled", label: t("chromeRuled") },
            { value: "boxed", label: t("chromeBoxed") },
          ],
        },
        {
          path: "page.size",
          label: t("pageSize"),
          type: "select",
          options: ["A4", "A3", "Letter", "Legal"].map((value) => ({ value, label: value })),
        },
        {
          path: "page.orientation",
          label: t("orientation"),
          type: "select",
          options: [
            { value: "portrait", label: t("portrait") },
            { value: "landscape", label: t("landscape") },
          ],
        },
        {
          path: "columns",
          label: t("columns"),
          type: "number",
          min: 1,
          max: 2,
          step: 1,
        },
        { path: "header_slot", label: t("headerSlot") },
        { path: "footer_slot", label: t("footerSlot") },
      ]}
    />
  );
}
