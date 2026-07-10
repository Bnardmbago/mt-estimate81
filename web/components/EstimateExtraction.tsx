"use client";

import { useCallback, useEffect, useRef, useState, type RefObject } from "react";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { apiFetch, apiJson } from "@/lib/api";
import type { EstimateDetail, ExtractedData, GanttData, CalculationResult } from "@/lib/estimate";
import type { EstimateFormHandle } from "@/components/EstimateForm";
import EstimateCalculation from "@/components/EstimateCalculation";
import EstimateNrcRcPanel from "@/components/EstimateNrcRcPanel";
import EstimateRateCardPanel from "@/components/EstimateRateCardPanel";
import ExportPanel from "@/components/ExportPanel";
import ActualsForm from "@/components/ActualsForm";
import FeatureItemEditor from "@/components/FeatureItemEditor";
import GanttChart, { type DeliveryScheduleAdvisory } from "@/components/GanttChart";
import RequirementsReview from "@/components/RequirementsReview";
import { resolveExtractedData } from "@/lib/resolveLocalizedContent";

type EstimateExtractionProps = {
  estimate: EstimateDetail;
  formRef?: RefObject<EstimateFormHandle | null>;
  hideDraftRateCard?: boolean;
  isContactUser?: boolean;
};

type ConstraintConfirmation = {
  pending?: boolean;
  budget_below_minimum?: boolean;
  schedule_below_minimum?: boolean;
  original_total_hours?: number;
  max_hours_cap?: number;
  binding_constraint?: "budget" | "schedule" | null;
  estimation_warnings?: string[];
  estimate_exclusions?: string[];
};

type EstimateStatusResponse = {
  status: string;
  extraction_progress: {
    documents_total: number;
    documents_done: number;
    phase?: "documents" | "rate_card" | "ai" | "rate_card_tune";
  } | null;
  extraction_error: string | null;
  constraint_confirmation?: ConstraintConfirmation | null;
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
  const [constraintConfirmation, setConstraintConfirmation] =
    useState<ConstraintConfirmation | null>(null);
  const [constraintProcessing, setConstraintProcessing] = useState(false);

  useEffect(() => {
    setStatus(estimate.status);
    if (estimate.status === "constraint_paused") {
      const extracted = resolveExtractedData(
        estimate.extracted_data as Record<string, unknown> | null,
        locale,
        estimate.locale,
      );
      const confirmation = (
        extracted as Record<string, unknown> & { constraint_confirmation?: ConstraintConfirmation }
      ).constraint_confirmation;
      if (confirmation?.pending) {
        setConstraintConfirmation(confirmation);
      }
    }
  }, [estimate.status, estimate.extracted_data, estimate.locale, locale]);

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

      if (response.status === "constraint_paused") {
        extractionPendingRef.current = false;
        setExtracting(false);
        setConstraintConfirmation(response.constraint_confirmation ?? null);
        return;
      }

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
        setConstraintConfirmation(null);
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
    if (status !== "constraint_paused") {
      return;
    }
    void pollStatus();
  }, [status, pollStatus]);

  useEffect(() => {
    if (status !== "extracting" && !extracting && status !== "constraint_paused") {
      return;
    }

    if (status === "constraint_paused") {
      void pollStatus();
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

  async function handleConstraintDecision(decision: "stop" | "continue") {
    setConstraintProcessing(true);
    setError(null);
    try {
      const response = await apiFetch(
        `/estimates/${estimate.id}/extract/constraint-confirmation`,
        {
          method: "POST",
          body: JSON.stringify({ decision }),
        },
        locale,
      );
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(parseApiError(payload, t("constraintConfirmationError")));
      }
      if (decision === "stop") {
        setConstraintConfirmation(null);
        setStatus("draft");
        router.refresh();
        return;
      }
      extractionPendingRef.current = true;
      setExtracting(true);
      setStatus("extracting");
      setConstraintConfirmation(null);
      await pollStatus();
    } catch (decisionError) {
      setError(
        decisionError instanceof Error
          ? decisionError.message
          : t("constraintConfirmationError"),
      );
    } finally {
      setConstraintProcessing(false);
    }
  }

  function constraintConfirmationBody(confirmation: ConstraintConfirmation): string {
    if (confirmation.budget_below_minimum && confirmation.schedule_below_minimum) {
      return t("constraintConfirmationBody");
    }
    if (confirmation.budget_below_minimum) {
      return t("constraintConfirmationBodyBudgetOnly");
    }
    return t("constraintConfirmationBodyScheduleOnly");
  }

  if (status === "constraint_paused") {
    if (!constraintConfirmation) {
      return (
        <section className="mt-8 border-t border-gray-200 pt-8">
          <p className="text-sm text-gray-500">{t("constraintConfirmationProcessing")}</p>
        </section>
      );
    }

    const bindingLabel =
      constraintConfirmation.binding_constraint === "schedule"
        ? t("constraintBindingSchedule")
        : t("constraintBindingBudget");
    const warnings = constraintConfirmation.estimation_warnings ?? [];
    const exclusions = constraintConfirmation.estimate_exclusions ?? [];

    return (
      <section className="mt-8 border-t border-gray-200 pt-8">
        <div
          className="mx-auto max-w-3xl rounded-lg border border-amber-300 bg-amber-50 p-6 shadow-sm"
          role="dialog"
          aria-labelledby="constraint-confirmation-title"
        >
          <h2 id="constraint-confirmation-title" className="text-lg font-semibold text-amber-950">
            {t("constraintConfirmationTitle")}
          </h2>
          <p className="mt-2 text-sm text-amber-900">
            {constraintConfirmationBody(constraintConfirmation)}
          </p>
          <p className="mt-2 text-sm font-medium text-amber-950">
            {t("constraintConfirmationHours", {
              originalHours: constraintConfirmation.original_total_hours ?? 0,
              capHours: constraintConfirmation.max_hours_cap ?? 0,
              binding: bindingLabel,
            })}
          </p>
          {warnings.length > 0 ? (
            <div className="mt-4">
              <p className="text-sm font-medium text-amber-950">
                {t("constraintConfirmationWarnings")}
              </p>
              <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-amber-900">
                {warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {exclusions.length > 0 ? (
            <div className="mt-4">
              <p className="text-sm font-medium text-amber-950">
                {t("constraintConfirmationExclusions")}
              </p>
              <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-amber-900">
                {exclusions.map((exclusion) => (
                  <li key={exclusion}>{exclusion}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {error ? (
            <p
              className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
              role="alert"
            >
              {error}
            </p>
          ) : null}
          <div className="mt-6 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => void handleConstraintDecision("stop")}
              disabled={constraintProcessing}
              className="rounded border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-800 hover:bg-gray-50 disabled:opacity-50"
            >
              {t("constraintConfirmationStop")}
            </button>
            <button
              type="button"
              onClick={() => void handleConstraintDecision("continue")}
              disabled={constraintProcessing}
              className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {constraintProcessing
                ? t("constraintConfirmationProcessing")
                : t("constraintConfirmationContinue")}
            </button>
          </div>
        </div>
      </section>
    );
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
    const deliveryScheduleAdvisory =
      (estimate.calculation_result as { delivery_schedule_advisory?: unknown } | null)
        ?.delivery_schedule_advisory ?? null;
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
        {extractedData.extraction_constraints?.hours_scaled ? (
          <div
            className="mb-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
            role="status"
          >
            <p className="font-medium">{t("constraintScaledTitle")}</p>
            <p className="mt-1">
              {t("constraintScaledDescription", {
                originalHours: extractedData.extraction_constraints.original_total_hours ?? 0,
                adjustedHours: extractedData.extraction_constraints.adjusted_total_hours ?? 0,
                factor: extractedData.extraction_constraints.applied_scale_factor ?? 1,
                capHours: extractedData.extraction_constraints.max_hours_cap ?? 0,
                binding:
                  extractedData.extraction_constraints.binding_constraint === "schedule"
                    ? t("constraintBindingSchedule")
                    : t("constraintBindingBudget"),
              })}
            </p>
          </div>
        ) : null}
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
          deliveryScheduleAdvisory={
            deliveryScheduleAdvisory as DeliveryScheduleAdvisory | null
          }
        />
        <EstimateNrcRcPanel
          estimateId={estimate.id}
          estimateUpdatedAt={estimate.updated_at}
          initialAssumptions={estimate.nrc_rc_assumptions ?? { setup_cost_items: [], monthly_rc_items: [] }}
          complexityLevel={estimate.complexity_profile?.level ?? null}
          editable={!isContactUser && (status === "review" || status === "calculated")}
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
        {estimate.calculation_result && !isContactUser && (
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
