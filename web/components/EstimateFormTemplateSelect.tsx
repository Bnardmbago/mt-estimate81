"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { apiJson } from "@/lib/api";
import type { EstimateDetail } from "@/lib/estimate";
import {
  type CategorizedTemplateOption,
  getCategoryLabel,
  groupTemplatesByCategory,
} from "@/lib/formTemplateCategories";

type EstimateFormTemplateSelectProps = {
  estimate: EstimateDetail;
};

export default function EstimateFormTemplateSelect({
  estimate,
}: EstimateFormTemplateSelectProps) {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("formTemplates");

  const [options, setOptions] = useState<CategorizedTemplateOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentTemplateId = estimate.form_template_id ?? "";

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
      setError(loadError instanceof Error ? loadError.message : t("loadError"));
    } finally {
      setLoading(false);
    }
  }, [locale, t]);

  useEffect(() => {
    void loadOptions();
  }, [loadOptions]);

  const groupedOptions = useMemo(() => groupTemplatesByCategory(options), [options]);

  async function handleChange(templateId: string) {
    if (!templateId || templateId === currentTemplateId) {
      return;
    }

    setSaving(true);
    setError(null);

    try {
      await apiJson<EstimateDetail>(
        `/estimates/${estimate.id}`,
        {
          method: "PATCH",
          body: JSON.stringify({ form_template_id: templateId }),
        },
        locale,
      );
      router.refresh();
    } catch (changeError) {
      setError(changeError instanceof Error ? changeError.message : t("changeError"));
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <p className="mb-4 text-sm text-gray-500">{t("loading")}</p>;
  }

  if (options.length <= 1) {
    return null;
  }

  return (
    <div className="mb-5 rounded-lg border border-gray-200 bg-gray-50 p-4">
      <label htmlFor="form-template-select" className="mb-1 block text-sm font-medium">
        {t("selectLabel")}
      </label>
      <select
        id="form-template-select"
        value={currentTemplateId}
        disabled={saving}
        onChange={(event) => void handleChange(event.target.value)}
        className="w-full max-w-md rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
      >
        {groupedOptions.map((group) => (
          <optgroup
            key={group.category}
            label={getCategoryLabel(group.category, locale)}
          >
            {group.templates.map((option) => (
              <option key={option.id} value={option.id}>
                {option.name}
                {option.is_default ? ` (${t("defaultBadge")})` : ""}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
      <p className="mt-2 text-xs text-gray-600">{t("changeWarning")}</p>
      {error && (
        <p className="mt-2 text-sm text-red-600" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
