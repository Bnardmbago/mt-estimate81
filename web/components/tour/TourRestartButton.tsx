"use client";

import { useTranslations } from "next-intl";
import { useTourOptional } from "@/components/tour/TourProvider";

type TourRestartButtonProps = {
  dataTour?: string;
  className?: string;
};

export default function TourRestartButton({
  dataTour = "help-restart-tour",
  className,
}: TourRestartButtonProps) {
  const t = useTranslations("tour");
  const tour = useTourOptional();

  if (!tour?.audience) return null;

  return (
    <button
      type="button"
      data-tour={dataTour}
      disabled={tour.isRunning}
      onClick={() => tour.restartTour()}
      className={
        className ??
        "rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
      }
    >
      {t("restart")}
    </button>
  );
}
