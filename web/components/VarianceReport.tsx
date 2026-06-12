"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";

export type VarianceMetric = {
  estimated: number;
  actual: number;
  variance_pct: number;
  severity: "green" | "amber" | "red";
};

export type VarianceSummary = {
  effort_hours: VarianceMetric;
  effort_days: VarianceMetric;
  nrc_jpy: VarianceMetric;
  rc_monthly_jpy: VarianceMetric;
};

export type VarianceDashboardRow = {
  estimate_id: string;
  project_name: string;
  client_name: string;
  completed_at: string;
  actuals_entered_at: string | null;
  variance: VarianceSummary | null;
  variance_notes: string | null;
};

type VarianceReportProps = {
  rows: VarianceDashboardRow[];
  locale: string;
  showProjectLink?: boolean;
};

const severityClass: Record<VarianceMetric["severity"], string> = {
  green: "bg-green-100 text-green-800",
  amber: "bg-amber-100 text-amber-800",
  red: "bg-red-100 text-red-800",
};

function formatPct(value: number): string {
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(1)}%`;
}

function formatJpy(value: number, locale: string): string {
  return new Intl.NumberFormat(locale === "ja" ? "ja-JP" : "en-US", {
    style: "currency",
    currency: "JPY",
    maximumFractionDigits: 0,
  }).format(value);
}

function MetricCell({
  metric,
  formatValue,
}: {
  metric: VarianceMetric;
  formatValue: (value: number) => string;
}) {
  return (
    <td className="px-3 py-2 text-sm">
      <div className="flex flex-col gap-1">
        <span className="text-gray-600">
          {formatValue(metric.estimated)} → {formatValue(metric.actual)}
        </span>
        <span
          className={`inline-flex w-fit rounded-full px-2 py-0.5 text-xs font-medium ${severityClass[metric.severity]}`}
        >
          {formatPct(metric.variance_pct)}
        </span>
      </div>
    </td>
  );
}

export default function VarianceReport({
  rows,
  locale,
  showProjectLink = true,
}: VarianceReportProps) {
  const t = useTranslations("variance");

  if (rows.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-gray-300 bg-white p-8 text-center text-gray-500">
        {t("empty")}
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
              {t("columns.project")}
            </th>
            <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
              {t("columns.client")}
            </th>
            <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
              {t("columns.effortHours")}
            </th>
            <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
              {t("columns.effortDays")}
            </th>
            <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
              {t("columns.nrc")}
            </th>
            <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
              {t("columns.rcMonthly")}
            </th>
            <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
              {t("columns.notes")}
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {rows.map((row) => (
            <tr key={row.estimate_id} className="align-top">
              <td className="px-3 py-2 text-sm font-medium text-gray-900">
                {showProjectLink ? (
                  <Link
                    href={`/${locale}/estimates/${row.estimate_id}`}
                    className="text-indigo-600 hover:text-indigo-800"
                  >
                    {row.project_name}
                  </Link>
                ) : (
                  row.project_name
                )}
              </td>
              <td className="px-3 py-2 text-sm text-gray-700">{row.client_name}</td>
              {row.variance ? (
                <>
                  <MetricCell
                    metric={row.variance.effort_hours}
                    formatValue={(value) => `${value.toLocaleString()}h`}
                  />
                  <MetricCell
                    metric={row.variance.effort_days}
                    formatValue={(value) => `${value.toLocaleString()}d`}
                  />
                  <MetricCell
                    metric={row.variance.nrc_jpy}
                    formatValue={(value) => formatJpy(value, locale)}
                  />
                  <MetricCell
                    metric={row.variance.rc_monthly_jpy}
                    formatValue={(value) => formatJpy(value, locale)}
                  />
                </>
              ) : (
                <td colSpan={4} className="px-3 py-2 text-sm text-gray-400">
                  {t("noActuals")}
                </td>
              )}
              <td className="px-3 py-2 text-sm text-gray-600">
                {row.variance_notes || "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
