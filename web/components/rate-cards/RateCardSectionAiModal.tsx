"use client";

import { useEffect, useMemo, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { apiFetch } from "@/lib/api";
import {
  previewItemsForDisplay,
  type RateCardAiSection,
  type RateCardAiSuggestResponse,
} from "@/lib/rateCardAi";

const NO_LINK_ESTIMATE = "__none__";

type RateCardEstimateUsage = {
  estimate_id: string;
  project_name: string;
  client_name: string;
  status: string;
  updated_at: string;
};

type RateCardSectionAiModalProps = {
  open: boolean;
  section: RateCardAiSection | null;
  rateCardId: string;
  usageEstimates: RateCardEstimateUsage[];
  onClose: () => void;
  onApply: (response: RateCardAiSuggestResponse) => void;
};

async function readApiError(response: Response, fallback: string): Promise<string> {
  const payload = await response.json().catch(() => ({}));
  const detail =
    typeof payload.detail === "object" && payload.detail !== null
      ? payload.detail
      : payload;
  const message =
    typeof detail.error === "string"
      ? detail.error
      : typeof payload.error === "string"
        ? payload.error
        : fallback;
  const extra =
    typeof detail.details?.message === "string" ? detail.details.message : null;
  return extra ? `${message} (${extra})` : message;
}

export default function RateCardSectionAiModal({
  open,
  section,
  rateCardId,
  usageEstimates,
  onClose,
  onApply,
}: RateCardSectionAiModalProps) {
  const t = useTranslations("rateCards.ai");
  const locale = useLocale() as "ja" | "en";
  const [estimateId, setEstimateId] = useState("");
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<RateCardAiSuggestResponse | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    setError(null);
    setPreview(null);
    setPrompt("");
    setEstimateId(NO_LINK_ESTIMATE);
  }, [open, section]);

  const sectionTitle = section ? t(`sections.${section}`) : "";

  const previewItems = useMemo(
    () => (preview ? previewItemsForDisplay(preview) : []),
    [preview],
  );

  if (!open || !section) {
    return null;
  }

  async function handleGenerate() {
    if (!prompt.trim()) {
      return;
    }

    setLoading(true);
    setError(null);
    setPreview(null);

    const linkedEstimateId =
      estimateId === NO_LINK_ESTIMATE ? null : estimateId;

    try {
      const response = await apiFetch(`/rate-cards/cards/${rateCardId}/ai/suggest`, {
        method: "POST",
        body: JSON.stringify({
          estimate_id: linkedEstimateId,
          section,
          prompt: prompt.trim(),
          locale,
        }),
      });

      if (!response.ok) {
        setError(await readApiError(response, t("error")));
        return;
      }

      const result = await response.json() as RateCardAiSuggestResponse;
      setPreview(result);
    } catch {
      setError(t("error"));
    } finally {
      setLoading(false);
    }
  }

  function handleApply() {
    if (!preview || preview.items.length === 0) {
      return;
    }
    onApply(preview);
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div
        className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white p-6 shadow-lg dark:bg-gray-900"
        role="dialog"
        aria-labelledby="rate-card-ai-modal-title"
      >
        <h3 id="rate-card-ai-modal-title" className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          {t("modalTitle", { section: sectionTitle })}
        </h3>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{t("modalDescription")}</p>

        <div className="mt-4 space-y-4">
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-gray-700 dark:text-gray-300">
              {t("estimateLabel")}
            </span>
            <select
              value={estimateId}
              onChange={(event) => setEstimateId(event.target.value)}
              disabled={loading}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800"
            >
              <option value={NO_LINK_ESTIMATE}>{t("noLinkOption")}</option>
              {usageEstimates.map((estimate) => (
                <option key={estimate.estimate_id} value={estimate.estimate_id}>
                  {estimate.project_name} — {estimate.client_name} ({estimate.status})
                </option>
              ))}
            </select>
          </label>

          <label className="block text-sm">
            <span className="mb-1 block font-medium text-gray-700 dark:text-gray-300">
              {t("promptLabel")}
            </span>
            <textarea
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              placeholder={t("promptPlaceholder")}
              rows={4}
              disabled={loading}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800"
            />
          </label>

          {error ? (
            <p className="text-sm text-red-600" role="alert">
              {error}
            </p>
          ) : null}

          {preview ? (
            <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-4 dark:border-indigo-900 dark:bg-indigo-950/30">
              <p className="text-sm font-medium text-indigo-950 dark:text-indigo-100">
                {preview.estimate
                  ? t("previewTitle", { project: preview.estimate.project_name })
                  : t("previewTitleNoLink")}
              </p>
              {preview.generation_notes ? (
                <p className="mt-2 text-sm text-indigo-900/80 dark:text-indigo-200/80">
                  {preview.generation_notes}
                </p>
              ) : null}
              {preview.replace_all ? (
                <p className="mt-2 text-xs font-medium text-amber-700 dark:text-amber-300">
                  {t("replaceAllPhasesHint")}
                </p>
              ) : null}
              {preview.items.length === 0 ? (
                <p className="mt-3 text-sm text-gray-600 dark:text-gray-400">{t("noSuggestions")}</p>
              ) : (
                <ul className="mt-3 space-y-2 text-sm text-gray-800 dark:text-gray-200">
                  {previewItems.map((item, index) => (
                    <li
                      key={`${section}-preview-${index}`}
                      className="rounded border border-white/60 bg-white/70 px-3 py-2 dark:border-gray-700 dark:bg-gray-900/60"
                    >
                      {section === "roles" ? (
                        <span>
                          {String(item.name)} — ¥{Number(item.hourly_rate_jpy).toLocaleString()}/hr
                        </span>
                      ) : null}
                      {section === "phases" ? (
                        <span>
                          {String(item.name)} — {Math.round(Number(item.percentage) * 100)}%
                        </span>
                      ) : null}
                      {section === "setup_cost_items" || section === "monthly_rc_items" ? (
                        <span>
                          {String(item.name)} — ¥{Number(item.amount_jpy).toLocaleString()}
                        </span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ) : null}
        </div>

        <div className="mt-6 flex flex-wrap justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="rounded border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:hover:bg-gray-800"
          >
            {t("cancel")}
          </button>
          <button
            type="button"
            onClick={() => void handleGenerate()}
            disabled={loading || !prompt.trim()}
            className="rounded border border-indigo-600 px-4 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-50 disabled:opacity-50 dark:text-indigo-300 dark:hover:bg-indigo-950/40"
          >
            {loading ? t("generating") : t("generate")}
          </button>
          <button
            type="button"
            onClick={handleApply}
            disabled={loading || !preview || preview.items.length === 0}
            className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {t("apply")}
          </button>
        </div>
      </div>
    </div>
  );
}
