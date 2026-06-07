"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { apiJson } from "@/lib/api";
import type { EstimateDetail, FeatureItem } from "@/lib/estimate";

type FeatureItemEditorProps = {
  estimateId: string;
  initialItems: FeatureItem[];
};

type EditableFeatureItem = {
  id?: string;
  sort_order: number;
  name: string;
  description: string;
  hours: string;
  phase: string;
  role: string;
  is_ai_generated: boolean;
};

const inputClassName =
  "w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

function toEditable(item: FeatureItem, index: number): EditableFeatureItem {
  return {
    id: item.id,
    sort_order: item.sort_order ?? index,
    name: item.name,
    description: item.description ?? "",
    hours: String(item.hours),
    phase: item.phase,
    role: item.role,
    is_ai_generated: item.is_ai_generated,
  };
}

function createEmptyRow(index: number): EditableFeatureItem {
  return {
    sort_order: index,
    name: "",
    description: "",
    hours: "8",
    phase: "development",
    role: "developer",
    is_ai_generated: false,
  };
}

export default function FeatureItemEditor({
  estimateId,
  initialItems,
}: FeatureItemEditorProps) {
  const router = useRouter();
  const t = useTranslations("review");
  const [items, setItems] = useState<EditableFeatureItem[]>(
    initialItems.map((item, index) => toEditable(item, index)),
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setItems(initialItems.map((item, index) => toEditable(item, index)));
    setSaved(false);
    setError(null);
  }, [initialItems]);

  function updateItem(index: number, field: keyof EditableFeatureItem, value: string | boolean) {
    setItems((current) =>
      current.map((item, itemIndex) =>
        itemIndex === index ? { ...item, [field]: value } : item,
      ),
    );
    setSaved(false);
  }

  function addRow() {
    setItems((current) => [...current, createEmptyRow(current.length)]);
    setSaved(false);
  }

  function removeRow(index: number) {
    setItems((current) => current.filter((_, itemIndex) => itemIndex !== index));
    setSaved(false);
  }

  async function handleSave() {
    setSaving(true);
    setError(null);

    const payload = items
      .map((item, index) => ({
        id: item.id ?? null,
        sort_order: index,
        name: item.name.trim(),
        description: item.description.trim(),
        hours: Number(item.hours),
        phase: item.phase.trim(),
        role: item.role.trim(),
        is_ai_generated: item.is_ai_generated,
      }))
      .filter((item) => item.name && item.phase && item.role && item.hours > 0);

    if (payload.length === 0) {
      setError(t("featureItemsRequired"));
      setSaving(false);
      return;
    }

    try {
      await apiJson<EstimateDetail>(`/estimates/${estimateId}/feature-items`, {
        method: "PUT",
        body: JSON.stringify({ items: payload }),
      });
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
          <h2 className="text-lg font-semibold">{t("featuresTitle")}</h2>
          <p className="text-sm text-gray-500">{t("featuresDescription")}</p>
        </div>
        <div className="flex items-center gap-3">
          {saved && <span className="text-sm text-green-600">{t("saved")}</span>}
          <button
            type="button"
            onClick={addRow}
            className="rounded border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            {t("addRow")}
          </button>
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

      <div className="overflow-x-auto rounded-lg border border-gray-200">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left font-medium text-gray-700">{t("columns.name")}</th>
              <th className="px-3 py-2 text-left font-medium text-gray-700">
                {t("columns.hours")}
              </th>
              <th className="px-3 py-2 text-left font-medium text-gray-700">
                {t("columns.phase")}
              </th>
              <th className="px-3 py-2 text-left font-medium text-gray-700">{t("columns.role")}</th>
              <th className="px-3 py-2 text-left font-medium text-gray-700">
                {t("columns.description")}
              </th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {items.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-4 text-center text-gray-500">
                  {t("emptyFeatures")}
                </td>
              </tr>
            ) : (
              items.map((item, index) => (
                <tr key={item.id ?? `new-${index}`}>
                  <td className="px-3 py-2">
                    <input
                      type="text"
                      value={item.name}
                      onChange={(event) => updateItem(index, "name", event.target.value)}
                      className={inputClassName}
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="number"
                      min="0.5"
                      step="0.5"
                      value={item.hours}
                      onChange={(event) => updateItem(index, "hours", event.target.value)}
                      className={`${inputClassName} w-24`}
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="text"
                      value={item.phase}
                      onChange={(event) => updateItem(index, "phase", event.target.value)}
                      className={inputClassName}
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="text"
                      value={item.role}
                      onChange={(event) => updateItem(index, "role", event.target.value)}
                      className={inputClassName}
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="text"
                      value={item.description}
                      onChange={(event) => updateItem(index, "description", event.target.value)}
                      className={inputClassName}
                    />
                  </td>
                  <td className="px-3 py-2 text-right">
                    <button
                      type="button"
                      onClick={() => removeRow(index)}
                      className="rounded border border-red-200 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-50"
                    >
                      {t("remove")}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
