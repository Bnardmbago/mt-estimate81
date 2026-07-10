"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { apiJson } from "@/lib/api";
import type { EstimateDetail, NrcRcAssumptions, NrcRcLineItem } from "@/lib/estimate-types";

type EstimateNrcRcPanelProps = {
  estimateId: string;
  estimateUpdatedAt: string;
  initialAssumptions: NrcRcAssumptions;
  complexityLevel?: "low" | "medium" | "high" | null;
  editable?: boolean;
};

const inputClassName =
  "w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

function emptyLineItem(): NrcRcLineItem {
  return { name: "", amount: 0 };
}

function normalizeAssumptions(value: NrcRcAssumptions | null | undefined): NrcRcAssumptions {
  return {
    setup_cost_items: (value?.setup_cost_items ?? []).map((item) => ({
      name: item.name,
      amount: item.amount ?? 0,
      category: item.category,
      service_description: item.service_description,
    })),
    monthly_rc_items: (value?.monthly_rc_items ?? []).map((item) => ({
      name: item.name,
      amount: item.amount ?? 0,
      category: item.category,
      service_description: item.service_description,
    })),
    source: value?.source ?? "derived",
    complexity_level: value?.complexity_level ?? null,
  };
}

export default function EstimateNrcRcPanel({
  estimateId,
  estimateUpdatedAt,
  initialAssumptions,
  complexityLevel,
  editable = true,
}: EstimateNrcRcPanelProps) {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("estimateNrcRc");
  const [assumptions, setAssumptions] = useState(() => normalizeAssumptions(initialAssumptions));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setAssumptions(normalizeAssumptions(initialAssumptions));
  }, [estimateUpdatedAt, initialAssumptions]);

  const setupTotal = useMemo(
    () => assumptions.setup_cost_items.reduce((sum, item) => sum + (item.amount || 0), 0),
    [assumptions.setup_cost_items],
  );
  const monthlyTotal = useMemo(
    () => assumptions.monthly_rc_items.reduce((sum, item) => sum + (item.amount || 0), 0),
    [assumptions.monthly_rc_items],
  );

  const sourceLabel = assumptions.source
    ? t(`source.${assumptions.source}`)
    : t("source.derived");
  const level = complexityLevel ?? assumptions.complexity_level;

  function updateSetupItem(index: number, field: "name" | "amount", value: string) {
    setAssumptions((current) => {
      const items = [...current.setup_cost_items];
      const row = { ...items[index] };
      if (field === "amount") {
        row.amount = Math.max(0, Number(value) || 0);
      } else {
        row.name = value;
      }
      items[index] = row;
      return { ...current, setup_cost_items: items };
    });
    setSaved(false);
  }

  function updateMonthlyItem(index: number, field: "name" | "amount", value: string) {
    setAssumptions((current) => {
      const items = [...current.monthly_rc_items];
      const row = { ...items[index] };
      if (field === "amount") {
        row.amount = Math.max(0, Number(value) || 0);
      } else {
        row.name = value;
      }
      items[index] = row;
      return { ...current, monthly_rc_items: items };
    });
    setSaved(false);
  }

  function addSetupItem() {
    setAssumptions((current) => ({
      ...current,
      setup_cost_items: [...current.setup_cost_items, emptyLineItem()],
    }));
    setSaved(false);
  }

  function addMonthlyItem() {
    setAssumptions((current) => ({
      ...current,
      monthly_rc_items: [...current.monthly_rc_items, emptyLineItem()],
    }));
    setSaved(false);
  }

  function removeSetupItem(index: number) {
    setAssumptions((current) => ({
      ...current,
      setup_cost_items: current.setup_cost_items.filter((_, itemIndex) => itemIndex !== index),
    }));
    setSaved(false);
  }

  function removeMonthlyItem(index: number) {
    setAssumptions((current) => ({
      ...current,
      monthly_rc_items: current.monthly_rc_items.filter((_, itemIndex) => itemIndex !== index),
    }));
    setSaved(false);
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const payload = {
        setup_cost_items: assumptions.setup_cost_items.filter((item) => item.name.trim()),
        monthly_rc_items: assumptions.monthly_rc_items.filter((item) => item.name.trim()),
        complexity_level: level ?? null,
      };
      await apiJson<EstimateDetail>(
        `/estimates/${estimateId}/nrc-rc-assumptions`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
        locale,
      );
      setSaved(true);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveError"));
    } finally {
      setSaving(false);
    }
  }

  if (
    assumptions.setup_cost_items.length === 0 &&
    assumptions.monthly_rc_items.length === 0
  ) {
    return null;
  }

  return (
    <section className="mb-8 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">{t("title")}</h2>
          <p className="mt-1 text-sm text-gray-500">{t("description")}</p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          {level ? (
            <span className="rounded-full bg-slate-100 px-2.5 py-1 font-medium text-slate-700">
              {t("complexity", { level: t(`complexityLevel.${level}`) })}
            </span>
          ) : null}
          <span className="rounded-full bg-blue-50 px-2.5 py-1 font-medium text-blue-700">
            {sourceLabel}
          </span>
        </div>
      </div>

      <div className="space-y-6">
        <div>
          <div className="mb-3 flex items-center justify-between gap-2">
            <h3 className="font-medium">{t("setupCosts")}</h3>
            {editable ? (
              <button
                type="button"
                onClick={addSetupItem}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                {t("addItem")}
              </button>
            ) : null}
          </div>
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-gray-700">{t("itemName")}</th>
                  <th className="px-3 py-2 text-left font-medium text-gray-700">{t("amount")}</th>
                  {editable ? <th className="px-3 py-2" /> : null}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {assumptions.setup_cost_items.map((item, index) => (
                  <tr key={`setup-${index}`}>
                    <td className="px-3 py-2">
                      {editable ? (
                        <input
                          type="text"
                          value={item.name}
                          onChange={(event) => updateSetupItem(index, "name", event.target.value)}
                          className={inputClassName}
                        />
                      ) : (
                        item.name
                      )}
                    </td>
                    <td className="px-3 py-2">
                      {editable ? (
                        <input
                          type="number"
                          min="0"
                          value={item.amount}
                          onChange={(event) => updateSetupItem(index, "amount", event.target.value)}
                          className={inputClassName}
                        />
                      ) : (
                        `¥${item.amount.toLocaleString()}`
                      )}
                    </td>
                    {editable ? (
                      <td className="px-3 py-2 text-right">
                        <button
                          type="button"
                          onClick={() => removeSetupItem(index)}
                          className="text-xs text-red-600 hover:text-red-800"
                        >
                          {t("removeItem")}
                        </button>
                      </td>
                    ) : null}
                  </tr>
                ))}
                <tr className="bg-gray-50 font-semibold">
                  <td className="px-3 py-2">{t("setupTotal")}</td>
                  <td className="px-3 py-2">¥{setupTotal.toLocaleString()}</td>
                  {editable ? <td /> : null}
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <div className="mb-3 flex items-center justify-between gap-2">
            <h3 className="font-medium">{t("monthlyRcItems")}</h3>
            {editable ? (
              <button
                type="button"
                onClick={addMonthlyItem}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                {t("addItem")}
              </button>
            ) : null}
          </div>
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-gray-700">{t("itemName")}</th>
                  <th className="px-3 py-2 text-left font-medium text-gray-700">{t("amount")}</th>
                  {editable ? <th className="px-3 py-2" /> : null}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {assumptions.monthly_rc_items.map((item, index) => (
                  <tr key={`monthly-${index}`}>
                    <td className="px-3 py-2">
                      {editable ? (
                        <input
                          type="text"
                          value={item.name}
                          onChange={(event) => updateMonthlyItem(index, "name", event.target.value)}
                          className={inputClassName}
                        />
                      ) : (
                        item.name
                      )}
                    </td>
                    <td className="px-3 py-2">
                      {editable ? (
                        <input
                          type="number"
                          min="0"
                          value={item.amount}
                          onChange={(event) =>
                            updateMonthlyItem(index, "amount", event.target.value)
                          }
                          className={inputClassName}
                        />
                      ) : (
                        `¥${item.amount.toLocaleString()}`
                      )}
                    </td>
                    {editable ? (
                      <td className="px-3 py-2 text-right">
                        <button
                          type="button"
                          onClick={() => removeMonthlyItem(index)}
                          className="text-xs text-red-600 hover:text-red-800"
                        >
                          {t("removeItem")}
                        </button>
                      </td>
                    ) : null}
                  </tr>
                ))}
                <tr className="bg-gray-50 font-semibold">
                  <td className="px-3 py-2">{t("monthlyTotal")}</td>
                  <td className="px-3 py-2">¥{monthlyTotal.toLocaleString()}</td>
                  {editable ? <td /> : null}
                </tr>
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-xs text-gray-500">{t("monthlyHint")}</p>
        </div>
      </div>

      {editable ? (
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => void handleSave()}
            disabled={saving}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {saving ? t("saving") : t("save")}
          </button>
          {saved ? <span className="text-sm text-green-700">{t("saved")}</span> : null}
          {error ? (
            <p className="text-sm text-red-600" role="alert">
              {error}
            </p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
