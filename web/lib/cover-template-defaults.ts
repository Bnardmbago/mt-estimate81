/** Default template config used when creating a Cover preset in Admin. */

export const DEFAULT_COVER_TEMPLATE_CONFIG: Record<string, unknown> = {
  layout: "executive_cover",
  cover: true,
  page: { size: "A4", orientation: "portrait" },
  cover_fields: [
    {
      key: "title",
      emphasis: "title",
      required: false,
      auto_fill: "project_name",
      content: {
        _i18n: {
          en: { label: "Title", default_text: "Proposal title" },
          ja: { label: "タイトル", default_text: "提案書タイトル" },
        },
      },
    },
  ],
  cover_design: {
    alignment: "left",
    padding_mm: 24,
    accent_shapes: [
      {
        id: "default-left-stripe",
        name: "Left stripe",
        type: "rectangle",
        visible: true,
        locked: false,
        geometry: {
          x_pct: 0,
          y_pct: 0,
          width_pct: (48 / 210) * 100,
          height_pct: 100,
          rotation_deg: 0,
          z_index: 1,
        },
        fill: { mode: "theme", opacity: 0.9 },
        border: {
          enabled: false,
          color: "#000000",
          width_pt: 0,
          style: "solid",
          radius_pct: 0,
        },
        pattern: {
          type: "none",
          color: "#ffffff",
          scale: 1,
          spacing: 1,
          opacity: 0.25,
        },
      },
    ],
    typography: { title_pt: 30, metadata_pt: 10 },
    colors: {
      background: "FFFFFF",
      title: "1E3A5F",
      text: "334155",
      accent: "2563EB",
    },
    assets: [],
  },
  toc_style: "numbered",
  section_chrome: "minimal",
  columns: 1,
  header_slot: "title_logo",
  footer_slot: "page_number",
};

export function templateHasCoverConfig(config: Record<string, unknown> | undefined | null): boolean {
  return Boolean(config?.cover);
}
