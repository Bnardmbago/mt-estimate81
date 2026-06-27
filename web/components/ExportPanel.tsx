"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { type CalculationResult } from "@/components/CalculationBreakdown";
import ExportPreviewModal from "@/components/ExportPreviewModal";
import { apiFetch, apiJson } from "@/lib/api";
import { formatLocalTimestamp, parseUtcTimestamp } from "@/lib/datetime";
import type { ExportRecord } from "@/lib/estimate";

type ExportFormat = "pdf" | "xlsx" | "md" | "docx";
type PdfVersion = "pdf" | "pdf_quotation";
type DocxVersion = "docx" | "docx_quotation";
type ExportLocale = "ja" | "en";

type ExportPanelProps = {
  estimateId: string;
  estimateUpdatedAt: string;
  calculationResult: CalculationResult;
  isContactUser?: boolean;
};

const CONTACT_EXPORT_LIMIT = 3;

type UserProfile = {
  email: string;
};

type PreviewTarget = {
  id: string;
  format: string;
};

const FORMAT_OPTIONS: ExportFormat[] = ["pdf", "xlsx", "md", "docx"];

const PDF_VERSION_OPTIONS: PdfVersion[] = ["pdf", "pdf_quotation"];

const DOCX_VERSION_OPTIONS: DocxVersion[] = ["docx", "docx_quotation"];

const pdfVersionLabelKey: Record<
  PdfVersion,
  "pdfVersionReport" | "pdfVersionQuotation"
> = {
  pdf: "pdfVersionReport",
  pdf_quotation: "pdfVersionQuotation",
};

const docxVersionLabelKey: Record<
  DocxVersion,
  "pdfVersionReport" | "pdfVersionQuotation"
> = {
  docx: "pdfVersionReport",
  docx_quotation: "pdfVersionQuotation",
};

function exportFormatLabel(
  format: string,
  t: (key: string) => string,
): string {
  if (format === "pdf") return t("pdfVersionReport");
  if (format === "pdf_quotation") return t("pdfVersionQuotation");
  if (format === "docx") return t("pdfVersionReport");
  if (format === "docx_quotation") return t("pdfVersionQuotation");
  if (format === "pdf_preliminary") return t("pdfVersionPreliminary");
  if (format === "xlsx") return t("formatXlsx");
  if (format === "md") return t("formatMd");
  return format.toUpperCase();
}

const formatLabelKey: Record<
  ExportFormat,
  "formatPdf" | "formatXlsx" | "formatMd" | "formatDocx"
> = {
  pdf: "formatPdf",
  xlsx: "formatXlsx",
  md: "formatMd",
  docx: "formatDocx",
};

function parseApiError(payload: unknown, fallback: string): string {
  if (typeof payload !== "object" || payload === null) {
    return fallback;
  }
  const record = payload as Record<string, unknown>;
  if (typeof record.error === "string") {
    return record.error;
  }
  const detail = record.detail;
  if (typeof detail === "object" && detail !== null && "error" in detail) {
    const message = (detail as { error?: unknown }).error;
    if (typeof message === "string") {
      return message;
    }
  }
  if (typeof detail === "string") {
    return detail;
  }
  return fallback;
}

export default function ExportPanel({
  estimateId,
  estimateUpdatedAt,
  calculationResult,
  isContactUser = false,
}: ExportPanelProps) {
  const locale = useLocale();
  const router = useRouter();
  const t = useTranslations("export");
  const [exports, setExports] = useState<ExportRecord[]>([]);
  const [exportLocale, setExportLocale] = useState<ExportLocale>(
    () => (locale === "ja" ? "ja" : "en"),
  );
  const [selectedFormats, setSelectedFormats] = useState<Set<ExportFormat>>(
    () => new Set(["pdf"]),
  );
  const [pdfVersion, setPdfVersion] = useState<PdfVersion>("pdf");
  const [docxVersion, setDocxVersion] = useState<DocxVersion>("docx");
  const [selectedExportIds, setSelectedExportIds] = useState<Set<string>>(
    () => new Set(),
  );
  const [previewTarget, setPreviewTarget] = useState<PreviewTarget | null>(null);
  const [confirmingDeleteId, setConfirmingDeleteId] = useState<string | null>(null);
  const [deletingExportId, setDeletingExportId] = useState<string | null>(null);
  const [toEmail, setToEmail] = useState("");
  const [emailMessage, setEmailMessage] = useState("");
  const [exporting, setExporting] = useState(false);
  const [sendingEmail, setSendingEmail] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [emailSuccess, setEmailSuccess] = useState<string | null>(null);

  const loadExports = useCallback(async () => {
    try {
      const records = await apiJson<ExportRecord[]>(`/estimates/${estimateId}/exports`);
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
        const profile = await apiJson<UserProfile>("/auth/me");
        setToEmail(profile.email);
      } catch {
        // Keep recipient field empty if profile cannot be loaded.
      }
    }

    void loadProfile();
  }, []);

  const latestExportAt = useMemo(() => {
    if (exports.length === 0) {
      return null;
    }
    return exports.reduce((latest, record) => {
      return new Date(record.generated_at) > new Date(latest) ? record.generated_at : latest;
    }, exports[0].generated_at);
  }, [exports]);

  const isStale = useMemo(() => {
    if (!latestExportAt) {
      return false;
    }
    return (
      new Date(estimateUpdatedAt).getTime() > parseUtcTimestamp(latestExportAt).getTime()
    );
  }, [estimateUpdatedAt, latestExportAt]);

  function toggleFormat(format: ExportFormat) {
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
    if (selectedFormats.size === 0) {
      return;
    }

    setExporting(true);
    setError(null);
    setEmailSuccess(null);

    try {
      let lastCreated: PreviewTarget | null = null;

      for (const format of selectedFormats) {
        const exportFormat =
          format === "pdf" ? pdfVersion : format === "docx" ? docxVersion : format;
        const response = await apiFetch(`/estimates/${estimateId}/export`, {
          method: "POST",
          body: JSON.stringify({ format: exportFormat, locale: exportLocale }),
        });

        if (!response.ok) {
          const payload = await response.json().catch(() => ({}));
          throw new Error(parseApiError(payload, t("exportError")));
        }

        const record = (await response.json()) as ExportRecord;
        lastCreated = { id: record.id, format: record.format };
      }

      await loadExports();
      router.refresh();

      if (isContactUser && toEmail) {
        setEmailSuccess(t("contactExportEmailed", { email: toEmail }));
      }

      if (lastCreated) {
        setPreviewTarget(lastCreated);
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
        throw new Error(parseApiError(payload, t("deleteError")));
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
      router.refresh();
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : t("deleteError"));
    } finally {
      setDeletingExportId(null);
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
        throw new Error(parseApiError(payload, t("emailError")));
      }

      setEmailSuccess(t("emailSuccess"));
      setSelectedExportIds(new Set());
      router.refresh();
    } catch (sendError) {
      setError(sendError instanceof Error ? sendError.message : t("emailError"));
    } finally {
      setSendingEmail(false);
    }
  }

  const exportsRemaining = CONTACT_EXPORT_LIMIT - exports.length;
  const exportLimitReached = isContactUser && exports.length >= CONTACT_EXPORT_LIMIT;

  return (
    <section className="mt-8 border-t border-gray-200 pt-8">
      {isContactUser ? (
        <div className="mb-4 rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900 dark:border-blue-900 dark:bg-blue-950/40 dark:text-blue-100">
          {exportLimitReached
            ? t("contactExportLimitReached", { limit: CONTACT_EXPORT_LIMIT })
            : t("contactExportsRemaining", {
                remaining: exportsRemaining,
                limit: CONTACT_EXPORT_LIMIT,
              })}
          <p className="mt-1 text-blue-800 dark:text-blue-200">{t("contactAutoEmailNote")}</p>
        </div>
      ) : null}
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold">{t("title")}</h2>
            {isStale && (
              <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800">
                {t("staleBadge")}
              </span>
            )}
          </div>
          <p className="text-sm text-gray-500">{t("description")}</p>
        </div>
      </div>

      <div className="mb-8 rounded-lg border border-gray-200 bg-gray-50 px-4 py-3">
        <h3 className="text-base font-semibold text-gray-900">{t("includedDataTitle")}</h3>
        <p className="mt-1 text-sm text-gray-600">{t("includedDataDescription")}</p>
      </div>

      <div className="mb-4">
        <p className="mb-2 text-sm font-medium text-gray-700">{t("localeLabel")}</p>
        <div className="mb-4 flex flex-wrap gap-4">
          {(["ja", "en"] as const).map((value) => (
            <label key={value} className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="radio"
                name="export-locale"
                checked={exportLocale === value}
                onChange={() => setExportLocale(value)}
                className="border-gray-300 text-indigo-600"
              />
              {t(value === "ja" ? "localeJa" : "localeEn")}
            </label>
          ))}
        </div>
      </div>

      <div className="mb-4">
        <p className="mb-2 text-sm font-medium text-gray-700">{t("formatsLabel")}</p>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap gap-4">
            {FORMAT_OPTIONS.map((format) => (
              <label key={format} className="flex items-center gap-2 text-sm text-gray-700">
                <input
                  type="checkbox"
                  checked={selectedFormats.has(format)}
                  onChange={() => toggleFormat(format)}
                  className="rounded border-gray-300"
                />
                {t(formatLabelKey[format])}
              </label>
            ))}
          </div>
          {selectedFormats.has("pdf") && (
            <div className="mb-4 rounded-md border border-gray-200 bg-gray-50 p-4">
              <p className="mb-2 text-sm font-medium text-gray-700">{t("pdfVersionLabel")}</p>
              <div className="flex flex-col gap-2">
                {PDF_VERSION_OPTIONS.map((version) => (
                  <label key={version} className="flex items-center gap-2 text-sm text-gray-700">
                    <input
                      type="radio"
                      name="pdf-version"
                      checked={pdfVersion === version}
                      onChange={() => setPdfVersion(version)}
                      className="border-gray-300 text-indigo-600"
                    />
                    {t(pdfVersionLabelKey[version])}
                  </label>
                ))}
              </div>
            </div>
          )}
          {selectedFormats.has("docx") && (
            <div className="mb-4 rounded-md border border-gray-200 bg-gray-50 p-4">
              <p className="mb-2 text-sm font-medium text-gray-700">{t("docxVersionLabel")}</p>
              <div className="flex flex-col gap-2">
                {DOCX_VERSION_OPTIONS.map((version) => (
                  <label key={version} className="flex items-center gap-2 text-sm text-gray-700">
                    <input
                      type="radio"
                      name="docx-version"
                      checked={docxVersion === version}
                      onChange={() => setDocxVersion(version)}
                      className="border-gray-300 text-indigo-600"
                    />
                    {t(docxVersionLabelKey[version])}
                  </label>
                ))}
              </div>
            </div>
          )}
          <button
            type="button"
            onClick={() => void handleExport()}
            disabled={exporting || selectedFormats.size === 0 || exportLimitReached}
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
        <h3 className="mb-2 text-sm font-medium text-gray-700">{t("downloadsTitle")}</h3>
        {loading ? (
          <p className="text-sm text-gray-500">{t("loading")}</p>
        ) : exports.length === 0 ? (
          <p className="text-sm text-gray-500">{t("empty")}</p>
        ) : (
          <ul className="divide-y divide-gray-100 rounded-md border border-gray-200">
            {exports.map((record) => {
              const isConfirmingDelete = confirmingDeleteId === record.id;
              const isDeleting = deletingExportId === record.id;

              return (
              <li
                key={record.id}
                className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <label className="flex items-start gap-3 text-sm text-gray-700">
                  {!isContactUser ? (
                    <input
                      type="checkbox"
                      checked={selectedExportIds.has(record.id)}
                      onChange={() => toggleExportSelection(record.id)}
                      className="mt-0.5 rounded border-gray-300"
                      aria-label={t("emailSelectLabel")}
                    />
                  ) : null}
                  <span>
                    <span className="font-medium">{exportFormatLabel(record.format, t)}</span>
                    <span className="mx-2 text-gray-400">·</span>
                    <span>{record.locale.toUpperCase()}</span>
                    <span className="mx-2 text-gray-400">·</span>
                    <span className="text-gray-500">
                      {formatLocalTimestamp(record.generated_at, locale)}
                    </span>
                  </span>
                </label>
                <div className="flex flex-wrap items-center gap-3 sm:ml-4">
                  <button
                    type="button"
                    onClick={() =>
                      setPreviewTarget({ id: record.id, format: record.format })
                    }
                    className="text-sm font-medium text-indigo-600 hover:text-indigo-800"
                  >
                    {t("preview")}
                  </button>
                  <a
                    href={`/api/exports/${record.id}/download`}
                    className="text-sm font-medium text-indigo-600 hover:text-indigo-800"
                  >
                    {t("download")}
                  </a>
                  {!isContactUser &&
                    (isConfirmingDelete ? (
                      <div className="inline-flex flex-wrap items-center gap-2">
                        <span className="text-xs text-gray-600">{t("deleteConfirm")}</span>
                        <button
                          type="button"
                          onClick={() => setConfirmingDeleteId(null)}
                          disabled={isDeleting}
                          className="rounded border border-gray-300 px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                        >
                          {t("deleteCancel")}
                        </button>
                        <button
                          type="button"
                          onClick={() => void handleDelete(record.id)}
                          disabled={isDeleting}
                          className="rounded bg-red-600 px-2 py-1 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50"
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
                        className="text-sm font-medium text-red-600 hover:text-red-800"
                      >
                        {t("delete")}
                      </button>
                    ))}
                </div>
              </li>
              );
            })}
          </ul>
        )}
      </div>

      {!isContactUser && exports.length > 0 && (
        <div className="mt-6 rounded-md border border-gray-200 p-4">
          <h3 className="text-sm font-medium text-gray-900">{t("emailTitle")}</h3>
          <p className="mt-1 text-sm text-gray-500">{t("emailDescription")}</p>

          <div className="mt-4 space-y-4">
            <div>
              <label htmlFor="export-email-to" className="mb-1 block text-sm font-medium text-gray-700">
                {t("emailToLabel")}
              </label>
              <input
                id="export-email-to"
                type="email"
                value={toEmail}
                onChange={(event) => setToEmail(event.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                autoComplete="email"
              />
            </div>

            <div>
              <label
                htmlFor="export-email-message"
                className="mb-1 block text-sm font-medium text-gray-700"
              >
                {t("emailMessageLabel")}
              </label>
              <textarea
                id="export-email-message"
                value={emailMessage}
                onChange={(event) => setEmailMessage(event.target.value)}
                rows={3}
                placeholder={t("emailMessagePlaceholder")}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
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
