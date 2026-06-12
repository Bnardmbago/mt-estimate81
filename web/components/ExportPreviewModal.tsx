"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { apiFetch } from "@/lib/api";

type ExportPreviewModalProps = {
  exportId: string;
  format: string;
  onClose: () => void;
};

export default function ExportPreviewModal({
  exportId,
  format,
  onClose,
}: ExportPreviewModalProps) {
  const t = useTranslations("export");
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [markdown, setMarkdown] = useState<string | null>(null);
  const [loading, setLoading] = useState(format === "md");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }
    document.addEventListener("keydown", onKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = "";
    };
  }, [onClose]);

  useEffect(() => {
    if (format !== "md") {
      return;
    }

    let cancelled = false;
    async function loadMarkdown() {
      setLoading(true);
      setError(null);
      try {
        const response = await apiFetch(`/exports/${exportId}/download?inline=1`);
        if (!response.ok) {
          throw new Error(t("previewError"));
        }
        const text = await response.text();
        if (!cancelled) {
          setMarkdown(text);
        }
      } catch (previewError) {
        if (!cancelled) {
          setError(
            previewError instanceof Error ? previewError.message : t("previewError"),
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadMarkdown();
    return () => {
      cancelled = true;
    };
  }, [exportId, format, t]);

  const previewUrl = `/api/exports/${exportId}/download?inline=1`;

  function handlePrint() {
    if (format === "pdf") {
      iframeRef.current?.contentWindow?.print();
      return;
    }
    if (format === "md") {
      window.print();
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 print-preview-backdrop"
      role="presentation"
      onClick={onClose}
    >
      <style jsx global>{`
        @media print {
          body * {
            visibility: hidden;
          }
          .print-preview-content,
          .print-preview-content * {
            visibility: visible;
          }
          .print-preview-backdrop {
            position: static;
            background: transparent;
            padding: 0;
          }
          .print-preview-dialog {
            box-shadow: none;
            max-height: none;
            width: 100%;
            max-width: none;
          }
          .print-preview-toolbar {
            display: none !important;
          }
          .print-preview-content {
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
            padding: 0;
          }
        }
      `}</style>
      <div
        className="print-preview-dialog flex max-h-[90vh] w-full max-w-5xl flex-col rounded-lg bg-white shadow-xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="export-preview-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="print-preview-toolbar flex items-center justify-between border-b border-gray-200 px-4 py-3">
          <h2 id="export-preview-title" className="text-base font-semibold text-gray-900">
            {t("previewTitle")}
          </h2>
          <div className="flex items-center gap-2">
            {(format === "pdf" || format === "md") && (
              <button
                type="button"
                onClick={handlePrint}
                className="rounded px-3 py-1.5 text-sm font-medium text-indigo-600 hover:bg-indigo-50"
              >
                {t("previewPrint")}
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              className="rounded px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100"
            >
              {t("previewClose")}
            </button>
          </div>
        </div>

        <div className="print-preview-content min-h-0 flex-1 overflow-auto p-4">
          {format === "pdf" && (
            <iframe
              ref={iframeRef}
              title={t("previewTitle")}
              src={previewUrl}
              className="h-[75vh] w-full rounded border border-gray-200 bg-gray-50"
            />
          )}

          {format === "md" && (
            <>
              {loading && <p className="text-sm text-gray-500">{t("previewLoading")}</p>}
              {error && (
                <p className="text-sm text-red-600" role="alert">
                  {error}
                </p>
              )}
              {markdown && (
                <pre className="whitespace-pre-wrap rounded border border-gray-200 bg-gray-50 p-4 text-xs text-gray-800">
                  {markdown}
                </pre>
              )}
            </>
          )}

          {format === "xlsx" && (
            <div className="rounded border border-gray-200 bg-gray-50 p-6 text-sm text-gray-700">
              <p>{t("previewXlsxHint")}</p>
              <a
                href={`/api/exports/${exportId}/download`}
                className="mt-3 inline-block font-medium text-indigo-600 hover:text-indigo-800"
              >
                {t("download")}
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
