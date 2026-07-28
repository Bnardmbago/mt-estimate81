"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import ExportPreviewModal from "@/components/ExportPreviewModal";
import { apiJson } from "@/lib/api";
import { formatLocalTimestamp } from "@/lib/datetime";
import {
  createProposalExport,
  deleteProposalExport,
  fetchProposalExports,
  patchProposalCoverValues,
  sendProposalExportToCanva,
  sendProposalExportToGoogle,
  sendProposalExportsEmail,
} from "@/lib/proposal";
import {
  ensureCanvaConnected,
  ensureGoogleConnected,
  formatFamilyLabel,
  isDocxFormat,
  isPdfFormat,
  isXlsxFormat,
} from "@/lib/export-destinations";
import {
  fetchPresentationDefaults,
  fetchPresentationStyles,
  fetchPresentationTemplate,
  fetchPresentationTemplates,
  fetchPresentationThemes,
  type PresentationPresetSummary,
} from "@/lib/presentation";
import type {
  ProposalCoverField,
  ProposalDetail,
  ProposalExportRecord,
  ProposalLocale,
} from "@/lib/proposal-types";
import ProposalCoverFields from "@/components/proposal/ProposalCoverFields";
import ProposalExportLocaleSelector from "@/components/proposal/ProposalExportLocaleSelector";
import PresentationSelectors, {
  NO_COVER_PRESET,
  templateHasCover,
} from "@/components/proposal/PresentationSelectors";

type ProposalExportPanelProps = {
  proposal: ProposalDetail;
  onProposalUpdated?: (proposal: ProposalDetail) => void;
  onExported: (row: ProposalExportRecord) => void;
  onExportsChanged?: (rows: ProposalExportRecord[]) => void;
};

type PreviewTarget = { id: string; format: string };

export default function ProposalExportPanel({
  proposal,
  onProposalUpdated,
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
  const [sendingDestinationId, setSendingDestinationId] = useState<string | null>(null);
  const [selectedExportIds, setSelectedExportIds] = useState<Set<string>>(
    () => new Set(),
  );
  const [toEmail, setToEmail] = useState("");
  const [emailMessage, setEmailMessage] = useState("");
  const [sendingEmail, setSendingEmail] = useState(false);
  const [emailSuccess, setEmailSuccess] = useState<string | null>(null);
  const [themes, setThemes] = useState<PresentationPresetSummary[]>([]);
  const [styles, setStyles] = useState<PresentationPresetSummary[]>([]);
  const [templates, setTemplates] = useState<PresentationPresetSummary[]>([]);
  const [coverFields, setCoverFields] = useState<ProposalCoverField[]>([]);
  const [themeId, setThemeId] = useState(proposal.theme_id || "corporate-navy");
  const [styleId, setStyleId] = useState(proposal.style_id || "comfortable");
  const [templateId, setTemplateId] = useState(proposal.template_id || "classic-linear");
  const [exportLocale, setExportLocale] = useState<ProposalLocale>(
    () => (proposal.locale === "ja" ? "ja" : "en"),
  );
  const [coverPresetId, setCoverPresetId] = useState(NO_COVER_PRESET);
  const coverDefaultedRef = useRef(false);

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
    setThemeId(proposal.theme_id || "corporate-navy");
    setStyleId(proposal.style_id || "comfortable");
    setTemplateId(proposal.template_id || "classic-linear");
    setExportLocale(proposal.locale === "ja" ? "ja" : "en");
    coverDefaultedRef.current = false;
  }, [proposal.id, proposal.theme_id, proposal.style_id, proposal.template_id]);

  useEffect(() => {
    void (async () => {
      try {
        const [themeRows, styleRows, templateRows, defaults] = await Promise.all([
          fetchPresentationThemes(),
          fetchPresentationStyles(),
          fetchPresentationTemplates(),
          fetchPresentationDefaults().catch(() => null),
        ]);
        setThemes(themeRows);
        setStyles(styleRows);
        setTemplates(templateRows);
        if (defaults?.cover_template_id) {
          coverDefaultedRef.current = true;
          setCoverPresetId((prev) => prev || defaults.cover_template_id || NO_COVER_PRESET);
        }
      } catch {
        // optional
      }
    })();
  }, []);

  useEffect(() => {
    if (coverDefaultedRef.current || !templates.length || !templateId) return;
    coverDefaultedRef.current = true;
    const selected = templates.find((row) => row.id === templateId);
    if (selected && templateHasCover(selected)) {
      setCoverPresetId(templateId);
    }
  }, [templateId, templates]);

  useEffect(() => {
    if (!coverPresetId) {
      setCoverFields([]);
      return;
    }
    let cancelled = false;
    setCoverFields([]);
    void fetchPresentationTemplate(coverPresetId)
      .then((detail) => {
        if (!cancelled) {
          setCoverFields(proposalCoverFields(detail.config.cover_fields));
        }
      })
      .catch(() => {
        if (!cancelled) setCoverFields([]);
      });
    return () => {
      cancelled = true;
    };
  }, [coverPresetId]);

  // Local list only — do not call onExportsChanged here (that updates parent
  // proposal and previously caused an infinite /exports refetch loop).
  useEffect(() => {
    let cancelled = false;
    void fetchProposalExports(proposal.id)
      .then((rows) => {
        if (!cancelled) {
          setExports(rows);
        }
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [proposal.id]);

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

  async function saveCoverValues(values: Record<string, string>) {
    const updated = await patchProposalCoverValues(proposal.id, exportLocale, values);
    onProposalUpdated?.(updated);
  }

  async function handleExport() {
    if (proposal.source_stale) {
      const proceed = window.confirm(t("exportStaleConfirm"));
      if (!proceed) {
        return;
      }
    }
    const colliding = exports.some(
      (row) =>
        row.manually_edited_at &&
        row.format === format &&
        row.variant === variant,
    );
    if (colliding) {
      window.alert(tExport("regenerateEditedWarn"));
    }
    setBusy(true);
    setError(null);
    setEmailSuccess(null);
    try {
      const row = await createProposalExport(proposal.id, {
        format,
        variant,
        locale: exportLocale,
        project_name: projectName.trim() || undefined,
        theme_id: themeId,
        style_id: styleId,
        template_id: templateId,
        include_cover: Boolean(coverPresetId),
        cover_template_id: coverPresetId || undefined,
        cover_values: proposal.cover_values,
      });
      onExported(row);
      const next = [row, ...exports.filter((e) => e.id !== row.id)];
      syncExports(next);
      // Auto-open preview only for PDF; DOCX/XLSX/MD go straight to the list.
      if (isPdfFormat(row.format)) {
        setPreviewTarget({ id: row.id, format: row.format });
      }
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


  async function handleOpenGoogle(row: ProposalExportRecord) {
    setSendingDestinationId(row.id);
    setError(null);
    try {
      const connected = await ensureGoogleConnected();
      if (!connected) return;
      const result = await sendProposalExportToGoogle(proposal.id, row.id);
      if (result.external_url) {
        window.open(result.external_url, "_blank", "noopener,noreferrer");
      }
      const next = await fetchProposalExports(proposal.id);
      syncExports(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : tExport("sendToDestinationError"));
    } finally {
      setSendingDestinationId(null);
    }
  }

  async function handleOpenCanva(row: ProposalExportRecord) {
    setSendingDestinationId(row.id);
    setError(null);
    try {
      const connected = await ensureCanvaConnected();
      if (!connected) return;
      const result = await sendProposalExportToCanva(proposal.id, row.id);
      if (result.external_url) {
        window.open(result.external_url, "_blank", "noopener,noreferrer");
      }
      const next = await fetchProposalExports(proposal.id);
      syncExports(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : tExport("sendToDestinationError"));
    } finally {
      setSendingDestinationId(null);
    }
  }

  const downloadHref = (exportId: string) =>
    `/api/proposals/${proposal.id}/exports/${exportId}/download`;

  const variantEditHint =
    format === "md"
      ? t("editDestinationMd")
      : variant === "assessment"
        ? t("editDestinationAssessment")
        : variant === "proposal"
          ? t("editDestinationProposal")
          : variant === "poc"
            ? t("editDestinationPoc")
            : t("editDestinationFull");

  return (
    <section
      data-tour="proposal-export-panel"
      className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900 print:hidden"
    >
      <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
        {t("exportTitle")}
      </h2>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
        {t("exportHint")}
      </p>
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-300" role="note">
        {variantEditHint}
      </p>
      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
        {t("editDestinationOfficialCostNote")}
      </p>

      {themes.length > 0 ? (
        <div className="mt-3">
          <PresentationSelectors
            themes={themes}
            styles={styles}
            templates={templates}
            themeId={themeId}
            styleId={styleId}
            templateId={templateId}
            coverPresetId={coverPresetId}
            disabled={busy}
            compact
            showCoverPreset
            onThemeChange={setThemeId}
            onStyleChange={setStyleId}
            onTemplateChange={setTemplateId}
            onCoverPresetChange={setCoverPresetId}
          />
        </div>
      ) : null}

      {coverPresetId ? (
        <ProposalCoverFields
          fields={coverFields}
          values={proposal.cover_values || {}}
          locale={exportLocale}
          disabled={busy}
          onSave={saveCoverValues}
        />
      ) : null}

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <ProposalExportLocaleSelector
          value={exportLocale}
          disabled={busy}
          onChange={setExportLocale}
        />
      </div>

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
                <span
                  className="inline-flex w-14 shrink-0 justify-center rounded bg-slate-100 px-1.5 py-0.5 text-xs font-semibold tracking-wide text-slate-800 dark:bg-slate-800 dark:text-slate-100"
                  title={tExport("formatsLabel")}
                >
                  {formatFamilyLabel(row.format)}
                </span>
                <span className="min-w-0 flex-1 text-slate-700 dark:text-slate-200">
                  <span>
                    v{row.revision} · {row.variant} ·{" "}
                    {formatLocalTimestamp(row.generated_at, locale)}
                  </span>
                  <span className="mt-0.5 block text-xs text-slate-500 dark:text-slate-400">
                    {row.format === "md"
                      ? t("editDestinationMd")
                      : row.variant === "assessment"
                        ? t("editDestinationAssessment")
                        : row.variant === "proposal"
                          ? t("editDestinationProposal")
                          : row.variant === "poc"
                            ? t("editDestinationPoc")
                            : t("editDestinationFull")}
                  </span>
                  {row.manually_edited_at ? (
                    <span className="mt-1 inline-flex rounded bg-amber-100 px-1.5 py-0.5 text-xs font-medium text-amber-900 dark:bg-amber-900/40 dark:text-amber-100">
                      {tExport("externallyEditedBadge")}
                    </span>
                  ) : null}
                </span>
                <button
                  type="button"
                  className="header-btn text-xs"
                  onClick={() => setPreviewTarget({ id: row.id, format: row.format })}
                >
                  {tExport("preview")}
                </button>
                <a
                  href={downloadHref(row.id)}
                  className="header-btn text-xs"
                >
                  {tExport("download")}
                </a>
                {isDocxFormat(row.format) ? (
                  <button
                    type="button"
                    disabled={sendingDestinationId === row.id}
                    className="header-btn text-xs disabled:opacity-50"
                    onClick={() => void handleOpenGoogle(row)}
                  >
                    {sendingDestinationId === row.id
                      ? t("exporting")
                      : tExport("openInDocs")}
                  </button>
                ) : null}
                {isXlsxFormat(row.format) ? (
                  <button
                    type="button"
                    disabled={sendingDestinationId === row.id}
                    className="header-btn text-xs disabled:opacity-50"
                    onClick={() => void handleOpenGoogle(row)}
                  >
                    {sendingDestinationId === row.id
                      ? t("exporting")
                      : tExport("openInSheets")}
                  </button>
                ) : null}
                {isPdfFormat(row.format) ? (
                  <button
                    type="button"
                    disabled={sendingDestinationId === row.id}
                    className="header-btn text-xs disabled:opacity-50"
                    onClick={() => void handleOpenCanva(row)}
                  >
                    {sendingDestinationId === row.id
                      ? t("exporting")
                      : tExport("openInCanva")}
                  </button>
                ) : null}
                {row.external_url ? (
                  <a
                    href={row.external_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="header-btn text-xs"
                  >
                    {row.destination === "canva"
                      ? tExport("openInCanva")
                      : row.destination === "google_sheets"
                        ? tExport("openInSheets")
                        : tExport("openInDocs")}
                  </a>
                ) : null}
                {confirmingDeleteId === row.id ? (
                  <span className="inline-flex items-center gap-2">
                    <button
                      type="button"
                      disabled={deletingExportId === row.id}
                      className="header-btn text-xs text-red-700 disabled:opacity-50"
                      onClick={() => void handleDelete(row.id)}
                    >
                      {deletingExportId === row.id
                        ? tExport("deleting")
                        : tExport("deleteConfirmAction")}
                    </button>
                    <button
                      type="button"
                      className="header-btn text-xs"
                      onClick={() => setConfirmingDeleteId(null)}
                    >
                      {tExport("deleteCancel")}
                    </button>
                  </span>
                ) : (
                  <button
                    type="button"
                    className="header-btn text-xs text-red-700"
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

function proposalCoverFields(value: unknown): ProposalCoverField[] {
  if (!Array.isArray(value)) return [];
  return value.filter(
    (field): field is ProposalCoverField =>
      Boolean(
        field &&
          typeof field === "object" &&
          "key" in field &&
          typeof field.key === "string" &&
          field.key,
      ),
  );
}
