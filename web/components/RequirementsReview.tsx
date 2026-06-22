"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { apiJson } from "@/lib/api";
import type { EstimateDetail, ExtractedData } from "@/lib/estimate-types";
import { resolveExtractedData } from "@/lib/resolveLocalizedContent";

type RequirementsReviewProps = {
  estimateId: string;
  estimateUpdatedAt: string;
  initialData: ExtractedData;
  contentLocale?: string;
  fallbackLocale?: string;
};

type ListSectionKey =
  | "functional_requirements"
  | "non_functional_requirements"
  | "user_roles"
  | "modules"
  | "external_systems"
  | "risks"
  | "gaps";

const LIST_SECTIONS: ListSectionKey[] = [
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

function hasAnyListItems(data: ExtractedData): boolean {
  return LIST_SECTIONS.some((section) => (data[section] ?? []).length > 0);
}

export default function RequirementsReview({
  estimateId,
  estimateUpdatedAt,
  initialData,
  contentLocale,
  fallbackLocale = "ja",
}: RequirementsReviewProps) {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("review");
  const displayLocale = contentLocale ?? locale;
  const resolvedSeed = resolveExtractedData(
    initialData as unknown as Record<string, unknown>,
    displayLocale,
    fallbackLocale,
  );
  const [data, setData] = useState<ExtractedData>(resolvedSeed);
  const [loading, setLoading] = useState(() => !hasAnyListItems(resolvedSeed));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadExtractedData() {
      setError(null);

      try {
        const latest = await apiJson<EstimateDetail>(
          `/estimates/${estimateId}?display_locale=${encodeURIComponent(displayLocale)}`,
          {},
          displayLocale,
        );
        if (cancelled) {
          return;
        }

        setData(
          resolveExtractedData(
            latest.extracted_data as Record<string, unknown> | null,
            displayLocale,
            latest.locale,
          ),
        );
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : t("loadError"));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadExtractedData();

    return () => {
      cancelled = true;
    };
  }, [estimateId, estimateUpdatedAt, displayLocale, fallbackLocale, t]);

  function updateListItem(section: ListSectionKey, index: number, value: string) {
    setData((current) => {
      const items = [...current[section]];
      items[index] = value;
      return { ...current, [section]: items };
    });
    setSaved(false);
  }

  function addListItem(section: ListSectionKey) {
    setData((current) => ({
      ...current,
      [section]: [...current[section], ""],
    }));
    setSaved(false);
  }

  function removeListItem(section: ListSectionKey, index: number) {
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
      await apiJson<EstimateDetail>(
        `/estimates/${estimateId}/extracted-data`,
        {
          method: "PATCH",
          body: JSON.stringify(payload),
        },
        displayLocale,
      );
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
            disabled={saving || loading}
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

      {!loading && !hasAnyListItems(data) && !data.confidence_notes.trim() && (
        <p className="mb-4 text-sm text-amber-700" role="status">
          {t("noRequirementsLoaded")}
        </p>
      )}

      {loading && !hasAnyListItems(data) ? (
        <p className="text-sm text-gray-500" role="status">
          {t("loadingRequirements")}
        </p>
      ) : (
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
      )}
    </section>
  );
}
