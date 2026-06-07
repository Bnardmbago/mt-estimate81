"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { apiFetch, apiJson } from "@/lib/api";
import type { EstimateDetail, ExtractedData } from "@/lib/estimate";
import EstimateCalculation from "@/components/EstimateCalculation";
import ExportPanel from "@/components/ExportPanel";
import ActualsForm from "@/components/ActualsForm";
import FeatureItemEditor from "@/components/FeatureItemEditor";
import RequirementsReview from "@/components/RequirementsReview";

type EstimateExtractionProps = {
  estimate: EstimateDetail;
};

type EstimateStatusResponse = {
  status: string;
  extraction_progress: {
    documents_total: number;
    documents_done: number;
  } | null;
};

const emptyExtractedData = (): ExtractedData => ({
  functional_requirements: [],
  non_functional_requirements: [],
  user_roles: [],
  modules: [],
  external_systems: [],
  risks: [],
  gaps: [],
  confidence_notes: "",
});

export default function EstimateExtraction({ estimate }: EstimateExtractionProps) {
  const router = useRouter();
  const t = useTranslations("review");
  const [status, setStatus] = useState(estimate.status);
  const [progress, setProgress] = useState<EstimateStatusResponse["extraction_progress"]>(null);
  const [extracting, setExtracting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setStatus(estimate.status);
  }, [estimate.status]);

  const pollStatus = useCallback(async () => {
    try {
      const response = await apiJson<EstimateStatusResponse>(`/estimates/${estimate.id}/status`);
      setStatus(response.status);
      setProgress(response.extraction_progress);

      if (response.status !== "extracting") {
        setExtracting(false);
        router.refresh();
      }
    } catch {
      setExtracting(false);
    }
  }, [estimate.id, router]);

  useEffect(() => {
    if (status !== "extracting" && !extracting) {
      return;
    }

    const interval = window.setInterval(() => {
      void pollStatus();
    }, 2000);

    return () => window.clearInterval(interval);
  }, [status, extracting, pollStatus]);

  async function handleExtract() {
    setError(null);
    setExtracting(true);
    setStatus("extracting");

    try {
      const response = await apiFetch(`/estimates/${estimate.id}/extract`, {
        method: "POST",
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        const message =
          typeof payload.detail === "object"
            ? payload.detail.error
            : payload.detail || response.statusText;
        throw new Error(message || t("extractError"));
      }

      await pollStatus();
    } catch (extractError) {
      setExtracting(false);
      setStatus(estimate.status);
      setError(extractError instanceof Error ? extractError.message : t("extractError"));
    }
  }

  if (status === "draft") {
    return (
      <section className="mt-8 border-t border-gray-200 pt-8">
        <h2 className="mb-1 text-lg font-semibold">{t("extractTitle")}</h2>
        <p className="mb-4 text-sm text-gray-500">{t("extractDescription")}</p>
        {error && (
          <p className="mb-4 text-sm text-red-600" role="alert">
            {error}
          </p>
        )}
        <button
          type="button"
          onClick={() => void handleExtract()}
          disabled={extracting}
          className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {extracting ? t("extracting") : t("extractButton")}
        </button>
      </section>
    );
  }

  if (status === "extracting" || extracting) {
    const progressLabel =
      progress && progress.documents_total > 0
        ? t("progressDocuments", {
            done: progress.documents_done,
            total: progress.documents_total,
          })
        : t("progressAi");

    return (
      <section className="mt-8 border-t border-gray-200 pt-8">
        <h2 className="mb-1 text-lg font-semibold">{t("extractingTitle")}</h2>
        <p className="text-sm text-gray-500">{progressLabel}</p>
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
    const extractedData = {
      ...emptyExtractedData(),
      ...(estimate.extracted_data ?? {}),
    };
    const showExportPanel =
      status === "calculated" || status === "exported" || status === "completed";

    return (
      <div>
        <RequirementsReview estimateId={estimate.id} initialData={extractedData} />
        <FeatureItemEditor
          estimateId={estimate.id}
          initialItems={estimate.feature_items ?? []}
        />
        <EstimateCalculation estimate={estimate} />
        {showExportPanel && estimate.calculation_result && (
          <ExportPanel
            estimateId={estimate.id}
            locale={estimate.locale}
            estimateUpdatedAt={estimate.updated_at}
          />
        )}
        {estimate.calculation_result && (
          <ActualsForm
            estimateId={estimate.id}
            locale={estimate.locale}
            status={status}
            calculationResult={estimate.calculation_result}
            initialActuals={estimate.actuals ?? null}
          />
        )}
      </div>
    );
  }

  return null;
}
