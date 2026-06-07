"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { apiJson } from "@/lib/api";
import VarianceReport, { type VarianceDashboardRow } from "@/components/VarianceReport";

type VarianceDashboardPageProps = {
  locale: string;
};

export default function VarianceDashboardPage({ locale }: VarianceDashboardPageProps) {
  const t = useTranslations("variance");
  const [rows, setRows] = useState<VarianceDashboardRow[]>([]);
  const [clientFilter, setClientFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [sortMetric, setSortMetric] = useState("effort_hours");
  const [sortOrder, setSortOrder] = useState("desc");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);

    const params = new URLSearchParams();
    if (clientFilter.trim()) {
      params.set("client", clientFilter.trim());
    }
    if (dateFrom) {
      params.set("date_from", `${dateFrom}T00:00:00`);
    }
    if (dateTo) {
      params.set("date_to", `${dateTo}T23:59:59`);
    }
    params.set("sort_metric", sortMetric);
    params.set("sort_order", sortOrder);

    try {
      const data = await apiJson<VarianceDashboardRow[]>(
        `/estimates/variance-dashboard?${params.toString()}`,
      );
      setRows(data);
    } catch (loadError) {
      setRows([]);
      setError(loadError instanceof Error ? loadError.message : t("loadError"));
    } finally {
      setLoading(false);
    }
  }, [clientFilter, dateFrom, dateTo, sortMetric, sortOrder, t]);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">{t("dashboardTitle")}</h1>
        <p className="mt-1 text-sm text-gray-500">{t("dashboardDescription")}</p>
      </div>

      <div className="mb-6 grid gap-4 rounded-lg border border-gray-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-5">
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-gray-700">{t("filters.client")}</span>
          <input
            type="text"
            value={clientFilter}
            onChange={(event) => setClientFilter(event.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2"
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-gray-700">{t("filters.dateFrom")}</span>
          <input
            type="date"
            value={dateFrom}
            onChange={(event) => setDateFrom(event.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2"
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-gray-700">{t("filters.dateTo")}</span>
          <input
            type="date"
            value={dateTo}
            onChange={(event) => setDateTo(event.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2"
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-gray-700">{t("filters.sortMetric")}</span>
          <select
            value={sortMetric}
            onChange={(event) => setSortMetric(event.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2"
          >
            <option value="effort_hours">{t("columns.effortHours")}</option>
            <option value="effort_days">{t("columns.effortDays")}</option>
            <option value="nrc_jpy">{t("columns.nrc")}</option>
            <option value="rc_monthly_jpy">{t("columns.rcMonthly")}</option>
          </select>
        </label>
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-gray-700">{t("filters.sortOrder")}</span>
          <select
            value={sortOrder}
            onChange={(event) => setSortOrder(event.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2"
          >
            <option value="desc">{t("filters.desc")}</option>
            <option value="asc">{t("filters.asc")}</option>
          </select>
        </label>
      </div>

      <div className="mb-4">
        <button
          type="button"
          onClick={() => void loadDashboard()}
          disabled={loading}
          className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? t("loading") : t("applyFilters")}
        </button>
      </div>

      {error && (
        <p className="mb-4 text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      {loading ? (
        <p className="text-sm text-gray-500">{t("loading")}</p>
      ) : (
        <VarianceReport rows={rows} locale={locale} />
      )}
    </div>
  );
}
