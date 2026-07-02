"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import CalculationBreakdown, { type CalculationResult } from "@/components/CalculationBreakdown";
import { apiFetch, parseApiErrorPayload } from "@/lib/api";
import type { EstimateDetail } from "@/lib/estimate";
import {
  extractQuestionnaireMissingFields,
  questionnaireMissingMessageKey,
  type QuestionnaireMissingKey,
} from "@/lib/questionnaireErrors";

type EstimateCalculationProps = {
  estimate: EstimateDetail;
  projectStartDate: string | null;
  isContactUser?: boolean;
};

export default function EstimateCalculation({
  estimate,
  projectStartDate,
  isContactUser = false,
}: EstimateCalculationProps) {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("calculation");
  const [calculating, setCalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [questionnaireMissing, setQuestionnaireMissing] = useState<string[]>([]);
  const [result, setResult] = useState<CalculationResult | null>(
    (estimate.calculation_result as CalculationResult | null) ?? null,
  );
  const scrollToTotalsRef = useRef(false);

  useEffect(() => {
    setResult((estimate.calculation_result as CalculationResult | null) ?? null);
  }, [estimate.calculation_result]);

  useEffect(() => {
    if (!scrollToTotalsRef.current || !result) {
      return;
    }

    scrollToTotalsRef.current = false;
    const frameId = requestAnimationFrame(() => {
      document.getElementById("total-development-cost")?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    });

    return () => cancelAnimationFrame(frameId);
  }, [result]);

  async function handleCalculate() {
    if (!estimate.rate_card_id) {
      setError(t("rateCardRequired"));
      return;
    }

    setCalculating(true);
    setError(null);
    setQuestionnaireMissing([]);

    try {
      const response = await apiFetch(
        `/estimates/${estimate.id}/calculate`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(
            projectStartDate ? { project_start_date: projectStartDate } : {},
          ),
        },
        locale,
      );

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        const missingFields = extractQuestionnaireMissingFields(payload);
        if (missingFields && missingFields.length > 0) {
          setQuestionnaireMissing(
            missingFields.map((field) =>
              t(questionnaireMissingMessageKey(field as QuestionnaireMissingKey)),
            ),
          );
          setError(t("questionnaireIncompleteIntro"));
          return;
        }

        const { message } = parseApiErrorPayload(payload, t("calculateError"));
        throw new Error(message);
      }

      const updated = (await response.json()) as EstimateDetail;
      setResult(updated.calculation_result as CalculationResult);
      scrollToTotalsRef.current = true;
      router.refresh();
    } catch (calculateError) {
      setError(
        calculateError instanceof Error ? calculateError.message : t("calculateError"),
      );
    } finally {
      setCalculating(false);
    }
  }

  const isCalculated =
    estimate.status === "calculated" ||
    estimate.status === "exported" ||
    estimate.status === "completed";

  return (
    <section className="mt-8 border-t border-gray-200 pt-8">
      <div className="mb-4 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 className="text-lg font-semibold">{t("calculateTitle")}</h2>
          <p className="text-sm text-gray-500">{t("calculateDescription")}</p>
        </div>

        <div className="flex w-full flex-col gap-3 sm:w-auto sm:min-w-[320px]">
          {!isContactUser && (
            <div className="block text-sm">
              <span className="mb-1 block font-medium text-gray-700">{t("rateCardLabel")}</span>
              <p className="rounded border border-gray-200 bg-gray-50 px-3 py-2 text-gray-800">
                {estimate.rate_card_name ?? "—"}
              </p>
              {estimate.rate_card_id && (
                <Link
                  href={`/${locale}/rate-cards/${estimate.rate_card_id}?estimateId=${estimate.id}`}
                  className="mt-2 inline-block rounded border border-blue-200 bg-white px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-50"
                >
                  {t("viewRateCard")}
                </Link>
              )}
              {isCalculated && (
                <p className="mt-1 text-xs text-gray-500">{t("rateCardFrozenHint")}</p>
              )}
            </div>
          )}

          <button
            type="button"
            onClick={() => void handleCalculate()}
            disabled={calculating || !estimate.rate_card_id}
            className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {calculating ? t("calculating") : t("calculateButton")}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 text-sm text-red-600" role="alert">
          <p>{error}</p>
          {questionnaireMissing.length > 0 ? (
            <ul className="mt-2 list-disc space-y-1 pl-5">
              {questionnaireMissing.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : null}
        </div>
      )}

      {result && (
        <CalculationBreakdown
          result={result}
          quotationIssueDate={estimate.updated_at}
        />
      )}
    </section>
  );
}
