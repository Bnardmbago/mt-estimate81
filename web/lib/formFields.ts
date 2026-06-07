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
    options: ["simple", "moderate", "complex"],
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

export type FormFieldKey = (typeof FORM_FIELDS)[number]["key"];

export type FormFieldValues = Record<FormFieldKey, string>;

export function emptyFormValues(): FormFieldValues {
  return Object.fromEntries(
    FORM_FIELDS.map((field) => [field.key, ""]),
  ) as FormFieldValues;
}

export function formValuesFromData(
  formData: Record<string, unknown> | null | undefined,
  projectName: string,
): FormFieldValues {
  const values = emptyFormValues();
  values.project_name = projectName;

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
