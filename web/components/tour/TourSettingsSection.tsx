"use client";

import { useTranslations } from "next-intl";
import { useTourOptional } from "@/components/tour/TourProvider";

export default function TourSettingsSection() {
  const t = useTranslations("tour");
  const tour = useTourOptional();

  if (!tour?.audience) return null;

  const { audience, pageId, prefs, setEnabled, restartTour, resetAllTours, isRunning } = tour;
  const audienceLabel = t(`audience.${audience}`);

  return (
    <section
      data-tour="settings-tour-section"
      className="space-y-3 rounded-lg border border-slate-200 p-4 dark:border-slate-700"
    >
      <h2 className="text-base font-semibold">{t("settingsTitle")}</h2>
      <p className="text-sm text-slate-600 dark:text-slate-300">
        {t("settingsDescription", { audience: audienceLabel })}
      </p>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={prefs.enabled}
          onChange={(e) => setEnabled(e.target.checked)}
        />
        {t("enableToggle")}
      </label>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          data-tour="settings-restart-tour"
          disabled={isRunning || !pageId}
          onClick={() => restartTour()}
          className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {t("restartPage")}
        </button>
        <button
          type="button"
          disabled={isRunning}
          onClick={() => resetAllTours()}
          className="rounded border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800 disabled:opacity-50"
        >
          {t("resetAllPages")}
        </button>
      </div>
    </section>
  );
}
