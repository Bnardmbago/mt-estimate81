"use client";

import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";

type EstimateRateCardPanelProps = {
  rateCardId: string | null;
  rateCardName: string | null;
  readOnly?: boolean;
};

export default function EstimateRateCardPanel({
  rateCardId,
  rateCardName,
  readOnly = false,
}: EstimateRateCardPanelProps) {
  const locale = useLocale();
  const t = useTranslations("review");
  const tPanel = useTranslations("review.rateCardPanel");

  return (
    <div className="mb-4 rounded-lg border border-gray-200 bg-gray-50 p-4">
      <h3 className="text-sm font-semibold text-gray-900">{tPanel("autoTitle")}</h3>
      <p className="mt-1 text-sm text-gray-600">{tPanel("autoDescription")}</p>

      {rateCardId && rateCardName ? (
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <p className="text-sm text-gray-800">
            {tPanel("selectedCard", { name: rateCardName })}
          </p>
          {!readOnly && (
            <Link
              href={`/${locale}/rate-cards/${rateCardId}`}
              className="rounded border border-blue-200 bg-white px-3 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-50"
            >
              {tPanel("editRateCard")}
            </Link>
          )}
        </div>
      ) : (
        <p className="mt-3 text-sm text-indigo-900">{tPanel("autoPending")}</p>
      )}

      {!readOnly && rateCardId && (
        <p className="mt-2 text-xs text-green-700">{tPanel("editableHint")}</p>
      )}

      {!readOnly && (
        <p className="mt-3 text-xs text-gray-500">{t("rateCardAutoRegenerateHint")}</p>
      )}
    </div>
  );
}
