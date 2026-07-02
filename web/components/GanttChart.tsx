"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { apiJson } from "@/lib/api";
import { useDisplayLabels } from "@/lib/displayI18n";

export type GanttTask = {
  feature_item_id: string | null;
  name: string;
  phase: string;
  role: string;
  hours: number;
  effort_days: number;
  personnel_count?: number;
  start_date: string;
  end_date: string;
  duration_working_days: number;
};

export type GanttPhase = {
  phase: string;
  start_date: string;
  end_date: string;
  duration_working_days: number;
};

export type GanttData = {
  project_start_date: string;
  project_end_date: string;
  total_working_days: number;
  phases: GanttPhase[];
  tasks: GanttTask[];
};

export type DeliveryScheduleAdvisory = {
  delivery_schedule_status: "within_band" | "over_band" | "unknown";
  delivery_schedule_message_key?: string;
  target_working_days?: number | null;
  actual_working_days?: number;
};

type GanttChartProps = {
  estimateId: string;
  initialStartDate: string | null;
  initialGantt: GanttData | null;
  hasFeatureItems: boolean;
  onStartDateChange?: (value: string) => void;
  deliveryScheduleAdvisory?: DeliveryScheduleAdvisory | null;
};

const inputClassName =
  "rounded border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500";

function parseDate(value: string): Date {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function formatDisplayDate(value: string, locale: string): string {
  const [year, month, day] = value.split("-").map(Number);
  const date = new Date(year, month - 1, day);
  return date.toLocaleDateString(locale === "ja" ? "ja-JP" : "en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function defaultStartDateValue(): string {
  const today = new Date();
  const day = today.getDay();
  const daysUntilMonday = day === 0 ? 1 : day === 6 ? 2 : day === 1 ? 0 : (8 - day) % 7;
  const start = new Date(today);
  start.setDate(today.getDate() + (day === 1 ? 0 : daysUntilMonday || 7));
  return start.toISOString().slice(0, 10);
}

function taskBarStyle(
  task: GanttTask,
  projectStart: string,
  projectEnd: string,
): { left: string; width: string } {
  const start = parseDate(projectStart).getTime();
  const end = parseDate(projectEnd).getTime();
  const total = Math.max(end - start, 1);
  const taskStart = parseDate(task.start_date).getTime();
  const taskEnd = parseDate(task.end_date).getTime();
  const left = ((taskStart - start) / total) * 100;
  const width = Math.max(((taskEnd - taskStart) / total) * 100 + (100 / total) * 86400000, 2);
  return {
    left: `${Math.max(0, left)}%`,
    width: `${Math.min(100 - left, width)}%`,
  };
}

const phaseColors: Record<string, string> = {
  requirement: "bg-sky-500",
  design: "bg-violet-500",
  development: "bg-indigo-600",
  testing: "bg-amber-500",
  deployment: "bg-emerald-500",
};

function phaseColor(phase: string): string {
  const key = phase.trim().toLowerCase();
  return phaseColors[key] ?? "bg-gray-500";
}

export default function GanttChart({
  estimateId,
  initialStartDate,
  initialGantt,
  hasFeatureItems,
  onStartDateChange,
  deliveryScheduleAdvisory = null,
}: GanttChartProps) {
  const t = useTranslations("gantt");
  const tCalc = useTranslations("calculation");
  const { locale, translatePhase, translateRole } = useDisplayLabels();
  const [startDate, setStartDate] = useState(initialStartDate ?? defaultStartDateValue());
  const [gantt, setGantt] = useState<GanttData | null>(initialGantt);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const loadGantt = useCallback(
    async (dateValue: string) => {
      setLoading(true);
      setError(null);
      try {
        const response = await apiJson<{ gantt: GanttData }>(
          `/estimates/${estimateId}/gantt?start_date=${encodeURIComponent(dateValue)}`,
          {},
          locale,
        );
        setGantt(response.gantt);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : t("loadError"));
      } finally {
        setLoading(false);
      }
    },
    [estimateId, locale, t],
  );

  useEffect(() => {
    if (initialGantt) {
      setGantt(initialGantt);
      if (initialGantt.project_start_date) {
        setStartDate(initialGantt.project_start_date);
      }
    }

    if (hasFeatureItems) {
      void loadGantt(initialStartDate ?? startDate);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [estimateId, hasFeatureItems, initialGantt, locale]);

  useEffect(() => {
    if (initialStartDate) {
      setStartDate(initialStartDate);
    }
  }, [initialStartDate]);

  const ticks = useMemo(() => {
    if (!gantt || gantt.tasks.length === 0) {
      return [];
    }
    const start = parseDate(gantt.project_start_date);
    const end = parseDate(gantt.project_end_date);
    const labels: string[] = [];
    const cursor = new Date(start);
    while (cursor <= end) {
      if (cursor.getDay() > 0 && cursor.getDay() < 6) {
        labels.push(cursor.toISOString().slice(0, 10));
      }
      cursor.setDate(cursor.getDate() + 7);
    }
    if (labels[labels.length - 1] !== gantt.project_end_date) {
      labels.push(gantt.project_end_date);
    }
    return labels;
  }, [gantt]);

  async function handleSaveStartDate() {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      await apiJson(
        `/estimates/${estimateId}`,
        {
          method: "PATCH",
          body: JSON.stringify({ project_start_date: startDate }),
        },
        locale,
      );
      onStartDateChange?.(startDate);
      setSaved(true);
      await loadGantt(startDate);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : t("saveError"));
    } finally {
      setSaving(false);
    }
  }

  function handleStartDateChange(value: string) {
    setStartDate(value);
    setSaved(false);
    onStartDateChange?.(value);
  }

  if (!hasFeatureItems) {
    return null;
  }

  return (
    <section className="mt-8 border-t border-gray-200 pt-8">
      <div className="mb-4 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 className="text-lg font-semibold">{t("title")}</h2>
          <p className="text-sm text-gray-500">{t("description")}</p>
          <p className="mt-1 text-xs text-gray-400">{t("assumption")}</p>
        </div>

        <div className="flex flex-wrap items-end gap-2">
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-gray-700">{t("startDate")}</span>
            <input
              type="date"
              value={startDate}
              onChange={(event) => handleStartDateChange(event.target.value)}
              className={inputClassName}
            />
          </label>
          <button
            type="button"
            onClick={() => void handleSaveStartDate()}
            disabled={saving}
            className="rounded border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50 disabled:opacity-50"
          >
            {saving ? t("saving") : t("saveStartDate")}
          </button>
          <button
            type="button"
            onClick={() => void loadGantt(startDate)}
            disabled={loading}
            className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {loading ? t("refreshing") : t("refresh")}
          </button>
        </div>
      </div>

      {saved && <p className="mb-3 text-sm text-green-600">{t("saved")}</p>}
      {error && (
        <p className="mb-3 text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      {deliveryScheduleAdvisory && (
        <div
          className={`mb-4 rounded-lg border p-4 text-sm ${
            deliveryScheduleAdvisory.delivery_schedule_status === "over_band"
              ? "border-amber-300 bg-amber-50 text-amber-900"
              : deliveryScheduleAdvisory.delivery_schedule_status === "within_band"
                ? "border-emerald-300 bg-emerald-50 text-emerald-900"
                : "border-gray-200 bg-gray-50 text-gray-700"
          }`}
          role="status"
        >
          {deliveryScheduleAdvisory.delivery_schedule_status === "unknown"
            ? tCalc("deliverySchedule.unknown")
            : tCalc(
                deliveryScheduleAdvisory.delivery_schedule_status === "within_band"
                  ? "deliverySchedule.withinBand"
                  : "deliverySchedule.overBand",
                {
                  actualDays: deliveryScheduleAdvisory.actual_working_days ?? 0,
                  targetDays: deliveryScheduleAdvisory.target_working_days ?? 0,
                },
              )}
        </div>
      )}

      {loading && !gantt && <p className="text-sm text-gray-500">{t("loading")}</p>}

      {gantt && gantt.tasks.length > 0 && (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm">
              <p className="text-gray-500">{t("projectStart")}</p>
              <p className="font-medium">{formatDisplayDate(gantt.project_start_date, locale)}</p>
            </div>
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm">
              <p className="text-gray-500">{t("projectEnd")}</p>
              <p className="font-medium">{formatDisplayDate(gantt.project_end_date, locale)}</p>
            </div>
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm">
              <p className="text-gray-500">{t("totalWorkingDays")}</p>
              <p className="font-medium">{gantt.total_working_days}</p>
            </div>
          </div>

          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <div className="min-w-[720px] bg-white p-4">
              <div className="mb-2 flex justify-between text-xs text-gray-400">
                {ticks.map((tick) => (
                  <span key={tick}>{formatDisplayDate(tick, locale)}</span>
                ))}
              </div>

              <div className="space-y-2">
                {gantt.tasks.map((task) => {
                  const style = taskBarStyle(
                    task,
                    gantt.project_start_date,
                    gantt.project_end_date,
                  );
                  return (
                    <div key={`${task.feature_item_id ?? task.name}-${task.start_date}`} className="grid grid-cols-[180px_1fr] items-center gap-3">
                      <div className="truncate text-sm">
                        <p className="font-medium text-gray-900">{task.name}</p>
                        <p className="text-xs text-gray-500">
                          {translatePhase(task.phase)} · {translateRole(task.role)}
                        </p>
                      </div>
                      <div className="relative h-8 rounded bg-gray-100">
                        <div
                          className={`absolute top-1 bottom-1 rounded ${phaseColor(task.phase)} opacity-90`}
                          style={style}
                          title={`${formatDisplayDate(task.start_date, locale)} – ${formatDisplayDate(task.end_date, locale)}`}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="min-w-[56rem] w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="min-w-[10rem] px-3 py-2 text-left font-medium text-gray-700">{t("task")}</th>
                  <th className="whitespace-nowrap px-3 py-2 text-left font-medium text-gray-700">{t("phase")}</th>
                  <th className="whitespace-nowrap px-3 py-2 text-left font-medium text-gray-700">{t("role")}</th>
                  <th className="whitespace-nowrap px-3 py-2 text-right font-medium text-gray-700">{tCalc("headcount")}</th>
                  <th className="whitespace-nowrap px-3 py-2 text-right font-medium text-gray-700">{t("hours")}</th>
                  <th className="whitespace-nowrap px-3 py-2 text-left font-medium text-gray-700">{t("startDate")}</th>
                  <th className="whitespace-nowrap px-3 py-2 text-left font-medium text-gray-700">{t("endDate")}</th>
                  <th className="whitespace-nowrap px-3 py-2 text-right font-medium text-gray-700">{t("durationDays")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {gantt.tasks.map((task) => (
                  <tr key={`row-${task.feature_item_id ?? task.name}-${task.start_date}`}>
                    <td className="min-w-[10rem] px-3 py-2">{task.name}</td>
                    <td className="whitespace-nowrap px-3 py-2">{translatePhase(task.phase)}</td>
                    <td className="whitespace-nowrap px-3 py-2">{translateRole(task.role)}</td>
                    <td className="whitespace-nowrap px-3 py-2 text-right">{task.personnel_count ?? 1}</td>
                    <td className="whitespace-nowrap px-3 py-2 text-right">{task.hours}</td>
                    <td className="whitespace-nowrap px-3 py-2">{formatDisplayDate(task.start_date, locale)}</td>
                    <td className="whitespace-nowrap px-3 py-2">{formatDisplayDate(task.end_date, locale)}</td>
                    <td className="whitespace-nowrap px-3 py-2 text-right">{task.duration_working_days}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {gantt && gantt.tasks.length === 0 && !loading && (
        <p className="text-sm text-gray-500">{t("empty")}</p>
      )}
    </section>
  );
}
