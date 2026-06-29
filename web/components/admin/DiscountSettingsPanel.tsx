"use client";

import { FormEvent, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { apiJson } from "@/lib/api";

type DiscountSettings = {
  estimate_discount_rate: number;
  estimate_markup_rate: number;
};

const inputClassName =
  "w-full max-w-xs rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

export default function DiscountSettingsPanel() {
  const t = useTranslations("admin.discountSettings");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [discountRatePercent, setDiscountRatePercent] = useState("30");
  const [markupRatePercent, setMarkupRatePercent] = useState("30");

  useEffect(() => {
    async function load() {
      try {
        const data = await apiJson<DiscountSettings>("/admin/discount-settings");
        setDiscountRatePercent(String(Math.round(data.estimate_discount_rate * 100)));
        setMarkupRatePercent(String(Math.round(data.estimate_markup_rate * 100)));
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : t("loadError"));
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [t]);

  function parseRatePercent(value: string): number | null {
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed < 0 || parsed > 100 || !Number.isInteger(parsed)) {
      return null;
    }
    return parsed;
  }

  async function handleSave(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setSaved(false);

    const discountParsed = parseRatePercent(discountRatePercent);
    const markupParsed = parseRatePercent(markupRatePercent);
    if (discountParsed === null || markupParsed === null) {
      setError(t("invalidRate"));
      setSaving(false);
      return;
    }

    try {
      const data = await apiJson<DiscountSettings>("/admin/discount-settings", {
        method: "PATCH",
        body: JSON.stringify({
          estimate_discount_rate: discountParsed / 100,
          estimate_markup_rate: markupParsed / 100,
        }),
      });
      setDiscountRatePercent(String(Math.round(data.estimate_discount_rate * 100)));
      setMarkupRatePercent(String(Math.round(data.estimate_markup_rate * 100)));
      setSaved(true);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : t("saveError"));
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <p className="text-sm text-gray-500">{t("loading")}</p>;
  }

  return (
    <form onSubmit={handleSave} className="space-y-6">
      <p className="text-sm text-gray-600">{t("description")}</p>

      <div className="space-y-4 rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/50">
        <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
          {t("discountSectionTitle")}
        </h3>
        <div>
          <label htmlFor="discount-rate" className="mb-1 block text-sm font-medium text-gray-700">
            {t("rateLabel")}
          </label>
          <div className="flex items-center gap-2">
            <input
              id="discount-rate"
              type="number"
              min={0}
              max={100}
              step={1}
              value={discountRatePercent}
              onChange={(event) => setDiscountRatePercent(event.target.value)}
              className={inputClassName}
            />
            <span className="text-sm text-gray-600">%</span>
          </div>
          <p className="mt-1 text-xs text-gray-500">{t("rateHint")}</p>
        </div>
        <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-400">
          {t("applicationIntro")}
        </p>
        <ul className="list-disc space-y-1.5 pl-5 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
          {(t.raw("applicationPoints") as string[]).map((point) => (
            <li key={point}>{point}</li>
          ))}
        </ul>
      </div>

      <div className="space-y-4 rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/50">
        <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
          {t("markupSectionTitle")}
        </h3>
        <div>
          <label htmlFor="markup-rate" className="mb-1 block text-sm font-medium text-gray-700">
            {t("markupRateLabel")}
          </label>
          <div className="flex items-center gap-2">
            <input
              id="markup-rate"
              type="number"
              min={0}
              max={100}
              step={1}
              value={markupRatePercent}
              onChange={(event) => setMarkupRatePercent(event.target.value)}
              className={inputClassName}
            />
            <span className="text-sm text-gray-600">%</span>
          </div>
          <p className="mt-1 text-xs text-gray-500">{t("markupRateHint")}</p>
        </div>
        <ul className="list-disc space-y-1.5 pl-5 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
          {(t.raw("markupApplicationPoints") as string[]).map((point) => (
            <li key={point}>{point}</li>
          ))}
        </ul>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {saved && <p className="text-sm text-green-600">{t("saved")}</p>}

      <button
        type="submit"
        disabled={saving}
        className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {saving ? t("saving") : t("save")}
      </button>
    </form>
  );
}
