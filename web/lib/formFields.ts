export const FORM_FIELDS = [
  { key: "project_name", required: true, type: "text" },
  { key: "nature_of_work", required: true, type: "textarea" },
  { key: "scope_boundaries", required: true, type: "textarea" },
  { key: "project_overview", required: true, type: "textarea" },
  { key: "system_type", required: true, type: "text" },
  { key: "business_domain", required: true, type: "text" },
  { key: "main_functional_needs", required: true, type: "textarea" },
  { key: "non_functional_needs", required: true, type: "textarea" },
  { key: "users_and_load", required: true, type: "textarea" },
  { key: "integrations", required: true, type: "textarea" },
  {
    key: "data_complexity",
    required: true,
    type: "select",
    options: ["low", "medium", "high"],
  },
  {
    key: "ui_complexity",
    required: true,
    type: "select",
    options: ["low", "medium", "high"],
  },
  { key: "technology_preferences", required: false, type: "textarea" },
  { key: "development_approach", required: true, type: "text" },
  { key: "rules_and_standards", required: true, type: "textarea" },
  { key: "team_and_resources", required: true, type: "textarea" },
  {
    key: "development_location",
    required: true,
    type: "select",
    options: ["japan", "offshore", "hybrid"],
  },
  { key: "delivery_timing", required: true, type: "textarea" },
  { key: "maintenance_support", required: true, type: "textarea" },
  { key: "risks_unknowns", required: true, type: "textarea" },
  { key: "budget", required: false, type: "text" },
] as const;

export type FormFieldDefinition = (typeof FORM_FIELDS)[number];

export type FormFieldKey = FormFieldDefinition["key"];

/** Project name is always required; other fields become optional when documents are uploaded. */
export function isFieldRequired(
  field: FormFieldDefinition,
  hasUploadedDocuments: boolean,
): boolean {
  if (field.key === "project_name") {
    return true;
  }
  if (hasUploadedDocuments) {
    return false;
  }
  return field.required;
}

export type FormFieldValues = Record<FormFieldKey, string>;

export const DEFAULT_PROJECT_NAMES = new Set(["New Estimate", "新規見積"]);

export function isUsableProjectName(name: string | null | undefined): boolean {
  const trimmed = (name ?? "").trim();
  return trimmed.length > 0 && !DEFAULT_PROJECT_NAMES.has(trimmed);
}

export function displayProjectName(projectName: string): string {
  return DEFAULT_PROJECT_NAMES.has(projectName) ? "" : projectName;
}

export function localizedProjectName(projectName: string | null | undefined, locale: string): string {
  const name = projectName ?? "";
  if (!DEFAULT_PROJECT_NAMES.has(name)) {
    return name;
  }
  return locale === "ja" ? "新規見積" : "New Estimate";
}

export function defaultProjectNameForLocale(locale: string): string {
  return locale === "ja" ? "新規見積" : "New Estimate";
}

/** Resolve the project name to persist or validate; placeholder defaults do not count as filled. */
export function resolveProjectNameForSave(
  formProjectName: string,
  storedProjectName: string,
): string {
  const trimmed = formProjectName.trim();
  if (isUsableProjectName(trimmed)) {
    return trimmed;
  }
  if (!trimmed && isUsableProjectName(storedProjectName)) {
    return storedProjectName.trim();
  }
  return "";
}

const DEFAULT_COMPLEXITY_VALUES: Partial<FormFieldValues> = {
  data_complexity: "low",
  ui_complexity: "low",
};

export function emptyFormValues(): FormFieldValues {
  return {
    ...Object.fromEntries(FORM_FIELDS.map((field) => [field.key, ""])),
    ...DEFAULT_COMPLEXITY_VALUES,
  } as FormFieldValues;
}

export function formValuesFromData(
  formData: Record<string, unknown> | null | undefined,
  projectName: string,
): FormFieldValues {
  const values = emptyFormValues();
  values.project_name = displayProjectName(projectName);

  if (formData) {
    for (const field of FORM_FIELDS) {
      if (field.key === "project_name") {
        continue;
      }
      const raw = formData[field.key];
      if (typeof raw === "string") {
        values[field.key] = raw;
      }
    }
  }

  return values;
}
