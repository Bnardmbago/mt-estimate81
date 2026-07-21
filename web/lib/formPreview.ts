import type { FormFieldSchema } from "@/lib/formSchema";
import { getFieldLabel, getOptionLabel, splitSchemaBySection } from "@/lib/formSchema";

function formatFieldDisplayValue(
  field: FormFieldSchema,
  value: string,
  locale: string,
): string {
  if (field.type === "select") {
    const option = (field.options ?? []).find((candidate) => candidate.value === value);
    if (option) {
      return getOptionLabel(option, locale);
    }
  }
  return value;
}

export function formatFormDataPreview(
  formData: Record<string, string>,
  schema: FormFieldSchema[],
  locale: string,
): string {
  const lines: string[] = [];
  const { specificationFields } = splitSchemaBySection(schema);

  for (const field of specificationFields) {
    const value = formData[field.key]?.trim();
    if (!value) {
      continue;
    }
    lines.push(`${getFieldLabel(field, locale)}\n${formatFieldDisplayValue(field, value, locale)}`);
  }

  return lines.join("\n\n");
}
