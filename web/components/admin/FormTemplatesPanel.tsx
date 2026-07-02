"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { apiFetch, apiJson } from "@/lib/api";
import {
  DEFAULT_NATURE_OF_WORK_CATEGORY,
  DEFAULT_TEMPLATE_LANGUAGE,
  NATURE_OF_WORK_CATEGORIES,
  TEMPLATE_LANGUAGES,
  getCategoryLabel,
  getLanguageLabel,
} from "@/lib/formTemplateCategories";
import type { FormFieldSchema, LocalizedText, SelectOptionSchema } from "@/lib/formSchema";
import { legacyFormFieldsToSchema, slugifyFieldKey } from "@/lib/formSchema";

type TemplateSummary = {
  id: string;
  name: string;
  description: string | null;
  nature_of_work_category: string;
  language: string;
  is_default: boolean;
  field_count: number;
};

type TemplateDetail = TemplateSummary & {
  fields: FormFieldSchema[];
  created_at: string;
  updated_at: string;
};

type TemplateForm = {
  name: string;
  description: string;
  nature_of_work_category: string;
  language: string;
  is_default: boolean;
};

const inputClassName =
  "w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

const FIELD_TYPES = ["text", "textarea", "select", "number", "currency"] as const;

function emptyLocalized(): LocalizedText {
  return { en: "", ja: "" };
}

function newField(sortOrder: number): FormFieldSchema {
  const key = `custom_${Date.now().toString(36)}`;
  return {
    key,
    type: "textarea",
    required: true,
    sort_order: sortOrder,
    label: emptyLocalized(),
    description: emptyLocalized(),
    placeholder: emptyLocalized(),
    options: [],
  };
}

function normalizeFields(fields: FormFieldSchema[]): FormFieldSchema[] {
  return fields.map((field, index) => ({
    ...field,
    sort_order: index * 10,
    options: field.type === "select" ? field.options ?? [] : [],
  }));
}

export default function FormTemplatesPanel() {
  const locale = useLocale();
  const t = useTranslations("admin.formTemplates");

  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<TemplateDetail | null>(null);
  const [fields, setFields] = useState<FormFieldSchema[]>([]);
  const [form, setForm] = useState<TemplateForm>({
    name: "",
    description: "",
    nature_of_work_category: DEFAULT_NATURE_OF_WORK_CATEGORY,
    language: DEFAULT_TEMPLATE_LANGUAGE,
    is_default: false,
  });
  const [filterCategory, setFilterCategory] = useState<string>("");
  const [filterLanguage, setFilterLanguage] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [duplicating, setDuplicating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingFieldIndex, setEditingFieldIndex] = useState<number | null>(null);
  const [confirmRemoveIndex, setConfirmRemoveIndex] = useState<number | null>(null);

  const loadTemplates = useCallback(async () => {
    setError(null);
    try {
      const data = await apiJson<TemplateSummary[]>("/admin/form-templates");
      setTemplates(data);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : t("loadError"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  const loadDetail = useCallback(
    async (templateId: string) => {
      setError(null);
      try {
        const data = await apiJson<TemplateDetail>(`/admin/form-templates/${templateId}`);
        setDetail(data);
        setForm({
          name: data.name,
          description: data.description ?? "",
          nature_of_work_category: data.nature_of_work_category,
          language: data.language,
          is_default: data.is_default,
        });
        setFields(data.fields);
        setSelectedId(templateId);
        setEditingFieldIndex(null);
        setConfirmRemoveIndex(null);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : t("loadError"));
      }
    },
    [t],
  );

  useEffect(() => {
    void loadTemplates();
  }, [loadTemplates]);

  function startCreate() {
    setSelectedId(null);
    setDetail(null);
    setForm({
      name: "",
      description: "",
      nature_of_work_category: DEFAULT_NATURE_OF_WORK_CATEGORY,
      language: DEFAULT_TEMPLATE_LANGUAGE,
      is_default: false,
    });
    setFields(legacyFormFieldsToSchema());
    setEditingFieldIndex(null);
    setConfirmRemoveIndex(null);
    setCreating(true);
  }

  function updateFieldAt(index: number, patch: Partial<FormFieldSchema>) {
    setFields((current) =>
      current.map((field, fieldIndex) =>
        fieldIndex === index ? { ...field, ...patch } : field,
      ),
    );
  }

  function updateFieldLabel(index: number, locale: keyof LocalizedText, value: string) {
    setFields((current) =>
      current.map((field, fieldIndex) => {
        if (fieldIndex !== index) {
          return field;
        }
        const nextLabel = { ...field.label, [locale]: value };
        const nextKey =
          field.key.startsWith("custom_") && locale === "en" && value.trim()
            ? slugifyFieldKey(value)
            : field.key;
        return { ...field, label: nextLabel, key: nextKey };
      }),
    );
  }

  function moveField(index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= fields.length) {
      return;
    }
    setFields((current) => {
      const next = [...current];
      const [item] = next.splice(index, 1);
      next.splice(target, 0, item);
      return normalizeFields(next);
    });
    setEditingFieldIndex(target);
  }

  function addField() {
    setFields((current) => normalizeFields([...current, newField(current.length * 10)]));
    setEditingFieldIndex(fields.length);
  }

  function removeField(index: number) {
    setFields((current) => normalizeFields(current.filter((_, fieldIndex) => fieldIndex !== index)));
    setConfirmRemoveIndex(null);
    setEditingFieldIndex(null);
  }

  function addSelectOption(index: number) {
    const option: SelectOptionSchema = {
      value: `option_${fields[index]?.options?.length ?? 0}`,
      label: emptyLocalized(),
    };
    setFields((current) =>
      current.map((field, fieldIndex) =>
        fieldIndex === index
          ? { ...field, options: [...(field.options ?? []), option] }
          : field,
      ),
    );
  }

  function updateSelectOption(
    fieldIndex: number,
    optionIndex: number,
    patch: Partial<SelectOptionSchema>,
  ) {
    setFields((current) =>
      current.map((field, index) => {
        if (index !== fieldIndex) {
          return field;
        }
        const options = (field.options ?? []).map((option, optIndex) =>
          optIndex === optionIndex ? { ...option, ...patch } : option,
        );
        return { ...field, options };
      }),
    );
  }

  async function handleSave(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);

    const payload = {
      name: form.name.trim(),
      description: form.description.trim() || null,
      nature_of_work_category: form.nature_of_work_category,
      language: form.language,
      is_default: form.is_default,
      fields: normalizeFields(fields),
    };

    try {
      if (selectedId) {
        await apiJson(`/admin/form-templates/${selectedId}`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        });
      } else {
        const created = await apiJson<TemplateDetail>("/admin/form-templates", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        setSelectedId(created.id);
        setCreating(false);
      }
      await loadTemplates();
      if (selectedId) {
        await loadDetail(selectedId);
      }
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : t("saveError"));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!selectedId || detail?.is_default) {
      return;
    }
    if (!window.confirm(t("deleteConfirm"))) {
      return;
    }

    setDeleting(true);
    setError(null);
    try {
      const response = await apiFetch(`/admin/form-templates/${selectedId}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        throw new Error(t("deleteError"));
      }
      setSelectedId(null);
      setDetail(null);
      setCreating(false);
      await loadTemplates();
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : t("deleteError"));
    } finally {
      setDeleting(false);
    }
  }

  async function handleDuplicate() {
    if (!selectedId) {
      return;
    }
    setDuplicating(true);
    setError(null);
    try {
      const duplicated = await apiJson<TemplateDetail>(
        `/admin/form-templates/${selectedId}/duplicate`,
        { method: "POST" },
      );
      await loadTemplates();
      await loadDetail(duplicated.id);
      setCreating(false);
    } catch (duplicateError) {
      setError(duplicateError instanceof Error ? duplicateError.message : t("duplicateError"));
    } finally {
      setDuplicating(false);
    }
  }

  const filteredTemplates = useMemo(() => {
    return templates.filter((template) => {
      if (filterCategory && template.nature_of_work_category !== filterCategory) {
        return false;
      }
      if (filterLanguage && template.language !== filterLanguage) {
        return false;
      }
      return true;
    });
  }, [filterCategory, filterLanguage, templates]);

  if (loading) {
    return <p className="text-sm text-gray-500">{t("loading")}</p>;
  }

  return (
    <div className="space-y-6">
      {error && (
        <p className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
          {error}
        </p>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">{t("title")}</h2>
        <button
          type="button"
          onClick={startCreate}
          className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
        >
          {t("create")}
        </button>
      </div>

      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        <div className="rounded border border-gray-200">
          <div className="border-b border-gray-200 px-3 py-2 text-sm font-medium">{t("listTitle")}</div>
          <div className="space-y-2 border-b border-gray-200 px-3 py-2">
            <select
              className={inputClassName}
              value={filterCategory}
              onChange={(event) => setFilterCategory(event.target.value)}
            >
              <option value="">{t("filterAllCategories")}</option>
              {NATURE_OF_WORK_CATEGORIES.map((category) => (
                <option key={category} value={category}>
                  {getCategoryLabel(category, locale)}
                </option>
              ))}
            </select>
            <select
              className={inputClassName}
              value={filterLanguage}
              onChange={(event) => setFilterLanguage(event.target.value)}
            >
              <option value="">{t("filterAllLanguages")}</option>
              {TEMPLATE_LANGUAGES.map((language) => (
                <option key={language} value={language}>
                  {getLanguageLabel(language, locale)}
                </option>
              ))}
            </select>
          </div>
          <ul className="divide-y divide-gray-100">
            {filteredTemplates.map((template) => (
              <li key={template.id}>
                <button
                  type="button"
                  onClick={() => {
                    setCreating(false);
                    void loadDetail(template.id);
                  }}
                  className={`w-full px-3 py-2 text-left text-sm hover:bg-gray-50 ${
                    selectedId === template.id ? "bg-blue-50 text-blue-700" : ""
                  }`}
                >
                  <div className="font-medium">{template.name}</div>
                  <div className="text-xs text-gray-500">
                    {getCategoryLabel(template.nature_of_work_category, locale)}
                    {" · "}
                    {getLanguageLabel(template.language, locale)}
                    {" · "}
                    {t("fieldCount", { count: template.field_count })}
                    {template.is_default ? ` · ${t("defaultBadge")}` : ""}
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </div>

        {(selectedId || creating) && (
          <form onSubmit={handleSave} className="space-y-5 rounded border border-gray-200 p-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium">{t("name")}</label>
                <input
                  className={inputClassName}
                  value={form.name}
                  onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                  required
                />
              </div>
              <div className="flex items-end">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={form.is_default}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, is_default: event.target.checked }))
                    }
                  />
                  {t("isDefault")}
                </label>
              </div>
              <div className="sm:col-span-2">
                <label className="mb-1 block text-sm font-medium">{t("description")}</label>
                <input
                  className={inputClassName}
                  value={form.description}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, description: event.target.value }))
                  }
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">{t("categoryLabel")}</label>
                <select
                  className={inputClassName}
                  value={form.nature_of_work_category}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      nature_of_work_category: event.target.value,
                    }))
                  }
                  required
                >
                  {NATURE_OF_WORK_CATEGORIES.map((category) => (
                    <option key={category} value={category}>
                      {getCategoryLabel(category, locale)}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">{t("languageLabel")}</label>
                <select
                  className={inputClassName}
                  value={form.language}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, language: event.target.value }))
                  }
                  required
                >
                  {TEMPLATE_LANGUAGES.map((language) => (
                    <option key={language} value={language}>
                      {getLanguageLabel(language, locale)}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-sm font-semibold">{t("fieldsTitle")}</h3>
                <button
                  type="button"
                  onClick={addField}
                  className="rounded border border-gray-300 px-2 py-1 text-xs hover:bg-gray-50"
                >
                  {t("addField")}
                </button>
              </div>

              <div className="space-y-3">
                {fields.map((field, index) => (
                  <div key={`${field.key}-${index}`} className="rounded border border-gray-200 p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="text-sm font-medium">
                        {field.label.en || field.key}
                        <span className="ml-2 text-xs text-gray-500">({field.key})</span>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        <button
                          type="button"
                          onClick={() => moveField(index, -1)}
                          disabled={index === 0}
                          className="rounded border px-2 py-0.5 text-xs disabled:opacity-40"
                        >
                          ↑
                        </button>
                        <button
                          type="button"
                          onClick={() => moveField(index, 1)}
                          disabled={index === fields.length - 1}
                          className="rounded border px-2 py-0.5 text-xs disabled:opacity-40"
                        >
                          ↓
                        </button>
                        <button
                          type="button"
                          onClick={() =>
                            setEditingFieldIndex(editingFieldIndex === index ? null : index)
                          }
                          className="rounded border px-2 py-0.5 text-xs"
                        >
                          {editingFieldIndex === index ? t("collapse") : t("edit")}
                        </button>
                        <button
                          type="button"
                          onClick={() => setConfirmRemoveIndex(index)}
                          className="rounded border border-red-200 px-2 py-0.5 text-xs text-red-700"
                        >
                          {t("remove")}
                        </button>
                      </div>
                    </div>

                    {confirmRemoveIndex === index && (
                      <div className="mt-2 rounded bg-red-50 p-2 text-xs text-red-800">
                        <p>{t("removeConfirm")}</p>
                        <div className="mt-2 flex gap-2">
                          <button
                            type="button"
                            onClick={() => removeField(index)}
                            className="rounded bg-red-600 px-2 py-1 text-white"
                          >
                            {t("confirmRemove")}
                          </button>
                          <button
                            type="button"
                            onClick={() => setConfirmRemoveIndex(null)}
                            className="rounded border px-2 py-1"
                          >
                            {t("cancel")}
                          </button>
                        </div>
                      </div>
                    )}

                    {editingFieldIndex === index && (
                      <div className="mt-3 grid gap-3 sm:grid-cols-2">
                        <div>
                          <label className="mb-1 block text-xs font-medium">{t("fieldKey")}</label>
                          <input
                            className={inputClassName}
                            value={field.key}
                            onChange={(event) => updateFieldAt(index, { key: event.target.value })}
                          />
                        </div>
                        <div>
                          <label className="mb-1 block text-xs font-medium">{t("fieldType")}</label>
                          <select
                            className={inputClassName}
                            value={field.type}
                            onChange={(event) =>
                              updateFieldAt(index, {
                                type: event.target.value as FormFieldSchema["type"],
                                options: event.target.value === "select" ? field.options ?? [] : [],
                              })
                            }
                          >
                            {FIELD_TYPES.map((type) => (
                              <option key={type} value={type}>
                                {t(`fieldTypes.${type}`)}
                              </option>
                            ))}
                          </select>
                        </div>
                        <div>
                          <label className="mb-1 block text-xs font-medium">{t("labelEn")}</label>
                          <input
                            className={inputClassName}
                            value={field.label.en}
                            onChange={(event) => updateFieldLabel(index, "en", event.target.value)}
                          />
                        </div>
                        <div>
                          <label className="mb-1 block text-xs font-medium">{t("labelJa")}</label>
                          <input
                            className={inputClassName}
                            value={field.label.ja}
                            onChange={(event) => updateFieldLabel(index, "ja", event.target.value)}
                          />
                        </div>
                        <div className="flex items-center sm:col-span-2">
                          <label className="flex items-center gap-2 text-xs">
                            <input
                              type="checkbox"
                              checked={field.required}
                              onChange={(event) =>
                                updateFieldAt(index, { required: event.target.checked })
                              }
                            />
                            {t("required")}
                          </label>
                        </div>

                        {field.type === "select" && (
                          <div className="space-y-2 sm:col-span-2">
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-medium">{t("selectOptions")}</span>
                              <button
                                type="button"
                                onClick={() => addSelectOption(index)}
                                className="rounded border px-2 py-0.5 text-xs"
                              >
                                {t("addOption")}
                              </button>
                            </div>
                            {(field.options ?? []).map((option, optionIndex) => (
                              <div key={optionIndex} className="grid gap-2 sm:grid-cols-3">
                                <input
                                  className={inputClassName}
                                  value={option.value}
                                  placeholder={t("optionValue")}
                                  onChange={(event) =>
                                    updateSelectOption(index, optionIndex, {
                                      value: event.target.value,
                                    })
                                  }
                                />
                                <input
                                  className={inputClassName}
                                  value={option.label.en}
                                  placeholder={t("labelEn")}
                                  onChange={(event) =>
                                    updateSelectOption(index, optionIndex, {
                                      label: { ...option.label, en: event.target.value },
                                    })
                                  }
                                />
                                <input
                                  className={inputClassName}
                                  value={option.label.ja}
                                  placeholder={t("labelJa")}
                                  onChange={(event) =>
                                    updateSelectOption(index, optionIndex, {
                                      label: { ...option.label, ja: event.target.value },
                                    })
                                  }
                                />
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <button
                type="submit"
                disabled={saving}
                className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? t("saving") : t("save")}
              </button>
              {selectedId && (
                <>
                  <button
                    type="button"
                    disabled={duplicating}
                    onClick={() => void handleDuplicate()}
                    className="rounded border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50 disabled:opacity-50"
                  >
                    {duplicating ? t("duplicating") : t("duplicate")}
                  </button>
                  <button
                    type="button"
                    disabled={deleting || detail?.is_default}
                    onClick={() => void handleDelete()}
                    className="rounded border border-red-300 px-4 py-2 text-sm text-red-700 hover:bg-red-50 disabled:opacity-50"
                  >
                    {deleting ? t("deleting") : t("delete")}
                  </button>
                </>
              )}
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
