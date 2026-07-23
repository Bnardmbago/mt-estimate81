"use client";

import { useTranslations } from "next-intl";

type ProposalStaleBannerProps = {
  onRefresh: () => void;
  onDismiss: () => void;
  refreshing?: boolean;
};

export default function ProposalStaleBanner({
  onRefresh,
  onDismiss,
  refreshing,
}: ProposalStaleBannerProps) {
  const t = useTranslations("proposal");
  return (
    <div
      role="status"
      className="mb-4 flex flex-col gap-3 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-100 print:hidden sm:flex-row sm:items-center sm:justify-between"
    >
      <div>
        <p className="font-semibold">{t("staleTitle")}</p>
        <p className="mt-1">{t("staleBody")}</p>
      </div>
      <div className="flex shrink-0 gap-2">
        <button
          type="button"
          className="rounded bg-amber-800 px-3 py-1.5 text-white disabled:opacity-50"
          disabled={refreshing}
          onClick={onRefresh}
        >
          {refreshing ? t("refreshing") : t("refreshFromEstimate")}
        </button>
        <button
          type="button"
          className="rounded border border-amber-400 px-3 py-1.5"
          onClick={onDismiss}
        >
          {t("dismiss")}
        </button>
      </div>
    </div>
  );
}
