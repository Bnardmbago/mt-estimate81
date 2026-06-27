"use client";

import { useCallback, useEffect, useRef, useState, type RefObject } from "react";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { apiFetch, apiJson } from "@/lib/api";
import type { EstimateDetail, ExtractedData, GanttData, CalculationResult } from "@/lib/estimate";
import type { EstimateFormHandle } from "@/components/EstimateForm";
import EstimateCalculation from "@/components/EstimateCalculation";
import EstimateRateCardPanel from "@/components/EstimateRateCardPanel";
import ExportPanel from "@/components/ExportPanel";
import ActualsForm from "@/components/ActualsForm";
import FeatureItemEditor from "@/components/FeatureItemEditor";
import GanttChart from "@/components/GanttChart";
import RequirementsReview from "@/components/RequirementsReview";
import { resolveExtractedData } from "@/lib/resolveLocalizedContent";

type EstimateExtractionProps = {
  estimate: EstimateDetail;
  formRef?: RefObject<EstimateFormHandle | null>;
  hideDraftRateCard?: boolean;
  isContactUser?: boolean;
};

type EstimateStatusResponse = {
  status: string;
  extraction_progress: {
    documents_total: number;
    documents_done: number;
    phase?: "documents" | "rate_card" | "ai" | "rate_card_tune";
  } | null;
  extraction_error: string | null;
};

const emptyExtractedData = (): ExtractedData => resolveExtractedData(null, "ja", "ja");

function parseApiError(payload: unknown, fallback: string): string {
  if (typeof payload === "object" && payload !== null) {
    const record = payload as Record<string, unknown>;
    if (typeof record.error === "string") {
      return record.error;
    }
    if (typeof record.detail === "object" && record.detail !== null) {
      const detail = record.detail as Record<string, unknown>;
      if (typeof detail.error === "string") {
        return detail.error;
      }
    }
    if (typeof record.detail === "string") {
      return record.detail;
    }
  }
  return fallback;
}

function ExtractButton({
  extracting,
  label,
  extractingLabel,
  onClick,
}: {
  extracting: boolean;
  label: string;
  extractingLabel: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={extracting}
      className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
    >
      {extracting ? extractingLabel : label}
    </button>
  );
}

export default function EstimateExtraction({
  estimate,
  formRef,
  hideDraftRateCard = false,
  isContactUser = false,
}: EstimateExtractionProps) {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("review");
  const [status, setStatus] = useState(estimate.status);
  const [progress, setProgress] = useState<EstimateStatusResponse["extraction_progress"]>(null);
  const [extracting, setExtracting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rateCardStale, setRateCardStale] = useState(estimate.rate_card_stale ?? false);
  const [projectStartDate, setProjectStartDate] = useState<string | null>(
    estimate.project_start_date ?? null,
  );
  const extractionPendingRef = useRef(false);
  const extractionStartedAtRef = useRef<number | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    setStatus(estimate.status);
  }, [estimate.status]);

  useEffect(() => {
    setProjectStartDate(estimate.project_start_date ?? null);
  }, [estimate.project_start_date]);

  useEffect(() => {
    setRateCardStale(estimate.rate_card_stale ?? false);
  }, [estimate.rate_card_stale]);

  const refreshRateCardStale = useCallback(async () => {
    try {
      const latest = await apiJson<EstimateDetail>(`/estimates/${estimate.id}`, {}, locale);
      setRateCardStale(latest.rate_card_stale ?? false);
    } catch {
      // Keep the last known value when refresh fails.
    }
  }, [estimate.id, locale]);

  useEffect(() => {
    void refreshRateCardStale();
    const onFocus = () => {
      void refreshRateCardStale();
    };
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [refreshRateCardStale]);

  const pollStatus = useCallback(async () => {
    try {
      const response = await apiJson<EstimateStatusResponse>(`/estimates/${estimate.id}/status`);
      setStatus(response.status);
      setProgress(response.extraction_progress);

      if (response.status === "extracting") {
        return;
      }

      if (response.status === "draft" && response.extraction_error) {
        extractionPendingRef.current = false;
        setExtracting(false);
        setStatus("draft");
        setError(response.extraction_error);
        router.refresh();
        return;
      }

      if (!extractionPendingRef.current) {
        return;
      }

      if (response.status === "review" || response.status === "calculated" || response.status === "exported") {
        extractionPendingRef.current = false;
        setExtracting(false);
        setError(null);
        router.refresh();
        return;
      }

      if (response.status === "draft" && response.extraction_error) {
        extractionPendingRef.current = false;
        setExtracting(false);
        setError(response.extraction_error);
        router.refresh();
        return;
      }

      // Background work still settling; keep polling.
    } catch (pollError) {
      extractionPendingRef.current = false;
      setExtracting(false);
      setError(pollError instanceof Error ? pollError.message : t("extractError"));
    }
  }, [estimate.id, locale, router, t]);

  useEffect(() => {
    if (status !== "extracting" && !extracting) {
      extractionStartedAtRef.current = null;
      setElapsedSeconds(0);
      return;
    }

    if (extractionStartedAtRef.current === null) {
      extractionStartedAtRef.current = Date.now();
    }

    const updateElapsed = () => {
      const startedAt = extractionStartedAtRef.current;
      if (startedAt === null) {
        return;
      }
      setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000));
    };

    updateElapsed();
    const interval = window.setInterval(updateElapsed, 1000);
    return () => window.clearInterval(interval);
  }, [status, extracting]);

  useEffect(() => {
    if (status !== "extracting" && !extracting) {
      return;
    }

    void pollStatus();
    const interval = window.setInterval(() => {
      void pollStatus();
    }, 2000);

    return () => window.clearInterval(interval);
  }, [status, extracting, pollStatus]);

  async function handleExtract() {
    if (extracting || extractionPendingRef.current) {
      return;
    }

    setError(null);

    const formSaved = await formRef?.current?.saveIfNeeded();
    if (formSaved === false) {
      setError(t("saveFormBeforeExtract"));
      document.getElementById("estimate-form")?.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }

    extractionPendingRef.current = true;
    setExtracting(true);
    setStatus("extracting");

    try {
      const response = await apiFetch(
        `/estimates/${estimate.id}/extract`,
        {
          method: "POST",
        },
        locale,
      );

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(parseApiError(payload, t("extractError")));
      }

      await pollStatus();
    } catch (extractError) {
      extractionPendingRef.current = false;
      setExtracting(false);
      setStatus(estimate.status);
      setError(extractError instanceof Error ? extractError.message : t("extractError"));
    }
  }

  if (status === "extracting" || extracting) {
    const progressLabel = (() => {
      if (!progress) {
        return t("progressAi");
      }
      const documentsPending =
        progress.documents_total > 0 &&
        progress.documents_done < progress.documents_total;
      if (documentsPending) {
        return t("progressDocuments", {
          done: progress.documents_done,
          total: progress.documents_total,
        });
      }
      if (progress.phase === "rate_card_tune") {
        return t("progressRateCardTune");
      }
      if (progress.phase === "rate_card") {
        return t("progressRateCard");
      }
      return t("progressAi");
    })();

    return (
      <section className="mt-8 border-t border-gray-200 pt-8">
        <h2 className="mb-1 text-lg font-semibold">{t("extractingTitle")}</h2>
        <p className="text-sm text-gray-500">{progressLabel}</p>
        {elapsedSeconds > 0 && (
          <p className="mt-1 text-xs text-gray-400">
            {t("progressElapsed", { seconds: elapsedSeconds })}
          </p>
        )}
        <p className="mt-1 text-xs text-gray-400">{t("progressHint")}</p>
        <div className="mt-4 h-2 w-full max-w-md overflow-hidden rounded-full bg-gray-200">
          <div className="h-full w-1/2 animate-pulse rounded-full bg-indigo-500" />
        </div>
      </section>
    );
  }

  if (
    status === "review" ||
    status === "calculated" ||
    status === "exported" ||
    status === "completed"
  ) {
    const extractedData = resolveExtractedData(
      estimate.extracted_data as Record<string, unknown> | null,
      locale,
      estimate.locale,
    );
    const showExportPanel =
      status === "calculated" || status === "exported" || status === "completed";
    const storedGantt = (estimate.calculation_result?.gantt as GanttData | undefined) ?? null;
    const featureItems = estimate.feature_items ?? [];
    const canReExtract =
      status === "review" || status === "calculated" || status === "exported";

    return (
      <div>
        {!isContactUser ? (
          <EstimateRateCardPanel
            estimateId={estimate.id}
            rateCardId={estimate.rate_card_id}
            rateCardName={estimate.rate_card_name}
            complexityProfile={estimate.complexity_profile ?? null}
            rateCardAutoTuned={estimate.rate_card_auto_tuned ?? false}
            rateCardTuneRecommended={estimate.rate_card_tune_recommended ?? false}
            rateCardAutoTuneEnabled={estimate.rate_card_auto_tune_enabled ?? true}
            readOnly={status === "completed"}
          />
        ) : null}
        {rateCardStale && canReExtract && !isContactUser && (
          <div
            className="mb-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
            role="status"
          >
            <p className="font-medium">{t("rateCardStaleTitle")}</p>
            <p className="mt-1">{t("rateCardStaleDescription")}</p>
          </div>
        )}
        {canReExtract && (
          <section className="mb-6 rounded-lg border border-indigo-100 bg-indigo-50 p-4">
            <h2 className="text-sm font-semibold text-indigo-950">{t("reExtractTitle")}</h2>
            <p className="mt-1 text-sm text-indigo-900">{t("reExtractDescription")}</p>
            {error && (
              <p
                className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
                role="alert"
              >
                {error}
              </p>
            )}
            <div className="mt-3">
              <ExtractButton
                extracting={extracting}
                label={t("extractButton")}
                extractingLabel={t("extracting")}
                onClick={() => void handleExtract()}
              />
            </div>
          </section>
        )}
        <RequirementsReview
          estimateId={estimate.id}
          estimateUpdatedAt={estimate.updated_at}
          initialData={extractedData}
          fallbackLocale={estimate.locale}
        />
        <FeatureItemEditor estimateId={estimate.id} initialItems={featureItems} />
        <GanttChart
          estimateId={estimate.id}
          initialStartDate={projectStartDate}
          initialGantt={storedGantt}
          hasFeatureItems={featureItems.length > 0}
          onStartDateChange={setProjectStartDate}
        />
        <EstimateCalculation
          estimate={estimate}
          projectStartDate={projectStartDate}
          isContactUser={isContactUser}
        />
        {showExportPanel && estimate.calculation_result && (
          <ExportPanel
            estimateId={estimate.id}
            estimateUpdatedAt={estimate.updated_at}
            calculationResult={estimate.calculation_result as CalculationResult}
            isContactUser={isContactUser}
          />
        )}
        {estimate.calculation_result && (
          <ActualsForm
            estimateId={estimate.id}
            status={status}
            calculationResult={estimate.calculation_result}
            initialActuals={estimate.actuals ?? null}
          />
        )}
      </div>
    );
  }

  if (status === "draft") {
    return (
      <section className="mt-8 border-t border-gray-200 pt-8">
        <h2 className="mb-1 text-lg font-semibold">{t("extractTitle")}</h2>
        <p className="mb-4 text-sm text-gray-500">{t("extractDescription")}</p>
        {!hideDraftRateCard && !isContactUser ? (
          <EstimateRateCardPanel
            estimateId={estimate.id}
            rateCardId={estimate.rate_card_id}
            rateCardName={estimate.rate_card_name}
            complexityProfile={estimate.complexity_profile ?? null}
            rateCardAutoTuned={estimate.rate_card_auto_tuned ?? false}
            rateCardTuneRecommended={estimate.rate_card_tune_recommended ?? false}
            rateCardAutoTuneEnabled={estimate.rate_card_auto_tune_enabled ?? true}
          />
        ) : null}
        {error && (
          <p
            className="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
            role="alert"
          >
            {error}
          </p>
        )}
        <ExtractButton
          extracting={extracting}
          label={t("extractButton")}
          extractingLabel={t("extracting")}
          onClick={() => void handleExtract()}
        />
      </section>
    );
  }

  return (
    <section className="mt-8 border-t border-gray-200 pt-8">
      <p className="text-sm text-gray-500">{t("extractDescription")}</p>
      {error && (
        <p
          className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
          role="alert"
        >
          {error}
        </p>
      )}
    </section>
  );
}
