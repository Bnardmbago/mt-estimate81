export const NATURE_OF_WORK_CATEGORIES = [
  "new_build",
  "enhancement",
  "replacement",
  "migration",
  "integration",
  "general",
] as const;

export const TEMPLATE_LANGUAGES = ["en", "ja", "both"] as const;

export type NatureOfWorkCategory = (typeof NATURE_OF_WORK_CATEGORIES)[number];
export type TemplateLanguage = (typeof TEMPLATE_LANGUAGES)[number];

const NATURE_OF_WORK_LABELS: Record<NatureOfWorkCategory, { en: string; ja: string }> = {
  new_build: { en: "New build", ja: "新規開発" },
  enhancement: { en: "Enhancement", ja: "機能追加・改修" },
  replacement: { en: "Replacement", ja: "リプレース" },
  migration: { en: "Migration", ja: "移行" },
  integration: { en: "Integration", ja: "システム連携" },
  general: { en: "General", ja: "汎用" },
};

const TEMPLATE_LANGUAGE_LABELS: Record<TemplateLanguage, { en: string; ja: string }> = {
  en: { en: "English", ja: "英語" },
  ja: { en: "Japanese", ja: "日本語" },
  both: { en: "Bilingual", ja: "バイリンガル" },
};

export const DEFAULT_NATURE_OF_WORK_CATEGORY: NatureOfWorkCategory = "general";
export const DEFAULT_TEMPLATE_LANGUAGE: TemplateLanguage = "both";

export function resolveLocale(locale: string): "en" | "ja" {
  return locale === "ja" ? "ja" : "en";
}

export function getCategoryLabel(category: string, locale: string): string {
  const labels = NATURE_OF_WORK_LABELS[category as NatureOfWorkCategory];
  if (!labels) {
    return category;
  }
  const resolved = resolveLocale(locale);
  return labels[resolved] || labels.en;
}

export function getLanguageLabel(language: string, locale: string): string {
  const labels = TEMPLATE_LANGUAGE_LABELS[language as TemplateLanguage];
  if (!labels) {
    return language;
  }
  const resolved = resolveLocale(locale);
  return labels[resolved] || labels.en;
}

export function categorySortKey(category: string): number {
  const index = NATURE_OF_WORK_CATEGORIES.indexOf(category as NatureOfWorkCategory);
  return index === -1 ? NATURE_OF_WORK_CATEGORIES.length : index;
}

export type CategorizedTemplateOption = {
  id: string;
  name: string;
  is_default: boolean;
  nature_of_work_category: string;
  language: string;
};

export function groupTemplatesByCategory<T extends CategorizedTemplateOption>(
  templates: T[],
): Array<{ category: string; templates: T[] }> {
  const grouped = new Map<string, T[]>();

  for (const template of templates) {
    const category = template.nature_of_work_category || DEFAULT_NATURE_OF_WORK_CATEGORY;
    const bucket = grouped.get(category) ?? [];
    bucket.push(template);
    grouped.set(category, bucket);
  }

  return [...grouped.entries()]
    .sort(([a], [b]) => categorySortKey(a) - categorySortKey(b))
    .map(([category, items]) => ({
      category,
      templates: [...items].sort((a, b) => {
        if (a.is_default !== b.is_default) {
          return a.is_default ? -1 : 1;
        }
        return a.name.localeCompare(b.name);
      }),
    }));
}
