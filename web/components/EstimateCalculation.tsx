"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import CalculationBreakdown, { type CalculationResult } from "@/components/CalculationBreakdown";
import { apiFetch, apiJson } from "@/lib/api";
import type { EstimateDetail } from "@/lib/estimate";

type EstimateCalculationProps = {
  estimate: EstimateDetail;
};

export default function EstimateCalculation({ estimate }: EstimateCalculationProps) {
  const router = useRouter();
  const t = useTranslations("calculation");
  const [calculating, setCalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recalculateWithCurrentRates, setRecalculateWithCurrentRates] = useState(false);
  const [result, setResult] = useState<CalculationResult | null>(
    (estimate.calculation_result as CalculationResult | null) ?? null,
  );

  async function handleCalculate() {
    setCalculating(true);
    setError(null);

    const query = recalculateWithCurrentRates
      ? "?recalculate_with_current_rates=true"
      : "";

    try {
      const response = await apiFetch(`/estimates/${estimate.id}/calculate${query}`, {
        method: "POST",
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        const message =
          typeof payload.detail === "object"
            ? payload.detail.error
            : payload.detail || response.statusText;
        throw new Error(message || t("calculateError"));
      }

      const updated = (await response.json()) as EstimateDetail;
      setResult(updated.calculation_result as CalculationResult);
      router.refresh();
    } catch (calculateError) {
      setError(
        calculateError instanceof Error ? calculateError.message : t("calculateError"),
      );
    } finally {
      setCalculating(false);
    }
  }

  return (
    <section className="mt-8 border-t border-gray-200 pt-8">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold">{t("calculateTitle")}</h2>
          <p className="text-sm text-gray-500">{t("calculateDescription")}</p>
        </div>
        <div className="flex flex-col items-start gap-2 sm:items-end">
          {estimate.status === "calculated" && (
            <label className="flex items-center gap-2 text-sm text-gray-600">
              <input
                type="checkbox"
                checked={recalculateWithCurrentRates}
                onChange={(event) => setRecalculateWithCurrentRates(event.target.checked)}
                className="rounded border-gray-300"
              />
              {t("recalculateWithCurrentRates")}
            </label>
          )}
          <button
            type="button"
            onClick={() => void handleCalculate()}
            disabled={calculating}
            className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {calculating ? t("calculating") : t("calculateButton")}
          </button>
        </div>
      </div>

      {error && (
        <p className="mb-4 text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      {result && <CalculationBreakdown result={result} />}
    </section>
  );
}
