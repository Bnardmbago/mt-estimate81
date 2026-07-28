"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { apiJson } from "@/lib/api";
import {
  NATURE_OF_WORK_CATEGORIES,
  type CategorizedTemplateOption,
  categorySortKey,
  getCategoryLabel,
} from "@/lib/formTemplateCategories";

const inputClassName =
  "w-full max-w-md rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

export default function NewEstimateForm() {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("estimates");
  const tFormTemplates = useTranslations("formTemplates");

  const [options, setOptions] = useState<CategorizedTemplateOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState("");
  const [selectedTemplateId, setSelectedTemplateId] = useState("");

  const loadOptions = useCallback(async () => {
    setError(null);
    try {
      const query = `?locale=${encodeURIComponent(locale)}`;
      const data = await apiJson<CategorizedTemplateOption[]>(
        `/form-templates/options${query}`,
        {},
        locale,
      );
      setOptions(data);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : t("createError"));
    } finally {
      setLoading(false);
    }
  }, [locale, t]);

  useEffect(() => {
    void loadOptions();
  }, [loadOptions]);

  const availableCategories = useMemo(() => {
    const seen = new Set(options.map((option) => option.nature_of_work_category));
    return NATURE_OF_WORK_CATEGORIES.filter((category) => seen.has(category));
  }, [options]);

  const templatesForCategory = useMemo(() => {
    if (!selectedCategory) {
      return [];
    }
    return options
      .filter((option) => option.nature_of_work_category === selectedCategory)
      .sort((a, b) => {
        if (a.is_default !== b.is_default) {
          return a.is_default ? -1 : 1;
        }
        return a.name.localeCompare(b.name);
      });
  }, [options, selectedCategory]);

  useEffect(() => {
    if (availableCategories.length === 0) {
      setSelectedCategory("");
      setSelectedTemplateId("");
      return;
    }

    setSelectedCategory((current) =>
      current && availableCategories.includes(current as (typeof availableCategories)[number])
        ? current
        : availableCategories[0],
    );
  }, [availableCategories]);

  useEffect(() => {
    if (templatesForCategory.length === 0) {
      setSelectedTemplateId("");
      return;
    }

    setSelectedTemplateId((current) => {
      if (current && templatesForCategory.some((template) => template.id === current)) {
        return current;
      }
      const preferred =
        templatesForCategory.find((template) => template.is_default) ?? templatesForCategory[0];
      return preferred.id;
    });
  }, [templatesForCategory]);

  function handleCreate() {
    if (!selectedTemplateId) {
      return;
    }

    setCreating(true);
    setError(null);
    router.push(
      `/${locale}/estimates/new/draft?template=${encodeURIComponent(selectedTemplateId)}`,
    );
  }

  if (loading) {
    return <p className="text-sm text-gray-500">{tFormTemplates("loading")}</p>;
  }

  if (options.length === 0) {
    return (
      <p className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
        {t("noTemplatesForLocale")}
      </p>
    );
  }

  return (
    <div
      data-tour="new-estimate-template-picker"
      className="max-w-lg space-y-5 rounded-lg border border-gray-200 bg-white p-6"
    >
      <div>
        <label htmlFor="new-estimate-category" className="mb-1 block text-sm font-medium">
          {t("natureOfWorkLabel")}
        </label>
        <select
          id="new-estimate-category"
          value={selectedCategory}
          disabled={creating}
          onChange={(event) => setSelectedCategory(event.target.value)}
          className={inputClassName}
        >
          {availableCategories
            .sort((a, b) => categorySortKey(a) - categorySortKey(b))
            .map((category) => (
              <option key={category} value={category}>
                {getCategoryLabel(category, locale)}
              </option>
            ))}
        </select>
      </div>

      <div>
        <label htmlFor="new-estimate-template" className="mb-1 block text-sm font-medium">
          {t("templateNameLabel")}
        </label>
        <select
          id="new-estimate-template"
          value={selectedTemplateId}
          disabled={creating || templatesForCategory.length === 0}
          onChange={(event) => setSelectedTemplateId(event.target.value)}
          className={inputClassName}
        >
          {templatesForCategory.map((template) => (
            <option key={template.id} value={template.id}>
              {template.name}
              {template.is_default ? ` (${tFormTemplates("defaultBadge")})` : ""}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      <button
        type="button"
        data-tour="new-estimate-create-button"
        onClick={handleCreate}
        disabled={creating || !selectedTemplateId}
        className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {creating ? t("creating") : t("createEstimate")}
      </button>
    </div>
  );
}
