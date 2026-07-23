"use client";

import { useCallback, useEffect, useMemo, useState, type RefObject } from "react";
import { useLocale, useTranslations } from "next-intl";
import DocumentUpload from "@/components/DocumentUpload";
import type { EstimateFormHandle } from "@/components/EstimateForm";
import { apiFetch, parseApiErrorPayload } from "@/lib/api";
import AiGenerationProgress from "@/components/AiGenerationProgress";
import { MAX_AI_USER_PROMPT_CHARS } from "@/lib/aiConstants";
import { isUsableProjectName, resolveProjectNameForSave } from "@/lib/formFields";
import {
  type FormFieldValues,
  resolveFormSchema,
} from "@/lib/formSchema";
import { formatFormDataPreview } from "@/lib/formPreview";
import type { EstimateDetail, EstimateDocument } from "@/lib/estimate";

type EstimateAiSpecPanelProps = {
  estimateId: string;
  estimate: EstimateDetail;
  formRef: RefObject<EstimateFormHandle | null>;
  initialDocuments: EstimateDocument[];
  onDocumentsChange?: (documents: EstimateDocument[]) => void;
};

type SuggestFormResponse = {
  form_data: Record<string, string>;
  generation_notes: string;
};

const textareaClassName =
  "min-h-[10rem] w-full resize-y rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

async function readApiError(response: Response, fallback: string): Promise<string> {
  const payload = await response.json().catch(() => ({}));
  const record = payload as Record<string, unknown>;
  const { message, code } = parseApiErrorPayload(payload, fallback);
  if (code === "AI_UNAVAILABLE") {
    const details = record.details as { message?: string } | undefined;
    if (details?.message?.trim()) {
      return `${message}: ${details.message}`;
    }
  }
  return message;
}

export default function EstimateAiSpecPanel({
  estimateId,
  estimate,
  formRef,
  initialDocuments,
  onDocumentsChange,
}: EstimateAiSpecPanelProps) {
  const locale = useLocale();
  const t = useTranslations("aiSpec");

  const schema = useMemo(
    () => resolveFormSchema(estimate.form_schema_snapshot),
    [estimate.form_schema_snapshot],
  );

  const [documents, setDocuments] = useState<EstimateDocument[]>(initialDocuments);
  const [prompt, setPrompt] = useState("");
  const [previewText, setPreviewText] = useState("");
  const [lastSuggestion, setLastSuggestion] = useState<SuggestFormResponse | null>(null);
  const [generationNotes, setGenerationNotes] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDocuments(initialDocuments);
  }, [initialDocuments]);

  const handleDocumentsChange = useCallback(
    (nextDocuments: EstimateDocument[]) => {
      setDocuments(nextDocuments);
      onDocumentsChange?.(nextDocuments);
    },
    [onDocumentsChange],
  );

  const hasProcessingDocuments = documents.some(
    (doc) => doc.extraction_status === "pending" || doc.extraction_status === "processing",
  );

  const hasReadyDocuments = documents.some((doc) => doc.extraction_status === "done");

  const canGenerate =
    (prompt.trim().length > 0 || hasReadyDocuments) && !loading && !hasProcessingDocuments;

  async function handleGenerate() {
    const promptText = prompt.trim();
    if (!promptText && !hasReadyDocuments) {
      setError(t("promptOrDocumentsRequired"));
      return;
    }

    const values = formRef.current?.getValues();
    const projectName = resolveProjectNameForSave(
      values?.project_name ?? "",
      estimate.project_name,
    );
    if (!isUsableProjectName(projectName)) {
      setError(t("projectNameRequired"));
      void formRef.current?.saveProjectName();
      return;
    }

    setError(null);
    setLoading(true);

    const projectSaved = await formRef.current?.saveBeforeAiSuggest();
    if (projectSaved === false) {
      setError(
        isUsableProjectName(projectName) ? t("saveFormBeforeGenerate") : t("projectNameRequired"),
      );
      setLoading(false);
      return;
    }

    try {
      const response = await apiFetch(
        `/estimates/${estimateId}/ai/suggest-form`,
        {
          method: "POST",
          body: JSON.stringify({
            prompt: promptText,
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
    formRef.current?.startPostApplyGuidance();
  }

  return (
    <section className="rounded-lg border border-indigo-100 bg-indigo-50/40 p-4">
      <h2 className="text-lg font-semibold text-gray-900">{t("title")}</h2>
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
            maxLength={MAX_AI_USER_PROMPT_CHARS}
            disabled={loading}
            className={textareaClassName}
          />
          <DocumentUpload
            estimateId={estimateId}
            initialDocuments={initialDocuments}
            onDocumentsChange={handleDocumentsChange}
            variant="embedded"
          />
          {hasProcessingDocuments ? (
            <p className="mt-2 text-xs text-indigo-800/80">{t("processingDocuments")}</p>
          ) : null}
          <button
            type="button"
            onClick={() => void handleGenerate()}
            disabled={!canGenerate}
            className="mt-3 self-start rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {loading ? t("generating") : t("generate")}
          </button>
          {loading ? (
            <div className="mt-3">
              <AiGenerationProgress active compact />
            </div>
          ) : null}
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
