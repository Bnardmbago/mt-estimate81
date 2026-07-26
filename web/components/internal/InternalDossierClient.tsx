"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import CalculationBreakdown, {
  type CalculationResult,
} from "@/components/CalculationBreakdown";
import InternalExportPanel from "@/components/internal/InternalExportPanel";
import { useDisplayLabels } from "@/lib/displayI18n";
import {
  fetchInternalDossier,
  type InternalDossier,
} from "@/lib/internal-dossier";
import type { ProposalPartBlob, ProposalSection } from "@/lib/proposal-types";

type DossierTab = "estimate" | "rateCard" | "proposal";

type RateCardRoleView = {
  name: string;
  hourly_rate?: number | null;
  daily_rate?: number | null;
};

type RateCardLineItemView = {
  name: string;
  amount?: number | null;
};

type RateCardSettingsView = {
  roles?: RateCardRoleView[];
  setup_cost_items?: RateCardLineItemView[];
  monthly_rc_items?: RateCardLineItemView[];
  currency?: string;
};

type CostDriverView = { name?: string; impact_jpy?: number } | string;

type ExtractedDisclosureView = {
  cost_drivers?: CostDriverView[];
  risks?: string[];
  gaps?: string[];
  confidence_notes?: string;
  confidence_score?: number;
  confidence_factors?: string[];
  missing_inputs?: string[];
  recommendations?: string[];
  estimation_warnings?: string[];
  assumption_risks?: string[];
  estimate_exclusions?: string[];
};

type QuestionnaireFieldView = { label: string; value: string };
type QuestionnaireSectionView = {
  id?: string;
  title: string;
  fields: QuestionnaireFieldView[];
};

type ReportView = {
  calculation?: CalculationResult;
  extracted?: ExtractedDisclosureView;
  questionnaire_sections?: QuestionnaireSectionView[];
};

type InternalDossierClientProps = {
  estimateId: string;
  locale: string;
};

function tableWrapperClass() {
  return "overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700";
}

function ProposalPartSection({
  title,
  blob,
  noneLabel,
  projectBriefLabel,
  pocRecommendedLabel,
}: {
  title: string;
  blob: ProposalPartBlob | null;
  noneLabel: string;
  projectBriefLabel: string;
  pocRecommendedLabel: string;
}) {
  const sections = blob?.sections ?? [];
  const tables = blob?.tables ?? [];
  const milestones = blob?.milestones ?? [];
  const hasContent =
    Boolean(blob) &&
    (sections.length > 0 ||
      Boolean(blob?.project_brief) ||
      tables.length > 0 ||
      milestones.length > 0);

  return (
    <section className="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
      <h3 className="mb-2 text-base font-semibold">{title}</h3>
      {!hasContent ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">{noneLabel}</p>
      ) : (
        <div className="space-y-4">
          {blob?.poc_recommended ? (
            <span className="inline-block rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">
              {pocRecommendedLabel}
            </span>
          ) : null}

          {blob?.project_brief ? (
            <div>
              <h4 className="mb-1 text-sm font-medium">{projectBriefLabel}</h4>
              <dl className="grid gap-2 text-sm sm:grid-cols-2">
                {Object.entries(blob.project_brief)
                  .filter(([, value]) => Boolean(value))
                  .map(([key, value]) => (
                    <div key={key}>
                      <dt className="capitalize text-gray-500 dark:text-gray-400">
                        {key.replace(/_/g, " ")}
                      </dt>
                      <dd className="whitespace-pre-wrap">{value}</dd>
                    </div>
                  ))}
              </dl>
            </div>
          ) : null}

          {sections.map((section: ProposalSection) => (
            <div
              key={section.id}
              className="border-t border-gray-100 pt-3 first:border-t-0 first:pt-0 dark:border-gray-800"
            >
              <h4 className="text-sm font-semibold">
                {section.title}
                {section.rating ? (
                  <span className="ml-2 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-normal text-gray-600 dark:bg-gray-800 dark:text-gray-300">
                    {section.rating}
                  </span>
                ) : null}
              </h4>
              {section.body ? (
                <p className="mt-1 whitespace-pre-wrap text-sm text-gray-700 dark:text-gray-200">
                  {section.body}
                </p>
              ) : null}
              {section.bullets?.length ? (
                <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-gray-700 dark:text-gray-200">
                  {section.bullets.map((bullet, idx) => (
                    <li key={idx}>{bullet}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          ))}

          {tables.map((table) => (
            <div key={table.id}>
              <h4 className="mb-1 text-sm font-medium">{table.title}</h4>
              <div className={tableWrapperClass()}>
                <table className="min-w-full divide-y divide-gray-200 text-sm dark:divide-gray-700">
                  {table.headers?.length ? (
                    <thead className="bg-gray-50 dark:bg-gray-800">
                      <tr>
                        {table.headers.map((header, idx) => (
                          <th
                            key={idx}
                            className="px-3 py-2 text-left font-medium text-gray-700 dark:text-gray-200"
                          >
                            {header}
                          </th>
                        ))}
                      </tr>
                    </thead>
                  ) : null}
                  <tbody className="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-900">
                    {(table.rows ?? []).map((row, rowIdx) => (
                      <tr key={rowIdx}>
                        {row.map((cell, cellIdx) => (
                          <td key={cellIdx} className="px-3 py-2">
                            {cell}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}

          {milestones.length > 0 ? (
            <ul className="list-disc space-y-1 pl-5 text-sm text-gray-700 dark:text-gray-200">
              {milestones.map((milestone) => (
                <li key={milestone.id}>
                  {milestone.name}
                  {milestone.date ? ` — ${milestone.date}` : ""}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      )}
    </section>
  );
}

const DISCLOSURE_LIST_FIELDS: {
  key: keyof ExtractedDisclosureView;
  labelKey: string;
}[] = [
  { key: "risks", labelKey: "disclosureRisks" },
  { key: "gaps", labelKey: "disclosureGaps" },
  { key: "confidence_factors", labelKey: "disclosureConfidenceFactors" },
  { key: "missing_inputs", labelKey: "disclosureMissingInputs" },
  { key: "recommendations", labelKey: "disclosureRecommendations" },
  { key: "estimation_warnings", labelKey: "disclosureEstimationWarnings" },
  { key: "assumption_risks", labelKey: "disclosureAssumptionRisks" },
  { key: "estimate_exclusions", labelKey: "disclosureEstimateExclusions" },
];

function DisclosureSection({
  extracted,
  questionnaireSections,
  t,
}: {
  extracted: ExtractedDisclosureView | undefined;
  questionnaireSections: QuestionnaireSectionView[] | undefined;
  t: ReturnType<typeof useTranslations>;
}) {
  const costDrivers = extracted?.cost_drivers ?? [];
  const sections = questionnaireSections ?? [];
  const hasContent =
    costDrivers.length > 0 ||
    DISCLOSURE_LIST_FIELDS.some(
      ({ key }) => ((extracted?.[key] as string[] | undefined) ?? []).length > 0,
    ) ||
    Boolean(extracted?.confidence_notes) ||
    extracted?.confidence_score != null ||
    sections.length > 0;

  if (!hasContent) {
    return null;
  }

  return (
    <section className="space-y-4 rounded-lg border border-gray-200 p-4 dark:border-gray-700">
      <h3 className="text-base font-semibold">{t("disclosureTitle")}</h3>

      {costDrivers.length > 0 ? (
        <div>
          <h4 className="mb-1 text-sm font-medium">{t("disclosureCostDrivers")}</h4>
          <ul className="list-disc space-y-1 pl-5 text-sm text-gray-700 dark:text-gray-200">
            {costDrivers.map((driver, idx) => (
              <li key={idx}>
                {typeof driver === "string"
                  ? driver
                  : [driver.name, driver.impact_jpy != null ? `¥${driver.impact_jpy.toLocaleString()}` : null]
                      .filter(Boolean)
                      .join(" — ")}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {DISCLOSURE_LIST_FIELDS.map(({ key, labelKey }) => {
        const items = (extracted?.[key] as string[] | undefined) ?? [];
        if (items.length === 0) {
          return null;
        }
        return (
          <div key={key}>
            <h4 className="mb-1 text-sm font-medium">{t(labelKey)}</h4>
            <ul className="list-disc space-y-1 pl-5 text-sm text-gray-700 dark:text-gray-200">
              {items.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>
        );
      })}

      {extracted?.confidence_notes || extracted?.confidence_score != null ? (
        <div>
          <h4 className="mb-1 text-sm font-medium">{t("disclosureConfidence")}</h4>
          <p className="text-sm text-gray-700 dark:text-gray-200">
            {extracted?.confidence_score != null
              ? t("disclosureConfidenceScore", { score: extracted.confidence_score })
              : ""}
            {extracted?.confidence_notes ? ` ${extracted.confidence_notes}` : ""}
          </p>
        </div>
      ) : null}

      {sections.length > 0 ? (
        <div>
          <h4 className="mb-1 text-sm font-medium">{t("disclosureQuestionnaire")}</h4>
          <div className="space-y-2">
            {sections.map((section, sIdx) => (
              <div key={section.id ?? sIdx}>
                <p className="text-sm font-medium">{section.title}</p>
                <dl className="grid gap-1 text-sm sm:grid-cols-2">
                  {section.fields.map((field, fIdx) => (
                    <div key={fIdx}>
                      <dt className="text-gray-500 dark:text-gray-400">{field.label}</dt>
                      <dd>{field.value}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}

export default function InternalDossierClient({
  estimateId,
  locale,
}: InternalDossierClientProps) {
  const t = useTranslations("internalDossier");
  const tRateCards = useTranslations("rateCards");
  const tProposal = useTranslations("proposal");
  const { formatMoney, moneySymbol } = useDisplayLabels();

  const [dossier, setDossier] = useState<InternalDossier | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<DossierTab>("estimate");
  const [proposalIndex, setProposalIndex] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchInternalDossier(estimateId)
      .then((data) => {
        if (!cancelled) {
          setDossier(data);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : t("loadError"));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [estimateId, t]);

  const report = (dossier?.report ?? {}) as ReportView;
  const rateCardSettings = (dossier?.rate_card?.settings ?? {}) as RateCardSettingsView;
  const currency = rateCardSettings.currency ?? "JPY";
  const symbol = moneySymbol(currency);
  const proposals = dossier?.proposals ?? [];
  const activeProposal =
    proposals[Math.min(proposalIndex, Math.max(proposals.length - 1, 0))] ?? null;

  const tabs: { key: DossierTab; label: string }[] = [
    { key: "estimate", label: t("tabEstimate") },
    { key: "rateCard", label: t("tabRateCard") },
    { key: "proposal", label: t("tabProposal") },
  ];

  function tabButtonClass(isActive: boolean) {
    return isActive ? "header-btn header-btn-active" : "header-btn";
  }

  function formatAmount(value: number | null | undefined) {
    return formatMoney(value ?? 0, currency);
  }

  const roles = rateCardSettings.roles ?? [];
  const setupCostItems = rateCardSettings.setup_cost_items ?? [];
  const monthlyRcItems = rateCardSettings.monthly_rc_items ?? [];

  return (
    <div className="space-y-4">
      <div>
        <Link
          href={`/${locale}/estimates/${estimateId}`}
          className="mb-2 inline-block text-sm text-gray-500 hover:text-blue-600 dark:text-gray-400 dark:hover:text-blue-400"
        >
          ← {t("backToEstimate")}
        </Link>
        <h1 className="text-2xl font-semibold">{t("title")}</h1>
      </div>

      <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
        {t("banner")}
      </div>

      {loading ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">{t("loading")}</p>
      ) : error ? (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : dossier ? (
        <div className="space-y-4">
          <div className="rounded-lg border border-gray-200 bg-white p-4 text-sm text-gray-700 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200">
            <p className="font-medium">{dossier.project_name}</p>
            <p className="text-gray-500 dark:text-gray-400">{dossier.client_name}</p>
            <dl className="mt-2 flex flex-wrap gap-x-6 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
              <div className="flex gap-1">
                <dt>{t("statusLabel")}:</dt>
                <dd className="font-medium text-gray-700 dark:text-gray-200">{dossier.status}</dd>
              </div>
              <div className="flex gap-1">
                <dt>{t("localeLabel")}:</dt>
                <dd className="font-medium text-gray-700 dark:text-gray-200">
                  {dossier.locale.toUpperCase()}
                </dd>
              </div>
            </dl>
          </div>

          {dossier.warnings.length > 0 || dossier.rate_card_stale ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
              <p className="font-medium">{t("warningsTitle")}</p>
              <ul className="mt-1 list-disc space-y-1 pl-5">
                {dossier.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
                {dossier.rate_card_stale ? <li>{t("rateCardStale")}</li> : null}
              </ul>
            </div>
          ) : null}

          <nav className="flex flex-wrap gap-2" aria-label={t("title")}>
            {tabs.map((tabItem) => (
              <button
                key={tabItem.key}
                type="button"
                onClick={() => setTab(tabItem.key)}
                aria-current={tab === tabItem.key ? "page" : undefined}
                className={tabButtonClass(tab === tabItem.key)}
              >
                {tabItem.label}
              </button>
            ))}
          </nav>

          {tab === "estimate" ? (
            <div className="space-y-4">
              {dossier.has_calculation && report.calculation ? (
                <CalculationBreakdown result={report.calculation} />
              ) : (
                <p className="text-sm text-gray-500 dark:text-gray-400">{t("noneLabel")}</p>
              )}
              <DisclosureSection
                extracted={report.extracted}
                questionnaireSections={report.questionnaire_sections}
                t={t}
              />
            </div>
          ) : null}

          {tab === "rateCard" ? (
            dossier.rate_card ? (
              <div className="space-y-4">
                <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm dark:border-gray-700 dark:bg-gray-800">
                  <p className="font-medium">{dossier.rate_card.name}</p>
                  <p className="text-gray-500 dark:text-gray-400">
                    {dossier.rate_card.version_number != null
                      ? t("rateCardVersion", { number: dossier.rate_card.version_number })
                      : null}
                    {dossier.rate_card.effective_date
                      ? ` · ${t("effectiveDate")}: ${new Date(
                          dossier.rate_card.effective_date,
                        ).toLocaleDateString(locale === "ja" ? "ja-JP" : "en-US")}`
                      : ""}
                  </p>
                </div>

                {roles.length > 0 ? (
                  <div>
                    <h3 className="mb-2 font-medium">{tRateCards("roles")}</h3>
                    <div className={tableWrapperClass()}>
                      <table className="min-w-full divide-y divide-gray-200 text-sm dark:divide-gray-700">
                        <thead className="bg-gray-50 dark:bg-gray-800">
                          <tr>
                            <th className="px-3 py-2 text-left font-medium text-gray-700 dark:text-gray-200">
                              {tRateCards("roleName")}
                            </th>
                            <th className="px-3 py-2 text-right font-medium text-gray-700 dark:text-gray-200">
                              {tRateCards("hourlyRate", { symbol })}
                            </th>
                            <th className="px-3 py-2 text-right font-medium text-gray-700 dark:text-gray-200">
                              {tRateCards("dailyRate", { symbol })}
                            </th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-900">
                          {roles.map((role) => (
                            <tr key={role.name}>
                              <td className="px-3 py-2">{role.name}</td>
                              <td className="px-3 py-2 text-right">
                                {formatAmount(role.hourly_rate)}
                              </td>
                              <td className="px-3 py-2 text-right">
                                {role.daily_rate != null ? formatAmount(role.daily_rate) : "—"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ) : null}

                {setupCostItems.length > 0 ? (
                  <div>
                    <h3 className="mb-2 font-medium">{tRateCards("setupCosts")}</h3>
                    <div className={tableWrapperClass()}>
                      <table className="min-w-full divide-y divide-gray-200 text-sm dark:divide-gray-700">
                        <thead className="bg-gray-50 dark:bg-gray-800">
                          <tr>
                            <th className="px-3 py-2 text-left font-medium text-gray-700 dark:text-gray-200">
                              {tRateCards("itemName")}
                            </th>
                            <th className="px-3 py-2 text-right font-medium text-gray-700 dark:text-gray-200">
                              {tRateCards("amount", { symbol })}
                            </th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-900">
                          {setupCostItems.map((item) => (
                            <tr key={item.name}>
                              <td className="px-3 py-2">{item.name}</td>
                              <td className="px-3 py-2 text-right">{formatAmount(item.amount)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ) : null}

                {monthlyRcItems.length > 0 ? (
                  <div>
                    <h3 className="mb-2 font-medium">{tRateCards("monthlyRcItems")}</h3>
                    <div className={tableWrapperClass()}>
                      <table className="min-w-full divide-y divide-gray-200 text-sm dark:divide-gray-700">
                        <thead className="bg-gray-50 dark:bg-gray-800">
                          <tr>
                            <th className="px-3 py-2 text-left font-medium text-gray-700 dark:text-gray-200">
                              {tRateCards("itemName")}
                            </th>
                            <th className="px-3 py-2 text-right font-medium text-gray-700 dark:text-gray-200">
                              {tRateCards("amount", { symbol })}
                            </th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-900">
                          {monthlyRcItems.map((item) => (
                            <tr key={item.name}>
                              <td className="px-3 py-2">{item.name}</td>
                              <td className="px-3 py-2 text-right">{formatAmount(item.amount)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ) : null}
              </div>
            ) : (
              <p className="text-sm text-gray-500 dark:text-gray-400">{t("rateCardEmpty")}</p>
            )
          ) : null}

          {tab === "proposal" ? (
            proposals.length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400">{t("emptyProposals")}</p>
            ) : (
              <div className="space-y-4">
                {proposals.length > 1 ? (
                  <nav
                    className="flex flex-wrap gap-2"
                    aria-label={t("proposalLocaleSwitcher")}
                  >
                    {proposals.map((proposal, idx) => (
                      <button
                        key={proposal.id}
                        type="button"
                        onClick={() => setProposalIndex(idx)}
                        aria-current={idx === proposalIndex ? "page" : undefined}
                        className={tabButtonClass(idx === proposalIndex)}
                      >
                        {proposal.locale.toUpperCase()}
                      </button>
                    ))}
                  </nav>
                ) : null}

                {activeProposal ? (
                  <div className="space-y-4">
                    <dl className="flex flex-wrap gap-x-6 gap-y-1 rounded-lg border border-gray-200 bg-gray-50 p-4 text-xs text-gray-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400">
                      <div className="flex gap-1">
                        <dt>{t("statusLabel")}:</dt>
                        <dd className="font-medium text-gray-700 dark:text-gray-200">
                          {activeProposal.status}
                        </dd>
                      </div>
                      <div className="flex gap-1">
                        <dt>{t("localeLabel")}:</dt>
                        <dd className="font-medium text-gray-700 dark:text-gray-200">
                          {activeProposal.locale.toUpperCase()}
                        </dd>
                      </div>
                    </dl>

                    <ProposalPartSection
                      title={tProposal("partAssessment")}
                      blob={activeProposal.assessment as ProposalPartBlob | null}
                      noneLabel={t("noneLabel")}
                      projectBriefLabel={t("projectBrief")}
                      pocRecommendedLabel={t("pocRecommendedBadge")}
                    />
                    <ProposalPartSection
                      title={tProposal("partProposal")}
                      blob={activeProposal.proposal_body as ProposalPartBlob | null}
                      noneLabel={t("noneLabel")}
                      projectBriefLabel={t("projectBrief")}
                      pocRecommendedLabel={t("pocRecommendedBadge")}
                    />
                    <ProposalPartSection
                      title={tProposal("partPoc")}
                      blob={activeProposal.poc as ProposalPartBlob | null}
                      noneLabel={t("noneLabel")}
                      projectBriefLabel={t("projectBrief")}
                      pocRecommendedLabel={t("pocRecommendedBadge")}
                    />
                  </div>
                ) : null}
              </div>
            )
          ) : null}

          <InternalExportPanel
            estimateId={estimateId}
            hasCalculation={dossier.has_calculation}
          />
        </div>
      ) : null}
    </div>
  );
}
