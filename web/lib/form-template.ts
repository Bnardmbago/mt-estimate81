import { apiJson } from "@/lib/api";
import type { FormFieldSchema } from "@/lib/formSchema";

export type FormTemplateDetail = {
  id: string;
  name: string;
  description: string | null;
  fields: FormFieldSchema[];
  nature_of_work_category: string;
  language: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
};

export async function fetchFormTemplate(
  templateId: string,
  locale: string,
): Promise<FormTemplateDetail> {
  return apiJson<FormTemplateDetail>(`/form-templates/${templateId}`, {}, locale);
}
