"use client";

import { useTranslations } from "next-intl";
import { useTourOptional } from "@/components/tour/TourProvider";

export default function TourFloatingControls() {
  const t = useTranslations("tour");
  const tour = useTourOptional();

  if (!tour?.hasPageTour || !tour.prefs.enabled || tour.prefs.dontShowAgain) {
    return null;
  }

  const {
    isRunning,
    pageCompleted,
    startTour,
    restartTour,
    exitTour,
    skipPageTour,
  } = tour;

  return (
    <div
      className="tour-floating-controls"
      role="region"
      aria-label={t("floatingLabel")}
    >
      <div className="tour-floating-controls-inner">
        <p className="tour-floating-controls-title">{t("floatingTitle")}</p>
        <div className="tour-floating-controls-actions">
          {isRunning ? (
            <button
              type="button"
              className="tour-floating-btn tour-floating-btn-exit"
              onClick={() => exitTour()}
            >
              {t("exit")}
            </button>
          ) : (
            <>
              <button
                type="button"
                className="tour-floating-btn tour-floating-btn-primary"
                onClick={() => (pageCompleted ? restartTour() : startTour())}
              >
                {pageCompleted ? t("restartPage") : t("start")}
              </button>
              {!pageCompleted ? (
                <button
                  type="button"
                  className="tour-floating-btn tour-floating-btn-ghost"
                  onClick={() => skipPageTour()}
                >
                  {t("skipPage")}
                </button>
              ) : null}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
