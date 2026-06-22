import { FORM_FIELDS } from "@/lib/formFields";

export type LocalizedText = {
  en: string;
  ja: string;
};

export type SelectOptionSchema = {
  value: string;
  label: LocalizedText;
};

export type FormFieldSchema = {
  key: string;
  type: "text" | "textarea" | "select";
  required: boolean;
  sort_order: number;
  section?: "header" | "specification";
  label: LocalizedText;
  description?: LocalizedText;
  placeholder?: LocalizedText;
  options?: SelectOptionSchema[];
};

const LEGACY_LABELS: Record<string, LocalizedText> = {
  nature_of_work: { en: "Nature of work", ja: "作業の性質" },
  scope_boundaries: { en: "Scope boundaries", ja: "スコープ境界" },
  project_overview: { en: "Project overview", ja: "プロジェクト概要" },
  system_type: { en: "Type of system", ja: "システム種別" },
  business_domain: { en: "Business domain", ja: "業界・ドメイン" },
  main_functional_needs: { en: "Main functional needs", ja: "主要機能要件" },
  non_functional_needs: { en: "Non-functional needs", ja: "非機能要件" },
  users_and_load: { en: "Users and load", ja: "ユーザー数・負荷" },
  integrations: { en: "Connections to other systems", ja: "他システム連携" },
  data_complexity: { en: "Data complexity", ja: "データ複雑度" },
  ui_complexity: { en: "User interface complexity", ja: "UI複雑度" },
  technology_preferences: { en: "Technology preferences", ja: "技術的偏好" },
  development_approach: { en: "Development approach", ja: "開発アプローチ" },
  rules_and_standards: { en: "Rules and standards to follow", ja: "遵守ルール・標準" },
  team_and_resources: { en: "Team and resources", ja: "チーム・リソース" },
  development_location: { en: "Where development happens", ja: "開発拠点" },
  delivery_timing: { en: "Delivery timing", ja: "納期・スケジュール" },
  maintenance_support: { en: "Maintenance and support", ja: "保守・サポート" },
  risks_unknowns: { en: "Risks and unknowns", ja: "リスク・不明点" },
  budget: { en: "Budget", ja: "予算" },
};

const OPTION_LABELS: Record<string, LocalizedText> = {
  simple: { en: "Simple", ja: "シンプル" },
  moderate: { en: "Moderate", ja: "中程度" },
  complex: { en: "Complex", ja: "複雑" },
  low: { en: "Low", ja: "低" },
  medium: { en: "Medium", ja: "中" },
  high: { en: "High", ja: "高" },
  japan: { en: "Mainly in Japan", ja: "主に国内" },
  offshore: { en: "Mainly offshore", ja: "主にオフショア" },
  hybrid: { en: "Mix of Japan and offshore", ja: "国内とオフショアの混合" },
};

export type FormFieldValues = Record<string, string>;

export function resolveLocale(locale: string): "en" | "ja" {
  return locale === "ja" ? "ja" : "en";
}

export function getFieldLabel(field: FormFieldSchema, locale: string): string {
  const resolved = resolveLocale(locale);
  return field.label[resolved] || field.label.en || field.key;
}

export function getFieldPlaceholder(field: FormFieldSchema, locale: string): string {
  const resolved = resolveLocale(locale);
  return field.placeholder?.[resolved] || field.placeholder?.en || "";
}

export function getOptionLabel(option: SelectOptionSchema, locale: string): string {
  const resolved = resolveLocale(locale);
  return option.label[resolved] || option.label.en || option.value;
}

export function legacyFormFieldsToSchema(): FormFieldSchema[] {
  return FORM_FIELDS.filter((field) => field.key !== "project_name").map((field, index) => {
    const labels = LEGACY_LABELS[field.key] ?? { en: field.key, ja: field.key };
    const schema: FormFieldSchema = {
      key: field.key,
      type: field.type,
      required: field.required,
      sort_order: index * 10,
      label: labels,
      description: { en: "", ja: "" },
      placeholder: { en: "", ja: "" },
    };
    if (field.type === "select" && "options" in field) {
      schema.options = field.options.map((value) => ({
        value,
        label: OPTION_LABELS[value] ?? { en: value, ja: value },
      }));
    }
    return schema;
  });
}

export function resolveFormSchema(
  snapshot: FormFieldSchema[] | null | undefined,
): FormFieldSchema[] {
  if (!snapshot || snapshot.length === 0) {
    return legacyFormFieldsToSchema();
  }
  return [...snapshot].sort((a, b) => a.sort_order - b.sort_order);
}

export function splitSchemaBySection(schema: FormFieldSchema[]): {
  headerFields: FormFieldSchema[];
  specificationFields: FormFieldSchema[];
} {
  const sorted = resolveFormSchema(schema);
  return {
    headerFields: sorted.filter((field) => field.section === "header"),
    specificationFields: sorted.filter((field) => field.section !== "header"),
  };
}

export function specificationFieldKeys(schema: FormFieldSchema[]): Set<string> {
  return new Set(splitSchemaBySection(schema).specificationFields.map((field) => field.key));
}

export function isSchemaFieldRequired(
  field: FormFieldSchema,
  hasUploadedDocuments: boolean,
): boolean {
  if (hasUploadedDocuments) {
    return false;
  }
  return field.required;
}

export function validateFormValues(
  schema: FormFieldSchema[],
  values: FormFieldValues,
  hasUploadedDocuments: boolean,
  requiredMessage: string,
): Partial<Record<string, string>> {
  const errors: Partial<Record<string, string>> = {};

  for (const field of schema) {
    if (!isSchemaFieldRequired(field, hasUploadedDocuments)) {
      continue;
    }
    if (!values[field.key]?.trim()) {
      errors[field.key] = requiredMessage;
    }
  }

  if (!values.project_name?.trim()) {
    errors.project_name = requiredMessage;
  }

  return errors;
}

export function emptyFormValuesForSchema(schema: FormFieldSchema[]): FormFieldValues {
  const values: FormFieldValues = { project_name: "" };
  for (const field of schema) {
    values[field.key] = "";
  }
  return values;
}

export function formValuesFromSchema(
  schema: FormFieldSchema[],
  formData: Record<string, unknown> | null | undefined,
  projectName: string,
  displayProjectName: (name: string) => string,
): FormFieldValues {
  const values = emptyFormValuesForSchema(schema);
  values.project_name = displayProjectName(projectName);

  if (formData) {
    for (const field of schema) {
      const raw = formData[field.key];
      if (typeof raw === "string") {
        values[field.key] = raw;
      }
    }
  }

  return values;
}

export function schemaFieldLabels(
  schema: FormFieldSchema[],
  locale: string,
): Record<string, string> {
  return Object.fromEntries(
    schema.map((field) => [field.key, getFieldLabel(field, locale)]),
  );
}

export function slugifyFieldKey(label: string): string {
  const slug = label
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 50);
  if (!slug || !/^[a-z]/.test(slug)) {
    return `field_${Date.now().toString(36)}`;
  }
  return slug;
}
