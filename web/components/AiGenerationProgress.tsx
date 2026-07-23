"use client";

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";

export type AiProgressStepStatus =
  | "pending"
  | "running"
  | "done"
  | "error"
  | "skipped";

export type AiProgressStep = {
  id: string;
  label: string;
  status: AiProgressStepStatus;
};

type AiGenerationProgressProps = {
  active: boolean;
  title?: string;
  message?: string;
  steps?: AiProgressStep[];
  /** 0–100 when known; omit for indeterminate animation */
  percent?: number | null;
  className?: string;
  compact?: boolean;
};

function stepPercent(steps: AiProgressStep[] | undefined): number | null {
  if (!steps?.length) {
    return null;
  }
  const countable = steps.filter((s) => s.status !== "skipped");
  if (!countable.length) {
    return null;
  }
  const done = countable.filter((s) => s.status === "done").length;
  const running = countable.some((s) => s.status === "running");
  const base = (done / countable.length) * 100;
  if (running) {
    return Math.min(95, base + (100 / countable.length) * 0.45);
  }
  return Math.round(base);
}

export default function AiGenerationProgress({
  active,
  title,
  message,
  steps,
  percent,
  className = "",
  compact = false,
}: AiGenerationProgressProps) {
  const t = useTranslations("aiProgress");
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    if (!active) {
      setElapsedSeconds(0);
      return;
    }
    setElapsedSeconds(0);
    const timer = window.setInterval(() => {
      setElapsedSeconds((s) => s + 1);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [active]);

  const resolvedPercent = useMemo(() => {
    if (typeof percent === "number") {
      return Math.max(0, Math.min(100, percent));
    }
    return stepPercent(steps);
  }, [percent, steps]);

  if (!active) {
    return null;
  }

  const indeterminate = resolvedPercent == null;
  const width = indeterminate ? undefined : `${resolvedPercent}%`;

  return (
    <div
      className={`ai-progress rounded-lg border border-indigo-200 bg-indigo-50/80 p-3 dark:border-indigo-800 dark:bg-indigo-950/40 ${className}`}
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <div className={`flex items-start gap-3 ${compact ? "" : ""}`}>
        <span
          className="ai-progress-spinner mt-0.5 inline-block h-5 w-5 shrink-0 rounded-full border-2 border-indigo-200 border-t-indigo-600 dark:border-indigo-700 dark:border-t-indigo-300"
          aria-hidden
        />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-indigo-950 dark:text-indigo-100">
            {title || t("title")}
          </p>
          <p className="mt-0.5 text-xs text-indigo-800/80 dark:text-indigo-200/80">
            {message || t("working")}
          </p>
          <p className="mt-1 text-xs text-indigo-700/70 dark:text-indigo-300/70">
            {t("elapsed", { seconds: elapsedSeconds })}
          </p>

          <div className="ai-progress-track mt-3 h-2 w-full overflow-hidden rounded-full bg-indigo-200/70 dark:bg-indigo-900">
            {indeterminate ? (
              <div className="ai-progress-indeterminate h-full w-1/3 rounded-full bg-indigo-600 dark:bg-indigo-400" />
            ) : (
              <div
                className="h-full rounded-full bg-indigo-600 transition-[width] duration-500 ease-out dark:bg-indigo-400"
                style={{ width }}
              />
            )}
          </div>

          {steps && steps.length > 0 && !compact ? (
            <ol className="mt-3 space-y-1.5">
              {steps.map((step) => (
                <li
                  key={step.id}
                  className="flex items-center gap-2 text-xs text-indigo-900/90 dark:text-indigo-100/90"
                >
                  <StepGlyph status={step.status} />
                  <span className="font-medium">{step.label}</span>
                  <span className="text-indigo-700/70 dark:text-indigo-300/70">
                    {t(`status.${step.status}`)}
                  </span>
                </li>
              ))}
            </ol>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function StepGlyph({ status }: { status: AiProgressStepStatus }) {
  if (status === "done") {
    return (
      <span className="inline-flex h-4 w-4 items-center justify-center rounded-full bg-emerald-500 text-[10px] text-white">
        ✓
      </span>
    );
  }
  if (status === "running") {
    return (
      <span className="ai-progress-spinner inline-block h-4 w-4 rounded-full border-2 border-indigo-200 border-t-indigo-600" />
    );
  }
  if (status === "error") {
    return (
      <span className="inline-flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] text-white">
        !
      </span>
    );
  }
  if (status === "skipped") {
    return <span className="inline-block h-4 w-4 rounded-full bg-slate-300 dark:bg-slate-600" />;
  }
  return <span className="inline-block h-4 w-4 rounded-full border border-indigo-300 dark:border-indigo-600" />;
}
