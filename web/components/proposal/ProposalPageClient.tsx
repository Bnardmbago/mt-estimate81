"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { apiJson } from "@/lib/api";
import {
  deleteProposal,
  fetchProposal,
  fetchProposalByEstimate,
  fetchProposalStatus,
  fetchProposals,
  finalizeProposal,
  generateProposal,
  patchProposalSections,
  refreshProposal,
  regenerateProposal,
} from "@/lib/proposal";
import { proposalDocLabels } from "@/lib/proposal-doc-labels";
import type {
  EstimatePickerItem,
  ProposalDetail,
  ProposalLocale,
  ProposalProjectBrief,
  ProposalSummary,
} from "@/lib/proposal-types";
import AiGenerationProgress, {
  type AiProgressStep,
  type AiProgressStepStatus,
} from "@/components/AiGenerationProgress";
import ProposalBriefEditor from "@/components/proposal/ProposalBriefEditor";
import ProposalDataTable from "@/components/proposal/ProposalDataTable";
import ProposalExportPanel from "@/components/proposal/ProposalExportPanel";
import ProposalGantt from "@/components/proposal/ProposalGantt";
import ProposalMermaid from "@/components/proposal/ProposalMermaid";
import ProposalSectionEditor from "@/components/proposal/ProposalSectionEditor";
import ProposalStaleBanner from "@/components/proposal/ProposalStaleBanner";
import ProposalToc, { type ProposalTab } from "@/components/proposal/ProposalToc";

const ELIGIBLE = new Set(["calculated", "exported", "completed"]);

export default function ProposalPageClient() {
  const t = useTranslations("proposal");
  const locale = useLocale() as ProposalLocale;
  const searchParams = useSearchParams();
  const presetEstimate = searchParams.get("estimate");

  const [estimates, setEstimates] = useState<EstimatePickerItem[]>([]);
  const [recent, setRecent] = useState<ProposalSummary[]>([]);
  const [estimateId, setEstimateId] = useState(presetEstimate || "");
  const [docLocale, setDocLocale] = useState<ProposalLocale>(locale === "ja" ? "ja" : "en");
  const [includePoc, setIncludePoc] = useState(false);
  const [proposal, setProposal] = useState<ProposalDetail | null>(null);
  const [activeTab, setActiveTab] = useState<ProposalTab>("assessment");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [staleDismissed, setStaleDismissed] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [confirmingDeleteId, setConfirmingDeleteId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const loadLists = useCallback(async () => {
    const [estimateRows, proposalRows] = await Promise.all([
      apiJson<EstimatePickerItem[]>("/estimates"),
      fetchProposals().catch(() => [] as ProposalSummary[]),
    ]);
    setEstimates(estimateRows.filter((row) => ELIGIBLE.has(row.status)));
    setRecent(proposalRows);
  }, []);

  function formatUpdated(value: string): string {
    if (!value) {
      return "—";
    }
    const normalized = value.includes("T") ? value : value.replace(" ", "T");
    const parsed = new Date(normalized);
    if (Number.isNaN(parsed.getTime())) {
      return value;
    }
    try {
      return new Intl.DateTimeFormat(locale === "ja" ? "ja-JP" : "en-US", {
        dateStyle: "medium",
      }).format(parsed);
    } catch {
      return value;
    }
  }

  async function handleDeleteProposal(row: ProposalSummary) {
    setDeletingId(row.id);
    setError(null);
    try {
      await deleteProposal(row.id);
      if (proposal?.id === row.id) {
        setProposal(null);
      }
      setConfirmingDeleteId(null);
      await loadLists();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("deleteFailed"));
    } finally {
      setDeletingId(null);
    }
  }

  useEffect(() => {
    void loadLists().catch((err) =>
      setError(err instanceof Error ? err.message : t("loadFailed")),
    );
  }, [loadLists, t]);

  useEffect(() => {
    if (!presetEstimate) {
      return;
    }
    void (async () => {
      try {
        const existing = await fetchProposalByEstimate(presetEstimate, docLocale);
        if (existing) {
          setProposal(existing);
          setEstimateId(presetEstimate);
          setIncludePoc(existing.include_poc);
        }
      } catch {
        // no existing proposal is fine
      }
    })();
  }, [presetEstimate, docLocale]);

  useEffect(() => {
    if (!proposal || proposal.status !== "generating") {
      return;
    }
    const timer = window.setInterval(() => {
      void fetchProposalStatus(proposal.id)
        .then(async (status) => {
          if (status.status !== "generating") {
            const fresh = await fetchProposal(proposal.id);
            setProposal(fresh);
          } else {
            setProposal((prev) =>
              prev
                ? {
                    ...prev,
                    status: status.status,
                    generation_meta: status.generation_meta,
                    assessment: status.assessment_ready ? prev.assessment : prev.assessment,
                  }
                : prev,
            );
            if (status.assessment_ready || status.proposal_ready) {
              const fresh = await fetchProposal(proposal.id);
              setProposal(fresh);
            }
          }
        })
        .catch(() => undefined);
    }, 2000);
    return () => window.clearInterval(timer);
  }, [proposal]);

  const partStatus = useMemo(() => {
    const parts = proposal?.generation_meta?.parts || {};
    return {
      assessment: parts.assessment?.status || (proposal?.assessment ? "done" : "pending"),
      proposal: parts.proposal?.status || (proposal?.proposal_body ? "done" : "pending"),
      poc: parts.poc?.status || (proposal?.poc ? "done" : includePoc ? "pending" : "skipped"),
    };
  }, [proposal, includePoc]);

  const isGenerating =
    busy || proposal?.status === "generating";

  const generationSteps = useMemo((): AiProgressStep[] => {
    const normalize = (value: string): AiProgressStepStatus => {
      if (value === "running" || value === "done" || value === "error" || value === "skipped") {
        return value;
      }
      return "pending";
    };
    const steps: AiProgressStep[] = [
      {
        id: "assessment",
        label: t("partAssessment"),
        status: normalize(partStatus.assessment),
      },
      {
        id: "proposal",
        label: t("partProposal"),
        status: normalize(partStatus.proposal),
      },
    ];
    if (includePoc || partStatus.poc !== "skipped") {
      steps.push({
        id: "poc",
        label: t("partPoc"),
        status: normalize(partStatus.poc),
      });
    }
    return steps;
  }, [includePoc, partStatus, t]);

  function statusLabel(status: string): string {
    switch (status) {
      case "running":
        return t("statusRunning");
      case "done":
        return t("statusDone");
      case "error":
        return t("statusError");
      case "skipped":
        return t("statusSkipped");
      default:
        return t("statusPending");
    }
  }

  async function handleGenerate() {
    if (!estimateId) {
      setError(t("selectEstimate"));
      return;
    }
    setBusy(true);
    setError(null);
    setStaleDismissed(false);
    try {
      const result = await generateProposal({
        estimate_id: estimateId,
        locale: docLocale,
        include_poc: includePoc,
      });
      setProposal(result);
      setActiveTab("assessment");
      await loadLists();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("generateFailed"));
    } finally {
      setBusy(false);
    }
  }

  function navigate(part: ProposalTab, sectionId?: string) {
    setActiveTab(part);
    if (sectionId) {
      window.setTimeout(() => {
        document.getElementById(sectionId)?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 50);
    } else {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  async function saveSection(
    part: "assessment" | "proposal" | "poc",
    sectionId: string,
    next: { body?: string; bullets?: string[] },
  ) {
    if (!proposal) {
      return;
    }
    const updated = await patchProposalSections(proposal.id, [
      { part, section_id: sectionId, ...next },
    ]);
    setProposal(updated);
  }

  async function saveBrief(next: ProposalProjectBrief) {
    if (!proposal) {
      return;
    }
    const updated = await patchProposalSections(proposal.id, [
      {
        part: "poc",
        section_id: "project_brief",
        extra: {
          project_name: next.project_name || "",
          project_description: next.project_description || "",
          business_problem: next.business_problem || "",
          target_users: next.target_users || "",
          technology_stack: next.technology_stack || "",
          constraints: next.constraints || "",
        },
      },
    ]);
    setProposal(updated);
  }

  const activeBlob =
    activeTab === "assessment"
      ? proposal?.assessment
      : activeTab === "proposal"
        ? proposal?.proposal_body
        : proposal?.poc;

  const costs = proposal?.source_snapshot?.costs;
  const docLabels = proposal ? proposalDocLabels(proposal.locale) : proposalDocLabels(docLocale);

  return (
    <div className="proposal-theme proposal-print space-y-6">
      <header className="print:hidden">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50">
          {t("pageTitle")}
        </h1>
        <p className="mt-1 max-w-3xl text-sm text-slate-600 dark:text-slate-300">
          {t("pageDescription")}
        </p>
      </header>

      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900 print:hidden">
        <div className="grid gap-3 md:grid-cols-4">
          <label className="text-sm md:col-span-2">
            <span className="mb-1 block text-slate-600 dark:text-slate-300">
              {t("selectEstimate")}
            </span>
            <select
              className="w-full rounded border border-slate-300 bg-white px-3 py-2 dark:border-slate-600 dark:bg-slate-950"
              value={estimateId}
              onChange={(e) => setEstimateId(e.target.value)}
            >
              <option value="">{t("selectEstimatePlaceholder")}</option>
              {estimates.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.project_name} — {row.client_name} ({row.status})
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-slate-600 dark:text-slate-300">
              {t("documentLanguage")}
            </span>
            <select
              className="w-full rounded border border-slate-300 bg-white px-3 py-2 dark:border-slate-600 dark:bg-slate-950"
              value={docLocale}
              onChange={(e) => setDocLocale(e.target.value as ProposalLocale)}
            >
              <option value="en">English</option>
              <option value="ja">日本語</option>
            </select>
          </label>
          <label className="flex items-end gap-2 pb-2 text-sm">
            <input
              type="checkbox"
              checked={includePoc}
              onChange={(e) => setIncludePoc(e.target.checked)}
            />
            <span>{t("includePoc")}</span>
          </label>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            disabled={busy}
            className="proposal-btn-primary rounded px-4 py-2 text-sm font-medium disabled:opacity-50"
            onClick={() => void handleGenerate()}
          >
            {busy ? t("generating") : proposal ? t("regenerateAll") : t("generate")}
          </button>
          {proposal ? (
            <>
              <button
                type="button"
                className="rounded border border-slate-300 px-3 py-2 text-sm dark:border-slate-600"
                onClick={() =>
                  void regenerateProposal(proposal.id, "assessment").then(setProposal)
                }
              >
                {t("regenAssessment")}
              </button>
              <button
                type="button"
                className="rounded border border-slate-300 px-3 py-2 text-sm dark:border-slate-600"
                onClick={() =>
                  void regenerateProposal(proposal.id, "proposal").then(setProposal)
                }
              >
                {t("regenProposal")}
              </button>
              {includePoc ? (
                <button
                  type="button"
                  className="rounded border border-slate-300 px-3 py-2 text-sm dark:border-slate-600"
                  onClick={() =>
                    void regenerateProposal(proposal.id, "poc").then(setProposal)
                  }
                >
                  {t("regenPoc")}
                </button>
              ) : null}
              <button
                type="button"
                className="rounded border border-slate-300 px-3 py-2 text-sm dark:border-slate-600"
                onClick={() =>
                  void finalizeProposal(proposal.id).then(setProposal)
                }
              >
                {t("finalize")}
              </button>
            </>
          ) : null}
        </div>
        {isGenerating ? (
          <div className="mt-4">
            <AiGenerationProgress
              active
              title={t("generatingTitle")}
              message={t("generatingHint")}
              steps={generationSteps}
            />
          </div>
        ) : proposal ? (
          <p className="mt-3 text-xs text-slate-500">
            {t("progress", {
              assessment: statusLabel(partStatus.assessment),
              proposal: statusLabel(partStatus.proposal),
              poc: statusLabel(partStatus.poc),
            })}
          </p>
        ) : null}
        {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}
      </section>

      {recent.length > 0 ? (
        <section className="print:hidden">
          <h2 className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-200">
            {t("recent")}
          </h2>
          <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-800/60">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                    {t("columnProject")}
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                    {t("columnClient")}
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                    {t("columnStatus")}
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                    {t("columnUpdated")}
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wide text-gray-500">
                    {t("columnActions")}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {recent.slice(0, 8).map((row) => {
                  const isConfirming = confirmingDeleteId === row.id;
                  const isDeleting = deletingId === row.id;
                  return (
                    <tr
                      key={row.id}
                      className="hover:bg-gray-50 dark:hover:bg-gray-800/40"
                    >
                      <td className="px-4 py-3 text-sm">
                        <button
                          type="button"
                          className="proposal-link text-left font-medium hover:underline"
                          onClick={() =>
                            void fetchProposal(row.id).then((detail) => {
                              setProposal(detail);
                              setEstimateId(detail.estimate_id);
                              setIncludePoc(detail.include_poc);
                              setDocLocale(detail.locale as ProposalLocale);
                            })
                          }
                        >
                          {row.project_name || "—"}
                        </button>
                        <div className="mt-0.5 text-xs text-gray-500">
                          {row.locale.toUpperCase()}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300">
                        {row.client_name || "—"}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300">
                        {row.status}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300">
                        {formatUpdated(row.updated_at)}
                      </td>
                      <td className="px-4 py-3 text-right text-sm">
                        {isConfirming ? (
                          <div className="inline-flex flex-col items-end gap-2 sm:flex-row sm:items-center">
                            <span className="max-w-xs text-left text-xs text-gray-600 dark:text-gray-300">
                              {t("deleteConfirm")}
                            </span>
                            <div className="flex gap-2">
                              <button
                                type="button"
                                onClick={() => setConfirmingDeleteId(null)}
                                disabled={isDeleting}
                                className="rounded border border-gray-300 px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
                              >
                                {t("deleteCancel")}
                              </button>
                              <button
                                type="button"
                                onClick={() => void handleDeleteProposal(row)}
                                disabled={isDeleting}
                                className="rounded bg-red-600 px-2 py-1 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50"
                              >
                                {isDeleting ? t("deleting") : t("deleteConfirmAction")}
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div className="inline-flex gap-2">
                            <button
                              type="button"
                              className="rounded border border-gray-300 px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
                              onClick={() =>
                                void fetchProposal(row.id).then((detail) => {
                                  setProposal(detail);
                                  setEstimateId(detail.estimate_id);
                                  setIncludePoc(detail.include_poc);
                                  setDocLocale(detail.locale as ProposalLocale);
                                })
                              }
                            >
                              {t("open")}
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                setError(null);
                                setConfirmingDeleteId(row.id);
                              }}
                              className="rounded border border-red-200 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-50 dark:border-red-800 dark:text-red-300 dark:hover:bg-red-950/40"
                            >
                              {t("delete")}
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {proposal ? (
        <>
          {proposal.source_stale && !staleDismissed ? (
            <ProposalStaleBanner
              refreshing={refreshing}
              onDismiss={() => setStaleDismissed(true)}
              onRefresh={() => {
                setRefreshing(true);
                void refreshProposal(proposal.id)
                  .then((detail) => {
                    setProposal(detail);
                    setStaleDismissed(false);
                  })
                  .finally(() => setRefreshing(false));
              }}
            />
          ) : null}

          <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
            <div>
              <h2 className="proposal-doc-heading text-xl font-semibold">
                {proposal.source_snapshot.project_name}
              </h2>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                {proposal.source_snapshot.client_name} · {proposal.status}
              </p>
            </div>
            <div
              role="tablist"
              aria-label={docLabels.parts}
              className="flex rounded-lg border border-slate-200 p-1 dark:border-slate-700"
            >
              {(
                [
                  ["assessment", docLabels.partAssessment],
                  ["proposal", docLabels.partProposal],
                  ...(proposal.include_poc
                    ? ([["poc", docLabels.partPoc]] as const)
                    : []),
                ] as Array<[ProposalTab, string]>
              ).map(([key, label]) => (
                <button
                  key={key}
                  type="button"
                  role="tab"
                  aria-selected={activeTab === key}
                  className={`rounded px-3 py-1.5 text-sm ${
                    activeTab === key
                      ? "proposal-tab-active"
                      : "text-slate-700 dark:text-slate-200"
                  }`}
                  onClick={() => setActiveTab(key)}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {costs ? (
            <div className="proposal-cost-strip grid gap-3 rounded-lg border p-4 text-sm sm:grid-cols-3 dark:border-slate-700">
              <div>
                <div className="text-slate-500">{docLabels.oneTimeCost}</div>
                <div className="font-semibold">
                  {costs.one_time_project_cost_jpy?.toLocaleString?.() ?? costs.one_time_project_cost_jpy} JPY
                </div>
              </div>
              <div>
                <div className="text-slate-500">{docLabels.monthlyCost}</div>
                <div className="font-semibold">
                  {costs.monthly_recurring_cost_jpy?.toLocaleString?.() ?? costs.monthly_recurring_cost_jpy} JPY
                </div>
              </div>
              <div>
                <div className="text-slate-500">{docLabels.firstYearTotal}</div>
                <div className="font-semibold">
                  {costs.first_year_total_jpy?.toLocaleString?.() ?? costs.first_year_total_jpy} JPY
                </div>
              </div>
            </div>
          ) : null}

          <div className="grid gap-6 lg:grid-cols-[16rem_1fr]">
            <ProposalToc
              proposal={proposal}
              activeTab={activeTab}
              onNavigate={navigate}
            />
            <article className="rounded-lg border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
              <h2
                id={activeTab}
                className="proposal-doc-heading mb-6 text-2xl font-semibold"
              >
                {activeTab === "assessment"
                  ? docLabels.partAssessment
                  : activeTab === "proposal"
                    ? docLabels.partProposal
                    : docLabels.partPoc}
              </h2>

              {activeTab === "poc" && proposal.poc?.project_brief ? (
                <ProposalBriefEditor
                  brief={proposal.poc.project_brief}
                  labels={docLabels}
                  onSave={saveBrief}
                />
              ) : null}

              {(activeBlob?.sections || []).map((section) => (
                <ProposalSectionEditor
                  key={section.id}
                  part={activeTab}
                  docLocale={proposal.locale}
                  section={section}
                  onSave={(next) => saveSection(activeTab, section.id, next)}
                />
              ))}

              {activeTab === "proposal" ? (
                <>
                  <ProposalGantt proposal={proposal} />
                  {proposal.diagrams.map((diagram) => (
                    <ProposalMermaid
                      key={diagram.id}
                      id={diagram.id}
                      title={diagram.title}
                      source={diagram.source}
                    />
                  ))}
                </>
              ) : null}

              {activeTab === "poc" ? (
                <>
                  {(proposal.poc?.tables || []).length ? (
                    <div className="mt-4">
                      <h3 className="proposal-doc-heading text-base font-semibold">
                        {docLabels.pocTables}
                      </h3>
                      {(proposal.poc?.tables || []).map((table) => (
                        <ProposalDataTable key={table.id} table={table} />
                      ))}
                    </div>
                  ) : null}
                  {(proposal.poc?.diagrams || []).map((diagram) => (
                    <ProposalMermaid
                      key={diagram.id}
                      id={diagram.id}
                      title={diagram.title}
                      source={diagram.source}
                    />
                  ))}
                  {(proposal.poc?.milestones || []).length ? (
                    <div className="mt-4">
                      <h3 className="proposal-doc-heading text-base font-semibold">
                        {docLabels.pocMilestones}
                      </h3>
                      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700 dark:text-slate-200">
                        {(proposal.poc?.milestones || []).map((m) => (
                          <li key={m.id}>
                            {m.name}
                            {m.date ? ` — ${m.date}` : ""}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </>
              ) : null}

              {activeTab === "poc" && proposal.poc?.official ? (
                <div className="proposal-box mt-4 rounded-lg border p-4 text-sm dark:border-slate-700">
                  <h3 className="font-semibold">{docLabels.officialPocCost}</h3>
                  <ul className="mt-2 space-y-1">
                    <li>
                      {docLabels.effortHours}: {proposal.poc.official.total_effort_hours}
                    </li>
                    <li>
                      {docLabels.effortDays}: {proposal.poc.official.total_effort_days}
                    </li>
                    <li>
                      {docLabels.workingDays}:{" "}
                      {proposal.poc.official.estimated_timeline_working_days}
                    </li>
                    <li>
                      {docLabels.oneTimeCost}:{" "}
                      {proposal.poc.official.estimated_one_time_cost_jpy?.toLocaleString()}{" "}
                      JPY
                    </li>
                  </ul>
                  {proposal.poc.suggested_validation_window ? (
                    <p className="mt-2 text-slate-600 dark:text-slate-300">
                      {docLabels.suggestedWindow}: {proposal.poc.suggested_validation_window}
                    </p>
                  ) : null}
                </div>
              ) : null}
            </article>
          </div>

          <ProposalExportPanel
            proposal={proposal}
            onExported={(row) =>
              setProposal((prev) =>
                prev
                  ? { ...prev, exports: [row, ...(prev.exports || [])] }
                  : prev,
              )
            }
            onExportsChanged={(rows) =>
              setProposal((prev) => (prev ? { ...prev, exports: rows } : prev))
            }
          />
        </>
      ) : null}

      <style jsx global>{`
        @media print {
          .print\\:hidden {
            display: none !important;
          }
          .proposal-print article {
            border: none !important;
            box-shadow: none !important;
          }
        }
      `}</style>
    </div>
  );
}
