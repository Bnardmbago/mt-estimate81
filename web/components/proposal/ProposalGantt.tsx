"use client";

import { useMemo } from "react";
import { proposalDocLabels } from "@/lib/proposal-doc-labels";
import type { ProposalDetail } from "@/lib/proposal-types";

type ProposalGanttProps = {
  proposal: ProposalDetail;
};

const PHASE_LABELS: Record<string, Record<string, string>> = {
  en: {
    requirement: "Requirements",
    design: "Design",
    development: "Development",
    testing: "Testing",
    deployment: "Deployment",
    management: "Project management",
  },
  ja: {
    requirement: "要件定義",
    design: "設計",
    development: "開発",
    testing: "テスト",
    deployment: "導入",
    management: "プロジェクト管理",
  },
};

const PHASE_COLORS: Record<string, string> = {
  requirement: "bg-sky-500",
  design: "bg-violet-500",
  development: "bg-indigo-600",
  testing: "bg-amber-500",
  deployment: "bg-emerald-500",
  management: "bg-cyan-500",
};

/** Match Estimate GanttChart: parse YYYY-MM-DD as local date (not UTC). */
function parseDate(value: string): Date {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function formatDisplayDate(value: string, locale: string): string {
  const date = parseDate(value);
  return date.toLocaleDateString(locale === "ja" ? "ja-JP" : "en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function phaseLabel(phase: string, locale: string): string {
  const key = phase.trim().toLowerCase();
  return PHASE_LABELS[locale === "ja" ? "ja" : "en"][key] || phase.replaceAll("_", " ");
}

function phaseColor(phase: string): string {
  const key = phase.trim().toLowerCase();
  return PHASE_COLORS[key] ?? "bg-gray-500";
}

function taskBarStyle(
  task: { start_date: string; end_date: string },
  projectStart: string,
  projectEnd: string,
): { left: string; width: string } {
  const start = parseDate(projectStart).getTime();
  const end = parseDate(projectEnd).getTime();
  const total = Math.max(end - start, 1);
  const taskStart = parseDate(task.start_date).getTime();
  const taskEnd = parseDate(task.end_date).getTime();
  const left = ((taskStart - start) / total) * 100;
  const width = Math.max(
    ((taskEnd - taskStart) / total) * 100 + (100 / total) * 86400000,
    2,
  );
  return {
    left: `${Math.max(0, left)}%`,
    width: `${Math.min(100 - left, width)}%`,
  };
}

export default function ProposalGantt({ proposal }: ProposalGanttProps) {
  const labels = proposalDocLabels(proposal.locale);
  const gantt = proposal.source_snapshot.gantt;
  const tasks = useMemo(() => gantt?.tasks || [], [gantt]);
  const phases = useMemo(() => gantt?.phases || [], [gantt]);
  const milestones = proposal.milestones || [];

  const ticks = useMemo(() => {
    if (!gantt?.project_start_date || !gantt?.project_end_date || tasks.length === 0) {
      return [] as string[];
    }
    const start = parseDate(gantt.project_start_date);
    const end = parseDate(gantt.project_end_date);
    const spanDays = Math.max(
      1,
      Math.round((end.getTime() - start.getTime()) / 86400000) + 1,
    );
    const stepDays = spanDays > 120 ? 28 : spanDays > 60 ? 14 : 7;
    const labelsTicks: string[] = [];
    const cursor = new Date(start);
    while (cursor <= end) {
      if (cursor.getDay() > 0 && cursor.getDay() < 6) {
        labelsTicks.push(
          `${cursor.getFullYear()}-${String(cursor.getMonth() + 1).padStart(2, "0")}-${String(cursor.getDate()).padStart(2, "0")}`,
        );
      }
      cursor.setDate(cursor.getDate() + stepDays);
    }
    if (labelsTicks[labelsTicks.length - 1] !== gantt.project_end_date) {
      labelsTicks.push(gantt.project_end_date);
    }
    return labelsTicks;
  }, [gantt, tasks.length]);

  if (!gantt || (!tasks.length && !phases.length && !milestones.length)) {
    return null;
  }

  const locale = proposal.locale;

  return (
    <section className="my-6 print:break-inside-avoid">
      <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
        {labels.timelineTitle}
      </h3>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
        {labels.timelineRange({
          start: gantt.project_start_date
            ? formatDisplayDate(gantt.project_start_date, locale)
            : "—",
          end: gantt.project_end_date
            ? formatDisplayDate(gantt.project_end_date, locale)
            : "—",
          days: gantt.total_working_days ?? "—",
        })}
      </p>

      {gantt.project_start_date && gantt.project_end_date ? (
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm dark:border-slate-700 dark:bg-slate-900/50">
            <p className="text-slate-500">{labels.timelineTitle}</p>
            <p className="font-medium">
              {formatDisplayDate(gantt.project_start_date, locale)} →{" "}
              {formatDisplayDate(gantt.project_end_date, locale)}
            </p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm dark:border-slate-700 dark:bg-slate-900/50">
            <p className="text-slate-500">{labels.workingDays}</p>
            <p className="font-medium">{gantt.total_working_days ?? "—"}</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm dark:border-slate-700 dark:bg-slate-900/50">
            <p className="text-slate-500">{labels.milestonesTitle}</p>
            <p className="font-medium">{phases.length || milestones.length}</p>
          </div>
        </div>
      ) : null}

      {tasks.length > 0 && gantt.project_start_date && gantt.project_end_date ? (
        <div className="mt-4 overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
          <div className="min-w-[720px] bg-white p-4 dark:bg-slate-900">
            {ticks.length > 0 ? (
              <div className="mb-2 flex justify-between text-xs text-slate-400">
                {ticks.map((tick) => (
                  <span key={tick}>{formatDisplayDate(tick, locale)}</span>
                ))}
              </div>
            ) : null}

            <div className="space-y-2">
              {tasks.map((task) => {
                const style = taskBarStyle(
                  task,
                  gantt.project_start_date!,
                  gantt.project_end_date!,
                );
                return (
                  <div
                    key={`${task.feature_item_id ?? task.name}-${task.start_date}-${task.end_date}`}
                    className="grid grid-cols-[180px_1fr] items-center gap-3"
                  >
                    <div className="truncate text-sm">
                      <p className="font-medium text-slate-900 dark:text-slate-100">
                        {task.name}
                      </p>
                      <p className="text-xs text-slate-500">
                        {phaseLabel(task.phase, locale)}
                        {task.role ? ` · ${task.role}` : ""}
                      </p>
                    </div>
                    <div className="relative h-8 rounded bg-slate-100 dark:bg-slate-800">
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
      ) : phases.length > 0 && gantt.project_start_date && gantt.project_end_date ? (
        <div className="mt-4 space-y-2">
          {phases.map((phase) => {
            const style = taskBarStyle(
              { start_date: phase.start_date, end_date: phase.end_date },
              gantt.project_start_date!,
              gantt.project_end_date!,
            );
            return (
              <div
                key={`${phase.phase}-${phase.start_date}`}
                className="grid grid-cols-[8rem_1fr] items-center gap-3"
              >
                <div className="truncate text-sm text-slate-700 dark:text-slate-200">
                  {phaseLabel(phase.phase, locale)}
                </div>
                <div className="relative h-7 rounded bg-slate-100 dark:bg-slate-800">
                  <div
                    className={`absolute top-1 bottom-1 rounded ${phaseColor(phase.phase)} opacity-90`}
                    style={style}
                    title={`${phase.start_date} → ${phase.end_date}`}
                  />
                </div>
              </div>
            );
          })}
        </div>
      ) : null}

      {tasks.length > 0 ? (
        <div className="mt-4 overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
          <table className="min-w-[48rem] w-full divide-y divide-slate-200 text-sm dark:divide-slate-700">
            <thead className="bg-slate-50 dark:bg-slate-800/60">
              <tr>
                <th className="px-3 py-2 text-left font-medium text-slate-700 dark:text-slate-200">
                  {locale === "ja" ? "作業項目" : "Task"}
                </th>
                <th className="px-3 py-2 text-left font-medium text-slate-700 dark:text-slate-200">
                  {locale === "ja" ? "フェーズ" : "Phase"}
                </th>
                <th className="px-3 py-2 text-right font-medium text-slate-700 dark:text-slate-200">
                  {locale === "ja" ? "時間" : "Hours"}
                </th>
                <th className="px-3 py-2 text-left font-medium text-slate-700 dark:text-slate-200">
                  {locale === "ja" ? "開始" : "Start"}
                </th>
                <th className="px-3 py-2 text-left font-medium text-slate-700 dark:text-slate-200">
                  {locale === "ja" ? "終了" : "End"}
                </th>
                <th className="px-3 py-2 text-right font-medium text-slate-700 dark:text-slate-200">
                  {locale === "ja" ? "稼働日" : "Days"}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
              {tasks.map((task) => (
                <tr key={`row-${task.feature_item_id ?? task.name}-${task.start_date}`}>
                  <td className="px-3 py-2">{task.name}</td>
                  <td className="px-3 py-2">{phaseLabel(task.phase, locale)}</td>
                  <td className="px-3 py-2 text-right">{task.hours}</td>
                  <td className="px-3 py-2">
                    {formatDisplayDate(task.start_date, locale)}
                  </td>
                  <td className="px-3 py-2">
                    {formatDisplayDate(task.end_date, locale)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {task.duration_working_days}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {milestones.length > 0 ? (
        <div className="mt-4">
          <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
            {labels.milestonesTitle}
          </h4>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700 dark:text-slate-200">
            {milestones.map((m) => (
              <li key={m.id}>
                {m.name}
                {m.date ? ` — ${formatDisplayDate(m.date, locale)}` : ""}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
