"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { apiJson } from "@/lib/api";
import type { EstimateDetail, ExtractedData } from "@/lib/estimate";

type RequirementsReviewProps = {
  estimateId: string;
  initialData: ExtractedData;
};

type SectionKey = keyof Omit<ExtractedData, "confidence_notes">;

const LIST_SECTIONS: SectionKey[] = [
  "functional_requirements",
  "non_functional_requirements",
  "user_roles",
  "modules",
  "external_systems",
  "risks",
  "gaps",
];

const inputClassName =
  "w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

function emptyData(): ExtractedData {
  return {
    functional_requirements: [],
    non_functional_requirements: [],
    user_roles: [],
    modules: [],
    external_systems: [],
    risks: [],
    gaps: [],
    confidence_notes: "",
  };
}

export default function RequirementsReview({
  estimateId,
  initialData,
}: RequirementsReviewProps) {
  const router = useRouter();
  const t = useTranslations("review");
  const [data, setData] = useState<ExtractedData>({ ...emptyData(), ...initialData });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setData({ ...emptyData(), ...initialData });
    setSaved(false);
    setError(null);
  }, [initialData]);

  function updateListItem(section: SectionKey, index: number, value: string) {
    setData((current) => {
      const items = [...current[section]];
      items[index] = value;
      return { ...current, [section]: items };
    });
    setSaved(false);
  }

  function addListItem(section: SectionKey) {
    setData((current) => ({
      ...current,
      [section]: [...current[section], ""],
    }));
    setSaved(false);
  }

  function removeListItem(section: SectionKey, index: number) {
    setData((current) => ({
      ...current,
      [section]: current[section].filter((_, itemIndex) => itemIndex !== index),
    }));
    setSaved(false);
  }

  async function handleSave() {
    setSaving(true);
    setError(null);

    const payload = Object.fromEntries(
      Object.entries(data).map(([key, value]) => {
        if (Array.isArray(value)) {
          return [key, value.map((item) => item.trim()).filter(Boolean)];
        }
        return [key, typeof value === "string" ? value.trim() : value];
      }),
    ) as ExtractedData;

    try {
      await apiJson<EstimateDetail>(`/estimates/${estimateId}/extracted-data`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      setData(payload);
      setSaved(true);
      router.refresh();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : t("saveError"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="mt-8 border-t border-gray-200 pt-8">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold">{t("requirementsTitle")}</h2>
          <p className="text-sm text-gray-500">{t("requirementsDescription")}</p>
        </div>
        <div className="flex items-center gap-3">
          {saved && <span className="text-sm text-green-600">{t("saved")}</span>}
          <button
            type="button"
            onClick={() => void handleSave()}
            disabled={saving}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? t("saving") : t("save")}
          </button>
        </div>
      </div>

      {error && (
        <p className="mb-4 text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      <div className="space-y-6">
        {LIST_SECTIONS.map((section) => (
          <div key={section}>
            <div className="mb-2 flex items-center justify-between">
              <h3 className="text-sm font-medium text-gray-900">{t(`sections.${section}`)}</h3>
              <button
                type="button"
                onClick={() => addListItem(section)}
                className="text-xs font-medium text-blue-600 hover:text-blue-700"
              >
                {t("addItem")}
              </button>
            </div>
            <ul className="space-y-2">
              {data[section].length === 0 ? (
                <li className="text-sm text-gray-500">{t("emptySection")}</li>
              ) : (
                data[section].map((item, index) => (
                  <li key={`${section}-${index}`} className="flex gap-2">
                    <input
                      type="text"
                      value={item}
                      onChange={(event) => updateListItem(section, index, event.target.value)}
                      className={inputClassName}
                    />
                    <button
                      type="button"
                      onClick={() => removeListItem(section, index)}
                      className="shrink-0 rounded border border-red-200 px-2.5 py-2 text-xs font-medium text-red-700 hover:bg-red-50"
                    >
                      {t("remove")}
                    </button>
                  </li>
                ))
              )}
            </ul>
          </div>
        ))}

        <div>
          <h3 className="mb-2 text-sm font-medium text-gray-900">
            {t("sections.confidence_notes")}
          </h3>
          <textarea
            rows={3}
            value={data.confidence_notes}
            onChange={(event) => {
              setData((current) => ({ ...current, confidence_notes: event.target.value }));
              setSaved(false);
            }}
            className={`${inputClassName} resize-y min-h-[4rem]`}
          />
        </div>
      </div>
    </section>
  );
}
