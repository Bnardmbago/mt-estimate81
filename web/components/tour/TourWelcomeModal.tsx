"use client";

import { useTranslations } from "next-intl";
import type { TourAudience } from "@/lib/tourAudience";

type TourWelcomeModalProps = {
  open: boolean;
  audience: TourAudience | null;
  pageTitle?: string;
  pageBody?: string;
  onStart: () => void;
  onSkip: () => void;
  onDontShowAgain: () => void;
};

export default function TourWelcomeModal({
  open,
  audience,
  pageTitle,
  pageBody,
  onStart,
  onSkip,
  onDontShowAgain,
}: TourWelcomeModalProps) {
  const t = useTranslations("tour");

  if (!open || !audience) return null;

  const audienceLabel = t(`audience.${audience}`);

  return (
    <div
      className="fixed inset-0 z-[10000] flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="tour-welcome-title"
    >
      <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-700 dark:bg-gray-900">
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-400">
          {audienceLabel}
        </p>
        <h2
          id="tour-welcome-title"
          className="mt-2 text-xl font-semibold text-slate-900 dark:text-slate-50"
        >
          {pageTitle ?? t("welcomeTitle")}
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
          {pageBody ?? t(`welcomeBody.${audience}`)}
        </p>
        <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:flex-wrap">
          <button
            type="button"
            onClick={onStart}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            {t("start")}
          </button>
          <button
            type="button"
            onClick={onSkip}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            {t("skip")}
          </button>
          <button
            type="button"
            onClick={onDontShowAgain}
            className="rounded-lg px-4 py-2 text-sm font-medium text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
          >
            {t("dontShowAgain")}
          </button>
        </div>
      </div>
    </div>
  );
}
