"use client";

import { useCallback, useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import ExportPreviewModal from "@/components/ExportPreviewModal";
import { apiJson } from "@/lib/api";
import { formatLocalTimestamp } from "@/lib/datetime";
import {
  createProposalExport,
  deleteProposalExport,
  fetchProposalExports,
  sendProposalExportsEmail,
} from "@/lib/proposal";
import type { ProposalDetail, ProposalExportRecord, ProposalLocale } from "@/lib/proposal-types";

type ProposalExportPanelProps = {
  proposal: ProposalDetail;
  onExported: (row: ProposalExportRecord) => void;
  onExportsChanged?: (rows: ProposalExportRecord[]) => void;
};

type PreviewTarget = { id: string; format: string };

export default function ProposalExportPanel({
  proposal,
  onExported,
  onExportsChanged,
}: ProposalExportPanelProps) {
  const t = useTranslations("proposal");
  const tExport = useTranslations("export");
  const locale = useLocale();
  const [format, setFormat] = useState<"pdf" | "docx" | "md" | "xlsx">("pdf");
  const [variant, setVariant] = useState<"full" | "assessment" | "proposal" | "poc">(
    "full",
  );
  const [projectName, setProjectName] = useState(
    () => proposal.source_snapshot?.project_name || "",
  );
  const [exports, setExports] = useState<ProposalExportRecord[]>(
    () => proposal.exports || [],
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewTarget, setPreviewTarget] = useState<PreviewTarget | null>(null);
  const [confirmingDeleteId, setConfirmingDeleteId] = useState<string | null>(null);
  const [deletingExportId, setDeletingExportId] = useState<string | null>(null);
  const [selectedExportIds, setSelectedExportIds] = useState<Set<string>>(
    () => new Set(),
  );
  const [toEmail, setToEmail] = useState("");
  const [emailMessage, setEmailMessage] = useState("");
  const [sendingEmail, setSendingEmail] = useState(false);
  const [emailSuccess, setEmailSuccess] = useState<string | null>(null);

  const syncExports = useCallback(
    (rows: ProposalExportRecord[]) => {
      setExports(rows);
      onExportsChanged?.(rows);
    },
    [onExportsChanged],
  );

  useEffect(() => {
    setProjectName(proposal.source_snapshot?.project_name || "");
  }, [proposal.id, proposal.source_snapshot?.project_name]);

  useEffect(() => {
    let cancelled = false;
    void fetchProposalExports(proposal.id)
      .then((rows) => {
        if (!cancelled) {
          syncExports(rows);
        }
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [proposal.id, syncExports]);

  useEffect(() => {
    async function loadProfile() {
      try {
        const profile = await apiJson<{ email: string }>("/auth/me");
        setToEmail(profile.email);
      } catch {
        // optional
      }
    }
    void loadProfile();
  }, []);

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
    if (proposal.source_stale) {
      const proceed = window.confirm(t("exportStaleConfirm"));
      if (!proceed) {
        return;
      }
    }
    setBusy(true);
    setError(null);
    setEmailSuccess(null);
    try {
      const row = await createProposalExport(proposal.id, {
        format,
        variant,
        locale: proposal.locale as ProposalLocale,
        project_name: projectName.trim() || undefined,
      });
      onExported(row);
      const next = [row, ...exports.filter((e) => e.id !== row.id)];
      syncExports(next);
      setPreviewTarget({ id: row.id, format: row.format });
    } catch (err) {
      setError(err instanceof Error ? err.message : t("exportFailed"));
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(exportId: string) {
    setDeletingExportId(exportId);
    setError(null);
    try {
      await deleteProposalExport(proposal.id, exportId);
      const next = exports.filter((row) => row.id !== exportId);
      syncExports(next);
      setSelectedExportIds((current) => {
        const nextSet = new Set(current);
        nextSet.delete(exportId);
        return nextSet;
      });
      if (previewTarget?.id === exportId) {
        setPreviewTarget(null);
      }
      setConfirmingDeleteId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : tExport("deleteError"));
    } finally {
      setDeletingExportId(null);
    }
  }

  async function handleSendEmail() {
    if (selectedExportIds.size === 0) {
      setError(tExport("emailSelectRequired"));
      return;
    }
    setSendingEmail(true);
    setError(null);
    setEmailSuccess(null);
    try {
      await sendProposalExportsEmail(proposal.id, {
        to_email: toEmail,
        export_ids: Array.from(selectedExportIds),
        message: emailMessage || undefined,
      });
      setEmailSuccess(tExport("emailSuccess"));
    } catch (err) {
      setError(err instanceof Error ? err.message : tExport("emailError"));
    } finally {
      setSendingEmail(false);
    }
  }

  const downloadHref = (exportId: string) =>
    `/api/proposals/${proposal.id}/exports/${exportId}/download`;

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900 print:hidden">
      <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
        {t("exportTitle")}
      </h2>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
        {t("exportHint")}
      </p>

      <div className="mt-3 flex flex-wrap gap-3">
        <label className="w-full text-sm md:max-w-md">
          <span className="mb-1 block text-slate-600 dark:text-slate-300">
            {t("exportProjectName")}
          </span>
          <input
            type="text"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            placeholder={t("exportProjectNamePlaceholder")}
            className="w-full rounded border border-slate-300 bg-white px-2 py-1.5 dark:border-slate-600 dark:bg-slate-950"
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-slate-600 dark:text-slate-300">{t("format")}</span>
          <select
            className="rounded border border-slate-300 bg-white px-2 py-1.5 dark:border-slate-600 dark:bg-slate-950"
            value={format}
            onChange={(e) => setFormat(e.target.value as typeof format)}
          >
            <option value="pdf">PDF</option>
            <option value="docx">DOCX</option>
            <option value="md">Markdown</option>
            <option value="xlsx">Excel</option>
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-slate-600 dark:text-slate-300">{t("variant")}</span>
          <select
            className="rounded border border-slate-300 bg-white px-2 py-1.5 dark:border-slate-600 dark:bg-slate-950"
            value={variant}
            onChange={(e) => setVariant(e.target.value as typeof variant)}
          >
            <option value="full">{t("variantFull")}</option>
            <option value="assessment">{t("partAssessment")}</option>
            <option value="proposal">{t("partProposal")}</option>
            <option value="poc" disabled={!proposal.include_poc}>
              {t("partPoc")}
            </option>
          </select>
        </label>
        <div className="flex items-end gap-2">
          <button
            type="button"
            disabled={busy || !proposal.proposal_body}
            className="proposal-btn-primary rounded px-4 py-2 text-sm disabled:opacity-50"
            onClick={() => void handleExport()}
          >
            {busy ? t("exporting") : tExport("exportButton")}
          </button>
        </div>
      </div>

      {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}
      {emailSuccess ? (
        <p className="mt-2 text-sm text-emerald-700 dark:text-emerald-300">{emailSuccess}</p>
      ) : null}

      <div className="mt-5">
        <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
          {tExport("downloadsTitle")}
        </h3>
        {exports.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">{tExport("empty")}</p>
        ) : (
          <ul className="mt-2 divide-y divide-slate-200 dark:divide-slate-700">
            {exports.map((row) => (
              <li
                key={row.id}
                className="flex flex-wrap items-center gap-2 py-2 text-sm"
              >
                <label className="inline-flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={selectedExportIds.has(row.id)}
                    onChange={() => toggleExportSelection(row.id)}
                  />
                  <span className="sr-only">{tExport("emailSelectLabel")}</span>
                </label>
                <span className="min-w-0 flex-1 text-slate-700 dark:text-slate-200">
                  v{row.revision} · {row.format.toUpperCase()} · {row.variant} ·{" "}
                  {formatLocalTimestamp(row.generated_at, locale)}
                </span>
                <button
                  type="button"
                  className="proposal-link text-sm hover:underline"
                  onClick={() => setPreviewTarget({ id: row.id, format: row.format })}
                >
                  {tExport("preview")}
                </button>
                <a
                  href={downloadHref(row.id)}
                  className="proposal-link text-sm hover:underline"
                >
                  {tExport("download")}
                </a>
                {confirmingDeleteId === row.id ? (
                  <span className="inline-flex items-center gap-1">
                    <button
                      type="button"
                      disabled={deletingExportId === row.id}
                      className="rounded bg-red-600 px-2 py-0.5 text-xs text-white disabled:opacity-50"
                      onClick={() => void handleDelete(row.id)}
                    >
                      {deletingExportId === row.id
                        ? tExport("deleting")
                        : tExport("deleteConfirmAction")}
                    </button>
                    <button
                      type="button"
                      className="text-xs text-slate-500"
                      onClick={() => setConfirmingDeleteId(null)}
                    >
                      {tExport("deleteCancel")}
                    </button>
                  </span>
                ) : (
                  <button
                    type="button"
                    className="text-sm text-red-600 hover:underline"
                    onClick={() => setConfirmingDeleteId(row.id)}
                  >
                    {tExport("delete")}
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="mt-5 rounded-lg border border-slate-200 p-3 dark:border-slate-700">
        <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
          {tExport("emailTitle")}
        </h3>
        <p className="mt-1 text-xs text-slate-500">{tExport("emailDescription")}</p>
        <label className="mt-3 block text-sm">
          <span className="mb-1 block text-slate-600 dark:text-slate-300">
            {tExport("emailToLabel")}
          </span>
          <input
            type="email"
            value={toEmail}
            onChange={(e) => setToEmail(e.target.value)}
            className="w-full rounded border border-slate-300 bg-white px-2 py-1.5 dark:border-slate-600 dark:bg-slate-950"
          />
        </label>
        <label className="mt-2 block text-sm">
          <span className="mb-1 block text-slate-600 dark:text-slate-300">
            {tExport("emailMessageLabel")}
          </span>
          <textarea
            value={emailMessage}
            onChange={(e) => setEmailMessage(e.target.value)}
            placeholder={tExport("emailMessagePlaceholder")}
            rows={2}
            className="w-full rounded border border-slate-300 bg-white px-2 py-1.5 dark:border-slate-600 dark:bg-slate-950"
          />
        </label>
        <button
          type="button"
          disabled={sendingEmail || !toEmail || selectedExportIds.size === 0}
          className="proposal-btn-primary mt-3 rounded px-4 py-2 text-sm disabled:opacity-50"
          onClick={() => void handleSendEmail()}
        >
          {sendingEmail ? tExport("emailSending") : tExport("emailSendButton")}
        </button>
      </div>

      {previewTarget ? (
        <ExportPreviewModal
          exportId={previewTarget.id}
          format={previewTarget.format}
          downloadPath={`/proposals/${proposal.id}/exports/${previewTarget.id}/download`}
          onClose={() => setPreviewTarget(null)}
        />
      ) : null}
    </section>
  );
}
