"use client";

import { useLocale, useTranslations } from "next-intl";
import { useDisplayLabels } from "@/lib/displayI18n";
import { filterActiveRoleBreakdown } from "@/lib/calculation";
import { roleDevelopersCount } from "@/lib/datetime";

type LineItemAmount = {
  amount?: number | null;
  amount_jpy?: number | null;
};

function lineItemAmountJpy(item: LineItemAmount): number {
  if (item.amount_jpy != null) {
    return item.amount_jpy;
  }
  return item.amount ?? 0;
}

export type CalculationResult = {
  total_effort_hours: number;
  total_effort_days: number;
  estimated_duration_days?: number;
  development_approach?: string;
  development_approach_effort_multiplier?: number;
  recommended_team_size?: number;
  phase_breakdown: Array<{ phase: string; hours: number; percentage: number }>;
  role_breakdown: Array<{
    role: string;
    hours: number;
    personnel_count?: number;
    rate_jpy: number;
    cost_jpy: number;
  }>;
  nrc: {
    labor_jpy: number;
    setup_items?: Array<{ name: string; amount?: number | null; amount_jpy?: number | null }>;
    setup_jpy: number;
    contingency_jpy: number;
    overhead_jpy: number;
    total_jpy: number;
  };
  rc: {
    monthly_items: Array<{ name: string; amount?: number | null; amount_jpy?: number | null }>;
    maintenance_jpy: number;
    monthly_total_jpy: number;
    annual_total_jpy: number;
  };
  rc_detailed_breakdown?: {
    line_items: Array<{
      category_key: string;
      category: string;
      service_description: string;
      monthly_jpy: number;
      annual_jpy: number;
      is_maintenance?: boolean;
    }>;
    monthly_total_jpy: number;
    annual_total_jpy: number;
    markup_rate_applied?: number;
  };
  first_year_total_jpy: number;
  rate_card_version_id: string;
  nrc_original_total_jpy?: number | null;
  discount_rate_applied?: number | null;
  discount_amount_jpy?: number | null;
};

type CalculationBreakdownProps = {
  result: CalculationResult;
  embedded?: boolean;
  quotationIssueDate?: string | null;
};

function formatIssueDate(value: string, locale: string): string {
  try {
    return new Intl.DateTimeFormat(locale === "ja" ? "ja-JP" : "en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function hasPricingDiscount(result: CalculationResult): boolean {
  const rate = result.discount_rate_applied;
  const original = result.nrc_original_total_jpy;
  return (
    rate != null &&
    rate > 0 &&
    original != null &&
    original > result.nrc.total_jpy
  );
}

function Tooltip({ text }: { text: string }) {
  return (
    <span
      className="ml-1 cursor-help text-gray-400"
      title={text}
      aria-label={text}
    >
      ⓘ
    </span>
  );
}

export default function CalculationBreakdown({
  result,
  embedded = false,
  quotationIssueDate = null,
}: CalculationBreakdownProps) {
  const locale = useLocale();
  const t = useTranslations("calculation");
  const tRateCards = useTranslations("rateCards");
  const { translatePhase, translateRole, translateSetupItem, formatJpy, formatNumber } =
    useDisplayLabels();

  const approachKey = result.development_approach;
  const approachLabel =
    approachKey &&
    ["traditional", "ai_assisted", "hybrid", "low_code"].includes(approachKey)
      ? tRateCards(`developmentApproachOptions.${approachKey}.label`)
      : null;

  const activeRoleBreakdown = filterActiveRoleBreakdown(
    result.role_breakdown,
    result.estimated_duration_days,
    result.total_effort_days,
  );

  return (
    <section
      className={
        embedded
          ? "space-y-8"
          : "mt-8 space-y-8 border-t border-gray-200 pt-8"
      }
    >
      {!embedded && (
        <div>
          <h2 className="text-lg font-semibold">{t("title")}</h2>
          <p className="text-sm text-gray-500">{t("description")}</p>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {approachLabel && (
          <>
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
              <p className="text-sm text-gray-500">{t("developmentApproach")}</p>
              <p className="text-xl font-semibold">{approachLabel}</p>
            </div>
            {result.development_approach_effort_multiplier != null && (
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                <p className="text-sm text-gray-500">{t("developmentApproachMultiplier")}</p>
                <p className="text-xl font-semibold">
                  ×{result.development_approach_effort_multiplier}
                </p>
              </div>
            )}
          </>
        )}
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
          <p className="text-sm text-gray-500">{t("totalHours")}</p>
          <p className="text-xl font-semibold">{formatNumber(result.total_effort_hours)}</p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
          <p className="text-sm text-gray-500">{t("totalDays")}</p>
          <p className="text-xl font-semibold">{formatNumber(result.total_effort_days)}</p>
          <p className="text-xs text-gray-400">{t("daysFormula")}</p>
        </div>
        {result.recommended_team_size != null && (
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
            <p className="text-sm text-gray-500">{t("recommendedTeamSize")}</p>
            <p className="text-xl font-semibold">{formatNumber(result.recommended_team_size)}</p>
            <p className="text-xs text-gray-400">{t("recommendedTeamSizeHint")}</p>
          </div>
        )}
      </div>

      <div>
        <h3 className="mb-2 font-medium">{t("phaseBreakdown")}</h3>
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left font-medium text-gray-700">{t("phase")}</th>
                <th className="px-3 py-2 text-right font-medium text-gray-700">{t("percentage")}</th>
                <th className="px-3 py-2 text-right font-medium text-gray-700">
                  {t("hours")}
                  <Tooltip text={t("phaseHoursFormula")} />
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {result.phase_breakdown.map((row) => (
                <tr key={row.phase}>
                  <td className="px-3 py-2">{translatePhase(row.phase)}</td>
                  <td className="px-3 py-2 text-right">{(row.percentage * 100).toFixed(0)}%</td>
                  <td className="px-3 py-2 text-right">{formatNumber(row.hours)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div>
        <h3 className="mb-1 font-medium">{t("roleBreakdown")}</h3>
        <p className="mb-2 text-xs text-gray-500">{t("roleBreakdownHint")}</p>
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left font-medium text-gray-700">{t("role")}</th>
                <th className="px-3 py-2 text-right font-medium text-gray-700">
                  {t("headcount")}
                  <Tooltip text={t("headcountFormula")} />
                </th>
                <th className="px-3 py-2 text-right font-medium text-gray-700">{t("hours")}</th>
                <th className="px-3 py-2 text-right font-medium text-gray-700">{t("rate")}</th>
                <th className="px-3 py-2 text-right font-medium text-gray-700">
                  {t("cost")}
                  <Tooltip text={t("roleCostFormula")} />
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {activeRoleBreakdown.map((row) => (
                <tr key={row.role}>
                  <td className="px-3 py-2">{translateRole(row.role)}</td>
                  <td className="px-3 py-2 text-right">
                    {row.hours > 0
                      ? formatNumber(
                          roleDevelopersCount(
                            row.hours,
                            row.personnel_count,
                            result.estimated_duration_days,
                            result.total_effort_days,
                          ),
                        )
                      : "—"}
                  </td>
                  <td className="px-3 py-2 text-right">{formatNumber(row.hours)}</td>
                  <td className="px-3 py-2 text-right">{formatJpy(row.rate_jpy)}</td>
                  <td className="px-3 py-2 text-right">{formatJpy(row.cost_jpy)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div>
        <h3 className="mb-2 font-medium">
          {t("nrcTitle")}
          <Tooltip text={t("nrcFormula")} />
        </h3>
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <tbody className="divide-y divide-gray-200 bg-white">
              <tr>
                <td className="px-3 py-2">{t("labor")}</td>
                <td className="px-3 py-2 text-right">{formatJpy(result.nrc.labor_jpy)}</td>
              </tr>
              {(result.nrc.setup_items ?? []).map((item) => (
                <tr key={item.name}>
                  <td className="px-3 py-2 pl-6 text-gray-600">
                    {t("setup")}: {translateSetupItem(item.name)}
                  </td>
                  <td className="px-3 py-2 text-right">{formatJpy(lineItemAmountJpy(item))}</td>
                </tr>
              ))}
              {(!result.nrc.setup_items || result.nrc.setup_items.length === 0) && (
                <tr>
                  <td className="px-3 py-2">{t("setup")}</td>
                  <td className="px-3 py-2 text-right">{formatJpy(result.nrc.setup_jpy)}</td>
                </tr>
              )}
              {(result.nrc.setup_items?.length ?? 0) > 0 && (
                <tr className="bg-gray-50">
                  <td className="px-3 py-2 font-medium">{t("setupTotal")}</td>
                  <td className="px-3 py-2 text-right font-medium">
                    {formatJpy(result.nrc.setup_jpy)}
                  </td>
                </tr>
              )}
              <tr>
                <td className="px-3 py-2">
                  {t("contingency")}
                  <Tooltip text={t("contingencyFormula")} />
                </td>
                <td className="px-3 py-2 text-right">{formatJpy(result.nrc.contingency_jpy)}</td>
              </tr>
              <tr>
                <td className="px-3 py-2">
                  {t("overhead")}
                  <Tooltip text={t("overheadFormula")} />
                </td>
                <td className="px-3 py-2 text-right">{formatJpy(result.nrc.overhead_jpy)}</td>
              </tr>
              <tr className="bg-gray-50 font-semibold">
                <td className="px-3 py-2">{t("nrcTotal")}</td>
                <td className="px-3 py-2 text-right">{formatJpy(result.nrc.total_jpy)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div>
        <h3 className="mb-2 font-medium">
          {t("rcTitle")}
          <Tooltip text={t("rcFormula")} />
        </h3>
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left font-medium text-gray-700">{t("rcCategory")}</th>
                <th className="px-3 py-2 text-left font-medium text-gray-700">
                  {t("rcServiceDescription")}
                </th>
                <th className="px-3 py-2 text-right font-medium text-gray-700">{t("cost")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {(result.rc_detailed_breakdown?.line_items ?? []).map((row) => (
                <tr key={row.category_key}>
                  <td className="px-3 py-2">{row.category}</td>
                  <td className="px-3 py-2">{row.service_description}</td>
                  <td className="px-3 py-2 text-right">{formatJpy(row.monthly_jpy)}</td>
                </tr>
              ))}
              <tr className="bg-gray-50">
                <td className="px-3 py-2 font-medium" colSpan={2}>
                  {t("monthlyTotal")}
                </td>
                <td className="px-3 py-2 text-right font-medium">
                  {formatJpy(
                    result.rc_detailed_breakdown?.monthly_total_jpy ?? result.rc.monthly_total_jpy,
                  )}
                </td>
              </tr>
              <tr className="bg-gray-50 font-semibold">
                <td className="px-3 py-2" colSpan={2}>
                  {t("annualTotal")}
                </td>
                <td className="px-3 py-2 text-right">
                  {formatJpy(
                    result.rc_detailed_breakdown?.annual_total_jpy ?? result.rc.annual_total_jpy,
                  )}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {!embedded && (
        <>
          <div
            id="total-development-cost"
            className="scroll-mt-20 rounded-lg border-2 border-indigo-200 bg-indigo-50 p-4"
          >
            {hasPricingDiscount(result) ? (
              <div className="space-y-2">
                <div className="flex items-baseline justify-between gap-4">
                  <p className="text-sm text-indigo-700">{t("pricing.developmentCost")}</p>
                  <p className="text-lg font-semibold text-indigo-900">
                    {formatJpy(result.nrc_original_total_jpy!)}
                  </p>
                </div>
                <div className="flex items-baseline justify-between gap-4">
                  <p className="text-sm text-indigo-700">{t("pricing.limitedTimeDiscount")}</p>
                  <p className="text-sm font-medium text-emerald-700">
                    {t("pricing.discountOff", {
                      percent: Math.round((result.discount_rate_applied ?? 0) * 100),
                      amount: formatJpy(
                        result.discount_amount_jpy ??
                          result.nrc_original_total_jpy! - result.nrc.total_jpy,
                      ),
                    })}
                  </p>
                </div>
                <div className="flex items-baseline justify-between gap-4 border-t border-indigo-200 pt-2">
                  <p className="text-sm font-medium text-indigo-700">{t("pricing.specialPrice")}</p>
                  <p className="text-2xl font-bold text-indigo-900">
                    {formatJpy(result.nrc.total_jpy)}{" "}
                    <span className="text-sm font-normal text-indigo-600">
                      {t("pricing.excludingTax")}
                    </span>
                  </p>
                </div>
                <div className="mt-3 rounded border border-indigo-100 bg-white/70 p-3 text-xs text-indigo-800">
                  <p className="font-semibold">*{t("pricing.campaignTermsTitle")}</p>
                  <p className="mt-1 whitespace-pre-wrap">
                    {t("pricing.campaignTermsBody", {
                      specialPrice: `${formatJpy(result.nrc.total_jpy)} ${t("pricing.excludingTax")}`,
                      issueDate: quotationIssueDate
                        ? formatIssueDate(quotationIssueDate, locale)
                        : t("pricing.issueDateFallback"),
                    })}
                  </p>
                </div>
              </div>
            ) : (
              <>
                <p className="text-sm text-indigo-700">{t("totalDevelopmentCost")}</p>
                <p className="text-2xl font-bold text-indigo-900">
                  {formatJpy(result.nrc.total_jpy)}
                </p>
                <p className="text-xs text-indigo-600">{t("totalDevelopmentCostFormula")}</p>
              </>
            )}
          </div>

          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
            <p className="text-sm text-gray-600">{t("firstYearTotal")}</p>
            <p className="text-xl font-semibold text-gray-900">
              {formatJpy(result.first_year_total_jpy)}
            </p>
            <p className="text-xs text-gray-500">{t("firstYearFormula")}</p>
          </div>
        </>
      )}
    </section>
  );
}
