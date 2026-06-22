"use client";

import { useMemo, useState, type RefObject } from "react";
import { useLocale, useTranslations } from "next-intl";
import type { EstimateFormHandle } from "@/components/EstimateForm";
import { apiFetch } from "@/lib/api";
import {
  type FormFieldValues,
  resolveFormSchema,
} from "@/lib/formSchema";
import { formatFormDataPreview } from "@/lib/formPreview";
import type { EstimateDetail } from "@/lib/estimate";

type EstimateAiSpecPanelProps = {
  estimateId: string;
  estimate: EstimateDetail;
  formRef: RefObject<EstimateFormHandle | null>;
};

type SuggestFormResponse = {
  form_data: Record<string, string>;
  generation_notes: string;
};

const textareaClassName =
  "min-h-[10rem] w-full resize-y rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

async function readApiError(response: Response, fallback: string): Promise<string> {
  const payload = await response.json().catch(() => ({}));
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

export default function EstimateAiSpecPanel({
  estimateId,
  estimate,
  formRef,
}: EstimateAiSpecPanelProps) {
  const locale = useLocale();
  const t = useTranslations("aiSpec");

  const schema = useMemo(
    () => resolveFormSchema(estimate.form_schema_snapshot),
    [estimate.form_schema_snapshot],
  );

  const [prompt, setPrompt] = useState("");
  const [previewText, setPreviewText] = useState("");
  const [lastSuggestion, setLastSuggestion] = useState<SuggestFormResponse | null>(null);
  const [generationNotes, setGenerationNotes] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleGenerate() {
    if (!prompt.trim()) {
      return;
    }

    setError(null);
    setLoading(true);

    const projectSaved = await formRef.current?.saveBeforeAiSuggest();
    if (projectSaved === false) {
      setError(t("saveFormBeforeGenerate"));
      setLoading(false);
      return;
    }

    try {
      const response = await apiFetch(
        `/estimates/${estimateId}/ai/suggest-form`,
        {
          method: "POST",
          body: JSON.stringify({
            prompt: prompt.trim(),
            locale,
          }),
        },
        locale,
      );

      if (!response.ok) {
        setError(await readApiError(response, t("error")));
        return;
      }

      const result = (await response.json()) as SuggestFormResponse;
      setLastSuggestion(result);
      setGenerationNotes(result.generation_notes || null);
      setPreviewText(formatFormDataPreview(result.form_data, schema, locale));
    } catch {
      setError(t("error"));
    } finally {
      setLoading(false);
    }
  }

  function handleApply() {
    if (!lastSuggestion) {
      return;
    }
    formRef.current?.applyValues(lastSuggestion.form_data as Partial<FormFieldValues>);
  }

  return (
    <section className="rounded-lg border border-indigo-100 bg-indigo-50/40 p-4">
      <h2 className="text-base font-semibold text-gray-900">{t("title")}</h2>
      <p className="mt-1 text-sm text-gray-600">{t("description")}</p>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="flex flex-col">
          <label htmlFor="ai-prompt" className="mb-1 text-sm font-medium text-gray-700">
            {t("promptLabel")}
          </label>
          <textarea
            id="ai-prompt"
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder={t("promptPlaceholder")}
            rows={6}
            disabled={loading}
            className={textareaClassName}
          />
          <button
            type="button"
            onClick={() => void handleGenerate()}
            disabled={loading || !prompt.trim()}
            className="mt-3 self-start rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {loading ? t("generating") : t("generate")}
          </button>
        </div>

        <div className="flex flex-col">
          <label htmlFor="ai-result" className="mb-1 text-sm font-medium text-gray-700">
            {t("resultLabel")}
          </label>
          <textarea
            id="ai-result"
            value={previewText}
            onChange={(event) => setPreviewText(event.target.value)}
            placeholder={t("resultPlaceholder")}
            rows={6}
            disabled={loading}
            className={textareaClassName}
          />
          {generationNotes ? (
            <p className="mt-2 text-xs text-indigo-900/80">
              {t("generationNotes")}: {generationNotes}
            </p>
          ) : null}
          <button
            type="button"
            onClick={handleApply}
            disabled={!lastSuggestion || loading}
            className="mt-3 self-start rounded border border-indigo-300 bg-white px-4 py-2 text-sm font-medium text-indigo-800 hover:bg-indigo-50 disabled:opacity-50"
          >
            {t("apply")}
          </button>
          <p className="mt-2 text-xs text-gray-500">{t("applyHint")}</p>
        </div>
      </div>

      {error ? (
        <p className="mt-4 text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : null}
    </section>
  );
}
