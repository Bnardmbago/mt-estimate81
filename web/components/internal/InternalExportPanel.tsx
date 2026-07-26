"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import ExportPreviewModal from "@/components/ExportPreviewModal";
import { apiFetch, apiJson, parseApiErrorPayload } from "@/lib/api";
import { formatLocalTimestamp } from "@/lib/datetime";
import type { ExportRecord } from "@/lib/estimate";
import {
  ensureCanvaConnected,
  ensureGoogleConnected,
  formatFamilyLabel,
  isDocxFormat,
  isPdfFormat,
  isXlsxFormat,
  sendEstimateExportToCanva,
  sendEstimateExportToGoogle,
} from "@/lib/export-destinations";

type InternalExportFormat = "pdf" | "xlsx" | "md" | "docx";
type ExportLocale = "ja" | "en";

type InternalExportPanelProps = {
  estimateId: string;
  hasCalculation: boolean;
};

type PreviewTarget = {
  id: string;
  format: string;
};

const FORMAT_OPTIONS: InternalExportFormat[] = ["pdf", "xlsx", "md", "docx"];

const FORMAT_TO_INTERNAL: Record<InternalExportFormat, string> = {
  pdf: "pdf_internal",
  xlsx: "xlsx_internal",
  md: "md_internal",
  docx: "docx_internal",
};

const formatLabelKey: Record<
  InternalExportFormat,
  "formatPdf" | "formatXlsx" | "formatMd" | "formatDocx"
> = {
  pdf: "formatPdf",
  xlsx: "formatXlsx",
  md: "formatMd",
  docx: "formatDocx",
};

function exportFormatLabel(format: string, t: (key: string) => string): string {
  if (format === "pdf_internal") return t("formatPdf");
  if (format === "docx_internal") return t("formatDocx");
  if (format === "xlsx_internal") return t("formatXlsx");
  if (format === "md_internal") return t("formatMd");
  return format.toUpperCase();
}

export default function InternalExportPanel({
  estimateId,
  hasCalculation,
}: InternalExportPanelProps) {
  const locale = useLocale();
  const t = useTranslations("export");
  const tDossier = useTranslations("internalDossier");
  const [exports, setExports] = useState<ExportRecord[]>([]);
  const [exportLocale, setExportLocale] = useState<ExportLocale>(
    () => (locale === "ja" ? "ja" : "en"),
  );
  const [selectedFormats, setSelectedFormats] = useState<Set<InternalExportFormat>>(
    () => new Set(["pdf"]),
  );
  const [selectedExportIds, setSelectedExportIds] = useState<Set<string>>(
    () => new Set(),
  );
  const [previewTarget, setPreviewTarget] = useState<PreviewTarget | null>(null);
  const [confirmingDeleteId, setConfirmingDeleteId] = useState<string | null>(null);
  const [deletingExportId, setDeletingExportId] = useState<string | null>(null);
  const [sendingDestinationId, setSendingDestinationId] = useState<string | null>(null);
  const [toEmail, setToEmail] = useState("");
  const [emailMessage, setEmailMessage] = useState("");
  const [exporting, setExporting] = useState(false);
  const [sendingEmail, setSendingEmail] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [emailSuccess, setEmailSuccess] = useState<string | null>(null);

  const loadExports = useCallback(async () => {
    try {
      const records = await apiJson<ExportRecord[]>(
        `/estimates/${estimateId}/exports?audience=internal`,
      );
      setExports(records);
    } catch {
      setExports([]);
    } finally {
      setLoading(false);
    }
  }, [estimateId]);

  useEffect(() => {
    void loadExports();
  }, [loadExports]);

  useEffect(() => {
    async function loadProfile() {
      try {
        const profile = await apiJson<{ email: string }>("/auth/me");
        setToEmail(profile.email);
      } catch {
        // Keep recipient field empty if profile cannot be loaded.
      }
    }

    void loadProfile();
  }, []);

  function toggleFormat(format: InternalExportFormat) {
    setSelectedFormats((current) => {
      const next = new Set(current);
      if (next.has(format)) {
        if (next.size > 1) {
          next.delete(format);
        }
      } else {
        next.add(format);
      }
      return next;
    });
  }

  function toggleExportSelection(exportId: string) {
    setSelectedExportIds((current) => {
      const next = new Set(current);
      if (next.has(exportId)) {
        next.delete(exportId);
      } else {
        next.add(exportId);
      }
      return next;
    });
  }

  async function handleExport() {
    if (selectedFormats.size === 0 || !hasCalculation) {
      return;
    }

    setExporting(true);
    setError(null);
    setEmailSuccess(null);

    try {
      let lastPdfPreview: PreviewTarget | null = null;

      for (const format of selectedFormats) {
        const exportFormat = FORMAT_TO_INTERNAL[format];
        const response = await apiFetch(`/estimates/${estimateId}/export`, {
          method: "POST",
          body: JSON.stringify({ format: exportFormat, locale: exportLocale }),
        });

        if (!response.ok) {
          const payload = await response.json().catch(() => ({}));
          throw new Error(parseApiErrorPayload(payload, t("exportError")).message);
        }

        const record = (await response.json()) as ExportRecord;
        // Auto-open preview only for PDF; DOCX/XLSX/MD go straight to the list.
        if (isPdfFormat(record.format)) {
          lastPdfPreview = { id: record.id, format: record.format };
        }
      }

      await loadExports();

      if (lastPdfPreview) {
        setPreviewTarget(lastPdfPreview);
      }
    } catch (exportError) {
      setError(exportError instanceof Error ? exportError.message : t("exportError"));
    } finally {
      setExporting(false);
    }
  }

  async function handleDelete(exportId: string) {
    setDeletingExportId(exportId);
    setError(null);
    setEmailSuccess(null);

    try {
      const response = await apiFetch(`/exports/${exportId}`, { method: "DELETE" });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(parseApiErrorPayload(payload, t("deleteError")).message);
      }

      setSelectedExportIds((current) => {
        const next = new Set(current);
        next.delete(exportId);
        return next;
      });
      if (previewTarget?.id === exportId) {
        setPreviewTarget(null);
      }
      setConfirmingDeleteId(null);
      await loadExports();
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : t("deleteError"));
    } finally {
      setDeletingExportId(null);
    }
  }

  async function handleOpenInGoogle(record: ExportRecord) {
    if (!isDocxFormat(record.format) && !isXlsxFormat(record.format)) {
      return;
    }
    setSendingDestinationId(record.id);
    setError(null);
    try {
      const connected = await ensureGoogleConnected();
      if (!connected) {
        return;
      }
      const result = await sendEstimateExportToGoogle(record.id);
      if (result.external_url) {
        window.open(result.external_url, "_blank", "noopener,noreferrer");
      }
      await loadExports();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("sendToDestinationError"));
    } finally {
      setSendingDestinationId(null);
    }
  }

  async function handleOpenInCanva(record: ExportRecord) {
    if (!isPdfFormat(record.format)) {
      return;
    }
    setSendingDestinationId(record.id);
    setError(null);
    try {
      const connected = await ensureCanvaConnected();
      if (!connected) {
        return;
      }
      const result = await sendEstimateExportToCanva(record.id);
      if (result.external_url) {
        window.open(result.external_url, "_blank", "noopener,noreferrer");
      }
      await loadExports();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("sendToDestinationError"));
    } finally {
      setSendingDestinationId(null);
    }
  }

  async function handleSendEmail() {
    if (selectedExportIds.size === 0) {
      setError(t("emailSelectRequired"));
      setEmailSuccess(null);
      return;
    }

    if (!toEmail.trim()) {
      setError(t("emailError"));
      setEmailSuccess(null);
      return;
    }

    setSendingEmail(true);
    setError(null);
    setEmailSuccess(null);

    try {
      const response = await apiFetch(`/estimates/${estimateId}/exports/email`, {
        method: "POST",
        body: JSON.stringify({
          to_email: toEmail.trim(),
          export_ids: Array.from(selectedExportIds),
          message: emailMessage.trim() || null,
        }),
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(parseApiErrorPayload(payload, t("emailError")).message);
      }

      setEmailSuccess(t("emailSuccess"));
      setSelectedExportIds(new Set());
    } catch (sendError) {
      setError(sendError instanceof Error ? sendError.message : t("emailError"));
    } finally {
      setSendingEmail(false);
    }
  }

  const exportDisabled = exporting || selectedFormats.size === 0 || !hasCalculation;

  const sortedExports = useMemo(
    () =>
      [...exports].sort(
        (a, b) => new Date(b.generated_at).getTime() - new Date(a.generated_at).getTime(),
      ),
    [exports],
  );

  return (
    <section className="rounded-lg border border-dashed border-gray-300 p-4 dark:border-gray-600">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          {tDossier("exportSectionTitle")}
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {tDossier("exportDescription")}
        </p>
      </div>

      {!hasCalculation ? (
        <p className="mb-4 text-sm text-amber-700 dark:text-amber-300" role="note">
          {tDossier("exportCalculationRequiredHint")}
        </p>
      ) : null}

      <div className="mb-4">
        <p className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">
          {t("localeLabel")}
        </p>
        <div className="mb-4 flex flex-wrap gap-4">
          {(["ja", "en"] as const).map((value) => (
            <label
              key={value}
              className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300"
            >
              <input
                type="radio"
                name="internal-export-locale"
                checked={exportLocale === value}
                onChange={() => setExportLocale(value)}
                disabled={!hasCalculation}
                className="border-gray-300 text-indigo-600"
              />
              {t(value === "ja" ? "localeJa" : "localeEn")}
            </label>
          ))}
        </div>
      </div>

      <div className="mb-4">
        <p className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">
          {t("formatsLabel")}
        </p>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap gap-4">
            {FORMAT_OPTIONS.map((format) => (
              <label
                key={format}
                className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300"
              >
                <input
                  type="checkbox"
                  checked={selectedFormats.has(format)}
                  onChange={() => toggleFormat(format)}
                  disabled={!hasCalculation}
                  className="rounded border-gray-300"
                />
                {t(formatLabelKey[format])}
              </label>
            ))}
          </div>
          <button
            type="button"
            onClick={() => void handleExport()}
            disabled={exportDisabled}
            className="shrink-0 rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {exporting ? t("exporting") : t("exportButton")}
          </button>
        </div>
      </div>

      {error && (
        <p className="mb-4 text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      {emailSuccess && (
        <p className="mb-4 text-sm text-green-700" role="status">
          {emailSuccess}
        </p>
      )}

      <div>
        <h3 className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">
          {t("downloadsTitle")}
        </h3>
        {loading ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">{t("loading")}</p>
        ) : sortedExports.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">{tDossier("exportEmpty")}</p>
        ) : (
          <ul className="divide-y divide-gray-100 rounded-md border border-gray-200 dark:divide-gray-800 dark:border-gray-700">
            {sortedExports.map((record) => {
              const isConfirmingDelete = confirmingDeleteId === record.id;
              const isDeleting = deletingExportId === record.id;

              return (
                <li
                  key={record.id}
                  className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
                >
                  <label className="flex items-start gap-3 text-sm text-gray-700 dark:text-gray-300">
                    <input
                      type="checkbox"
                      checked={selectedExportIds.has(record.id)}
                      onChange={() => toggleExportSelection(record.id)}
                      className="mt-0.5 rounded border-gray-300"
                      aria-label={t("emailSelectLabel")}
                    />
                    <span
                      className="mt-0.5 inline-flex w-14 shrink-0 justify-center rounded bg-gray-100 px-1.5 py-0.5 text-xs font-semibold tracking-wide text-gray-800 dark:bg-gray-800 dark:text-gray-100"
                      title={t("formatsLabel")}
                    >
                      {formatFamilyLabel(record.format)}
                    </span>
                    <span>
                      <span className="font-medium">{exportFormatLabel(record.format, t)}</span>
                      <span className="mx-2 text-gray-400">·</span>
                      <span>{record.locale.toUpperCase()}</span>
                      <span className="mx-2 text-gray-400">·</span>
                      <span className="text-gray-500 dark:text-gray-400">
                        {formatLocalTimestamp(record.generated_at, locale)}
                      </span>
                      {record.manually_edited_at ? (
                        <span className="mt-1 inline-flex rounded bg-amber-100 px-1.5 py-0.5 text-xs font-medium text-amber-900">
                          {t("externallyEditedBadge")}
                        </span>
                      ) : null}
                    </span>
                  </label>
                  <div className="flex flex-wrap items-center gap-2 sm:ml-4">
                    <button
                      type="button"
                      onClick={() =>
                        setPreviewTarget({ id: record.id, format: record.format })
                      }
                      className="header-btn text-xs"
                    >
                      {t("preview")}
                    </button>
                    <a
                      href={`/api/exports/${record.id}/download`}
                      className="header-btn text-xs"
                    >
                      {t("download")}
                    </a>
                    {isDocxFormat(record.format) ? (
                      <button
                        type="button"
                        disabled={sendingDestinationId === record.id}
                        onClick={() => void handleOpenInGoogle(record)}
                        className="header-btn text-xs disabled:opacity-50"
                      >
                        {sendingDestinationId === record.id
                          ? t("exporting")
                          : t("openInDocs")}
                      </button>
                    ) : null}
                    {isXlsxFormat(record.format) ? (
                      <button
                        type="button"
                        disabled={sendingDestinationId === record.id}
                        onClick={() => void handleOpenInGoogle(record)}
                        className="header-btn text-xs disabled:opacity-50"
                      >
                        {sendingDestinationId === record.id
                          ? t("exporting")
                          : t("openInSheets")}
                      </button>
                    ) : null}
                    {isPdfFormat(record.format) ? (
                      <button
                        type="button"
                        disabled={sendingDestinationId === record.id}
                        onClick={() => void handleOpenInCanva(record)}
                        className="header-btn text-xs disabled:opacity-50"
                      >
                        {sendingDestinationId === record.id
                          ? t("exporting")
                          : t("openInCanva")}
                      </button>
                    ) : null}
                    {record.external_url ? (
                      <a
                        href={record.external_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="header-btn text-xs"
                      >
                        {record.destination === "canva"
                          ? t("openInCanva")
                          : record.destination === "google_sheets"
                            ? t("openInSheets")
                            : t("openInDocs")}
                      </a>
                    ) : null}
                    {isConfirmingDelete ? (
                      <div className="inline-flex flex-wrap items-center gap-2">
                        <span className="text-xs text-gray-600 dark:text-gray-400">
                          {t("deleteConfirm")}
                        </span>
                        <button
                          type="button"
                          onClick={() => setConfirmingDeleteId(null)}
                          disabled={isDeleting}
                          className="header-btn text-xs disabled:opacity-50"
                        >
                          {t("deleteCancel")}
                        </button>
                        <button
                          type="button"
                          onClick={() => void handleDelete(record.id)}
                          disabled={isDeleting}
                          className="header-btn text-xs text-red-700 disabled:opacity-50"
                        >
                          {isDeleting ? t("deleting") : t("deleteConfirmAction")}
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={() => {
                          setError(null);
                          setConfirmingDeleteId(record.id);
                        }}
                        className="header-btn text-xs text-red-700"
                      >
                        {t("delete")}
                      </button>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {exports.length > 0 && (
        <div className="mt-6 rounded-md border border-gray-200 p-4 dark:border-gray-700">
          <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">
            {t("emailTitle")}
          </h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {t("emailDescription")}
          </p>

          <div className="mt-4 space-y-4">
            <div>
              <label
                htmlFor="internal-export-email-to"
                className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
              >
                {t("emailToLabel")}
              </label>
              <input
                id="internal-export-email-to"
                type="email"
                value={toEmail}
                onChange={(event) => setToEmail(event.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900"
                autoComplete="email"
              />
            </div>

            <div>
              <label
                htmlFor="internal-export-email-message"
                className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
              >
                {t("emailMessageLabel")}
              </label>
              <textarea
                id="internal-export-email-message"
                value={emailMessage}
                onChange={(event) => setEmailMessage(event.target.value)}
                rows={3}
                placeholder={t("emailMessagePlaceholder")}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900"
              />
            </div>

            <button
              type="button"
              onClick={() => void handleSendEmail()}
              disabled={sendingEmail || selectedExportIds.size === 0 || !toEmail.trim()}
              className="rounded border border-indigo-600 px-4 py-2 text-sm font-medium text-indigo-600 hover:bg-indigo-50 disabled:opacity-50"
            >
              {sendingEmail ? t("emailSending") : t("emailSendButton")}
            </button>
          </div>
        </div>
      )}

      {previewTarget && (
        <ExportPreviewModal
          exportId={previewTarget.id}
          format={previewTarget.format}
          onClose={() => setPreviewTarget(null)}
        />
      )}
    </section>
  );
}
