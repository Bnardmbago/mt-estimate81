import type { FormFieldSchema } from "@/lib/formSchema";
import { getFieldLabel, splitSchemaBySection } from "@/lib/formSchema";

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
    lines.push(`${getFieldLabel(field, locale)}\n${value}`);
  }

  return lines.join("\n\n");
}
