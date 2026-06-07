"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { apiFetch, apiJson } from "@/lib/api";
import type { CalculationResult } from "@/lib/estimate";
import VarianceReport, { type VarianceSummary } from "@/components/VarianceReport";

type ActualsFormProps = {
  estimateId: string;
  locale: string;
  status: string;
  calculationResult: CalculationResult;
  initialActuals?: {
    actual_effort_hours: number;
    actual_duration_days: number;
    actual_nrc_jpy: number;
    actual_rc_monthly_jpy: number;
    variance_notes: string | null;
  } | null;
};

type ActualsResponse = {
  actuals: {
    actual_effort_hours: number;
    actual_duration_days: number;
    actual_nrc_jpy: number;
    actual_rc_monthly_jpy: number;
    variance_notes: string | null;
  };
  variance: VarianceSummary | null;
};

export default function ActualsForm({
  estimateId,
  locale,
  status,
  calculationResult,
  initialActuals,
}: ActualsFormProps) {
  const router = useRouter();
  const t = useTranslations("variance");
  const canEnterActuals =
    status === "calculated" || status === "exported" || status === "completed";

  const [effortHours, setEffortHours] = useState(
    String(initialActuals?.actual_effort_hours ?? calculationResult.total_effort_hours),
  );
  const [effortDays, setEffortDays] = useState(
    String(initialActuals?.actual_duration_days ?? calculationResult.total_effort_days),
  );
  const [nrcJpy, setNrcJpy] = useState(
    String(initialActuals?.actual_nrc_jpy ?? calculationResult.nrc.total_jpy),
  );
  const [rcMonthlyJpy, setRcMonthlyJpy] = useState(
    String(initialActuals?.actual_rc_monthly_jpy ?? calculationResult.rc.monthly_total_jpy),
  );
  const [notes, setNotes] = useState(initialActuals?.variance_notes ?? "");
  const [variance, setVariance] = useState<VarianceSummary | null>(null);
  const [saving, setSaving] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  if (!canEnterActuals) {
    return null;
  }

  async function saveActuals() {
    setSaving(true);
    setError(null);
    setSaved(false);

    try {
      const response = await apiJson<ActualsResponse>(`/estimates/${estimateId}/actuals`, {
        method: "PUT",
        body: JSON.stringify({
          actual_effort_hours: Number(effortHours),
          actual_duration_days: Number(effortDays),
          actual_nrc_jpy: Number(nrcJpy),
          actual_rc_monthly_jpy: Number(rcMonthlyJpy),
          variance_notes: notes.trim() || null,
        }),
      });
      setVariance(response.variance);
      setSaved(true);
      router.refresh();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : t("saveError"));
    } finally {
      setSaving(false);
    }
  }

  async function markComplete() {
    setCompleting(true);
    setError(null);

    try {
      const response = await apiJson<ActualsResponse>(`/estimates/${estimateId}/actuals`, {
        method: "PUT",
        body: JSON.stringify({
          actual_effort_hours: Number(effortHours),
          actual_duration_days: Number(effortDays),
          actual_nrc_jpy: Number(nrcJpy),
          actual_rc_monthly_jpy: Number(rcMonthlyJpy),
          variance_notes: notes.trim() || null,
        }),
      });
      setVariance(response.variance);
      setSaved(true);

      const completeResponse = await apiFetch(`/estimates/${estimateId}/complete`, {
        method: "POST",
      });
      if (!completeResponse.ok) {
        const payload = await completeResponse.json().catch(() => ({}));
        const message =
          typeof payload.detail === "object"
            ? payload.detail.error
            : payload.detail || completeResponse.statusText;
        throw new Error(message || t("completeError"));
      }
      router.refresh();
    } catch (completeError) {
      setError(completeError instanceof Error ? completeError.message : t("completeError"));
    } finally {
      setCompleting(false);
    }
  }

  const displayVariance = variance;

  return (
    <section className="mt-8 border-t border-gray-200 pt-8">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold">{t("actualsTitle")}</h2>
          <p className="text-sm text-gray-500">{t("actualsDescription")}</p>
        </div>
        {status !== "completed" && (
          <button
            type="button"
            onClick={() => void markComplete()}
            disabled={completing || saving}
            className="rounded bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
          >
            {completing ? t("completing") : t("markComplete")}
          </button>
        )}
      </div>

      <div className="mb-4 grid gap-4 sm:grid-cols-2">
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-gray-700">{t("fields.effortHours")}</span>
          <input
            type="number"
            min="0"
            step="0.5"
            value={effortHours}
            onChange={(event) => setEffortHours(event.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2"
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-gray-700">{t("fields.effortDays")}</span>
          <input
            type="number"
            min="0"
            step="0.5"
            value={effortDays}
            onChange={(event) => setEffortDays(event.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2"
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-gray-700">{t("fields.nrc")}</span>
          <input
            type="number"
            min="0"
            step="1"
            value={nrcJpy}
            onChange={(event) => setNrcJpy(event.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2"
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-gray-700">{t("fields.rcMonthly")}</span>
          <input
            type="number"
            min="0"
            step="1"
            value={rcMonthlyJpy}
            onChange={(event) => setRcMonthlyJpy(event.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2"
          />
        </label>
        <label className="block text-sm sm:col-span-2">
          <span className="mb-1 block font-medium text-gray-700">{t("fields.notes")}</span>
          <textarea
            rows={3}
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2"
          />
        </label>
      </div>

      <div className="mb-4 flex items-center gap-3">
        <button
          type="button"
          onClick={() => void saveActuals()}
          disabled={saving || completing}
          className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {saving ? t("saving") : t("saveActuals")}
        </button>
        {saved && <span className="text-sm text-green-600">{t("saved")}</span>}
      </div>

      {error && (
        <p className="mb-4 text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      {displayVariance && (
        <div className="mt-6">
          <h3 className="mb-2 text-sm font-medium text-gray-700">{t("varianceTitle")}</h3>
          <VarianceReport
            rows={[
              {
                estimate_id: estimateId,
                project_name: "",
                client_name: "",
                completed_at: "",
                actuals_entered_at: null,
                variance: displayVariance,
                variance_notes: notes.trim() || null,
              },
            ]}
            locale={locale}
            showProjectLink={false}
          />
        </div>
      )}
    </section>
  );
}
