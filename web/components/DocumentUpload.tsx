"use client";

import { DragEvent, useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { apiFetch } from "@/lib/api";
import type { EstimateDocument } from "@/lib/estimate";

type DocumentUploadProps = {
  estimateId: string;
  initialDocuments: EstimateDocument[];
  onDocumentsChange?: (documents: EstimateDocument[]) => void;
};

const SUPPORTED_EXTENSIONS = ["pdf", "docx", "xlsx", "txt", "md"];

const textareaClassName =
  "min-h-[10rem] w-full flex-1 resize-y rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

const statusBadgeClassName: Record<string, string> = {
  pending: "bg-gray-100 text-gray-700",
  processing: "bg-yellow-100 text-yellow-800",
  done: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
};

function getFileExtension(filename: string): string {
  const parts = filename.split(".");
  return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : "";
}

export default function DocumentUpload({
  estimateId,
  initialDocuments,
  onDocumentsChange,
}: DocumentUploadProps) {
  const router = useRouter();
  const t = useTranslations("documents");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [documents, setDocuments] = useState<EstimateDocument[]>(initialDocuments);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionId, setActionId] = useState<string | null>(null);
  const [aiPrompt, setAiPrompt] = useState("");

  useEffect(() => {
    setDocuments(initialDocuments);
  }, [initialDocuments]);

  useEffect(() => {
    onDocumentsChange?.(documents);
  }, [documents, onDocumentsChange]);

  const hasProcessing = documents.some(
    (doc) => doc.extraction_status === "pending" || doc.extraction_status === "processing",
  );

  useEffect(() => {
    if (!hasProcessing) {
      return;
    }

    const interval = window.setInterval(() => {
      router.refresh();
    }, 3000);

    return () => window.clearInterval(interval);
  }, [hasProcessing, router]);

  const uploadFiles = useCallback(
    async (files: FileList | File[]) => {
      const fileList = Array.from(files);
      if (fileList.length === 0) {
        return;
      }

      setError(null);
      setUploading(true);

      try {
        for (const file of fileList) {
          const extension = getFileExtension(file.name);
          if (!SUPPORTED_EXTENSIONS.includes(extension)) {
            throw new Error(t("unsupportedType", { type: extension || "unknown" }));
          }

          const formData = new FormData();
          formData.append("file", file);

          const response = await apiFetch(`/estimates/${estimateId}/documents`, {
            method: "POST",
            body: formData,
          });

          if (!response.ok) {
            const payload = await response.json().catch(() => ({}));
            const message =
              typeof payload.detail === "object"
                ? payload.detail.error
                : payload.detail || response.statusText;
            throw new Error(message || t("uploadError"));
          }

          const uploaded = (await response.json()) as EstimateDocument;
          setDocuments((current) => [...current, uploaded]);
        }

        router.refresh();
      } catch (uploadError) {
        setError(uploadError instanceof Error ? uploadError.message : t("uploadError"));
      } finally {
        setUploading(false);
      }
    },
    [estimateId, router, t],
  );

  function handleDragOver(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(true);
  }

  function handleDragLeave(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    if (event.dataTransfer.files.length > 0) {
      void uploadFiles(event.dataTransfer.files);
    }
  }

  async function handleDelete(documentId: string) {
    setActionId(documentId);
    setError(null);

    try {
      const response = await apiFetch(`/estimates/${estimateId}/documents/${documentId}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error(t("deleteError"));
      }

      setDocuments((current) => current.filter((doc) => doc.id !== documentId));
      router.refresh();
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : t("deleteError"));
    } finally {
      setActionId(null);
    }
  }

  async function handleRetry(documentId: string) {
    setActionId(documentId);
    setError(null);

    try {
      const response = await apiFetch(
        `/estimates/${estimateId}/documents/${documentId}/retry`,
        { method: "POST" },
      );

      if (!response.ok) {
        throw new Error(t("retryError"));
      }

      const updated = (await response.json()) as EstimateDocument;
      setDocuments((current) =>
        current.map((doc) => (doc.id === documentId ? updated : doc)),
      );
      router.refresh();
    } catch (retryError) {
      setError(retryError instanceof Error ? retryError.message : t("retryError"));
    } finally {
      setActionId(null);
    }
  }

  return (
    <section className="mt-8 border-t border-gray-200 pt-8">
      <h2 className="mb-1 text-lg font-semibold">{t("title")}</h2>
      <p className="mb-4 text-sm text-gray-500">{t("description")}</p>

      <div className="mb-4 grid gap-4 lg:grid-cols-2">
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`flex cursor-pointer flex-col justify-center rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors ${
            isDragging
              ? "border-blue-500 bg-blue-50"
              : "border-gray-300 bg-gray-50 hover:border-blue-400 hover:bg-blue-50/50"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.docx,.xlsx,.txt,.md"
            className="hidden"
            onChange={(event) => {
              if (event.target.files) {
                void uploadFiles(event.target.files);
                event.target.value = "";
              }
            }}
          />
          <p className="text-sm font-medium text-gray-700">
            {uploading ? t("uploading") : t("dropzone")}
          </p>
          <p className="mt-1 text-xs text-gray-500">{t("supportedTypes")}</p>
        </div>

        <div className="flex flex-col" onClick={(event) => event.stopPropagation()}>
          <label htmlFor="ai-prompt" className="mb-1 text-sm font-medium text-gray-700">
            {t("aiPromptLabel")}
          </label>
          <textarea
            id="ai-prompt"
            value={aiPrompt}
            onChange={(event) => setAiPrompt(event.target.value)}
            placeholder={t("aiPromptPlaceholder")}
            rows={6}
            className={textareaClassName}
          />
        </div>
      </div>

      {error && (
        <p className="mb-4 text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      {documents.length === 0 ? (
        <p className="text-sm text-gray-500">{t("empty")}</p>
      ) : (
        <ul className="divide-y divide-gray-200 rounded-lg border border-gray-200">
          {documents.map((document) => {
            const badgeClass =
              statusBadgeClassName[document.extraction_status] ??
              "bg-gray-100 text-gray-700";
            const isBusy = actionId === document.id;

            return (
              <li
                key={document.id}
                className="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-gray-900">
                    {document.original_filename}
                  </p>
                  <p className="text-xs uppercase text-gray-500">{document.file_type}</p>
                  {document.extraction_status === "failed" && document.extracted_text && (
                    <p className="mt-1 text-xs text-red-600">{document.extracted_text}</p>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-xs font-medium uppercase tracking-wide ${badgeClass}`}
                  >
                    {t(`status.${document.extraction_status}`)}
                  </span>

                  {document.extraction_status === "failed" && (
                    <button
                      type="button"
                      onClick={() => void handleRetry(document.id)}
                      disabled={isBusy}
                      className="rounded border border-gray-300 px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                    >
                      {isBusy ? t("retrying") : t("retry")}
                    </button>
                  )}

                  <button
                    type="button"
                    onClick={() => void handleDelete(document.id)}
                    disabled={isBusy}
                    className="rounded border border-red-200 px-2.5 py-1 text-xs font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
                  >
                    {isBusy ? t("deleting") : t("delete")}
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
