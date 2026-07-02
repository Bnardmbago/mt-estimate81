"use client";

import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";

export type RateCardListItem = {
  id: string;
  name: string;
  is_active: boolean;
  is_system?: boolean;
  development_approach: string;
  estimate_count: number;
  is_locked: boolean;
};

type RateCardListProps = {
  cards: RateCardListItem[];
  loading?: boolean;
  currentCardId?: string;
};

const APPROACH_KEYS = ["traditional", "ai_assisted", "hybrid", "low_code"] as const;

export default function RateCardList({
  cards,
  loading = false,
  currentCardId,
}: RateCardListProps) {
  const locale = useLocale();
  const t = useTranslations("rateCards.allCardsList");
  const tRateCards = useTranslations("rateCards");

  function approachLabel(approach: string): string {
    if (APPROACH_KEYS.includes(approach as (typeof APPROACH_KEYS)[number])) {
      return tRateCards(`developmentApproachOptions.${approach}.label`);
    }
    return approach;
  }

  function statusLabel(card: RateCardListItem): string {
    if (card.is_active) {
      return t("statusActive");
    }
    if (card.is_locked) {
      return t("statusLocked");
    }
    return t("statusInactive");
  }

  function displayRateCardName(card: RateCardListItem): string {
    return card.is_system ? tRateCards("systemDefaultCardName") : card.name;
  }

  return (
    <section className="mt-10 border-t border-gray-200 pt-8">
      <h2 className="text-lg font-semibold text-gray-900">{t("title")}</h2>
      <p className="mt-1 text-sm text-gray-500">{t("description")}</p>

      {loading ? (
        <p className="mt-4 text-sm text-gray-500">{t("loading")}</p>
      ) : cards.length === 0 ? (
        <p className="mt-4 text-sm text-gray-500">{t("empty")}</p>
      ) : (
        <div className="mt-4 overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2.5 text-left font-medium text-gray-700">{t("name")}</th>
                <th className="px-4 py-2.5 text-left font-medium text-gray-700">
                  {t("developmentApproach")}
                </th>
                <th className="px-4 py-2.5 text-left font-medium text-gray-700">{t("status")}</th>
                <th className="px-4 py-2.5 text-right font-medium text-gray-700">
                  {t("estimates")}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {cards.map((card) => {
                const isCurrent = card.id === currentCardId;
                return (
                  <tr
                    key={card.id}
                    className={isCurrent ? "bg-indigo-50/60" : "hover:bg-gray-50"}
                  >
                    <td className="px-4 py-2.5">
                      <Link
                        href={`/${locale}/rate-cards/${card.id}`}
                        className="font-medium text-blue-600 hover:text-blue-800 hover:underline"
                      >
                        {displayRateCardName(card)}
                      </Link>
                    </td>
                    <td className="px-4 py-2.5 text-gray-700">
                      {approachLabel(card.development_approach)}
                    </td>
                    <td className="px-4 py-2.5">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                          card.is_active
                            ? "bg-green-100 text-green-800"
                            : card.is_locked
                              ? "bg-amber-100 text-amber-800"
                              : "bg-gray-100 text-gray-700"
                        }`}
                      >
                        {statusLabel(card)}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-right text-gray-700">
                      {t("estimateCount", { count: card.estimate_count })}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
