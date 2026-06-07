"use client";

import { useTranslations } from "next-intl";

export type CalculationResult = {
  total_effort_hours: number;
  total_effort_days: number;
  phase_breakdown: Array<{ phase: string; hours: number; percentage: number }>;
  role_breakdown: Array<{
    role: string;
    hours: number;
    rate_jpy: number;
    cost_jpy: number;
  }>;
  nrc: {
    labor_jpy: number;
    setup_jpy: number;
    contingency_jpy: number;
    overhead_jpy: number;
    total_jpy: number;
  };
  rc: {
    monthly_items: Array<{ name: string; amount_jpy: number }>;
    maintenance_jpy: number;
    monthly_total_jpy: number;
    annual_total_jpy: number;
  };
  first_year_total_jpy: number;
  rate_card_version_id: string;
};

type CalculationBreakdownProps = {
  result: CalculationResult;
};

function formatJpy(value: number): string {
  return `¥${value.toLocaleString()}`;
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

export default function CalculationBreakdown({ result }: CalculationBreakdownProps) {
  const t = useTranslations("calculation");

  return (
    <section className="mt-8 space-y-8 border-t border-gray-200 pt-8">
      <div>
        <h2 className="text-lg font-semibold">{t("title")}</h2>
        <p className="text-sm text-gray-500">{t("description")}</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
          <p className="text-sm text-gray-500">{t("totalHours")}</p>
          <p className="text-xl font-semibold">{result.total_effort_hours.toLocaleString()}</p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
          <p className="text-sm text-gray-500">{t("totalDays")}</p>
          <p className="text-xl font-semibold">{result.total_effort_days.toLocaleString()}</p>
          <p className="text-xs text-gray-400">{t("daysFormula")}</p>
        </div>
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
                  <td className="px-3 py-2">{row.phase}</td>
                  <td className="px-3 py-2 text-right">{(row.percentage * 100).toFixed(0)}%</td>
                  <td className="px-3 py-2 text-right">{row.hours.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div>
        <h3 className="mb-2 font-medium">{t("roleBreakdown")}</h3>
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left font-medium text-gray-700">{t("role")}</th>
                <th className="px-3 py-2 text-right font-medium text-gray-700">{t("hours")}</th>
                <th className="px-3 py-2 text-right font-medium text-gray-700">{t("rate")}</th>
                <th className="px-3 py-2 text-right font-medium text-gray-700">
                  {t("cost")}
                  <Tooltip text={t("roleCostFormula")} />
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {result.role_breakdown.map((row) => (
                <tr key={row.role}>
                  <td className="px-3 py-2">{row.role}</td>
                  <td className="px-3 py-2 text-right">{row.hours.toLocaleString()}</td>
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
              <tr>
                <td className="px-3 py-2">{t("setup")}</td>
                <td className="px-3 py-2 text-right">{formatJpy(result.nrc.setup_jpy)}</td>
              </tr>
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
            <tbody className="divide-y divide-gray-200 bg-white">
              {result.rc.monthly_items.map((item) => (
                <tr key={item.name}>
                  <td className="px-3 py-2">{item.name}</td>
                  <td className="px-3 py-2 text-right">{formatJpy(item.amount_jpy)}</td>
                </tr>
              ))}
              <tr>
                <td className="px-3 py-2">
                  {t("maintenance")}
                  <Tooltip text={t("maintenanceFormula")} />
                </td>
                <td className="px-3 py-2 text-right">{formatJpy(result.rc.maintenance_jpy)}</td>
              </tr>
              <tr className="bg-gray-50">
                <td className="px-3 py-2 font-medium">{t("monthlyTotal")}</td>
                <td className="px-3 py-2 text-right font-medium">
                  {formatJpy(result.rc.monthly_total_jpy)}
                </td>
              </tr>
              <tr className="bg-gray-50 font-semibold">
                <td className="px-3 py-2">{t("annualTotal")}</td>
                <td className="px-3 py-2 text-right">{formatJpy(result.rc.annual_total_jpy)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div className="rounded-lg border-2 border-indigo-200 bg-indigo-50 p-4">
        <p className="text-sm text-indigo-700">{t("firstYearTotal")}</p>
        <p className="text-2xl font-bold text-indigo-900">
          {formatJpy(result.first_year_total_jpy)}
        </p>
        <p className="text-xs text-indigo-600">{t("firstYearFormula")}</p>
      </div>
    </section>
  );
}
