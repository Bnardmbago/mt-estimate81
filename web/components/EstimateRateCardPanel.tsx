"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { apiJson } from "@/lib/api";

export type ComplexityProfile = {
  level: "low" | "medium" | "high";
  overall_score: number;
  drivers?: string[];
};

type EstimateRateCardPanelProps = {
  estimateId?: string;
  rateCardId: string | null;
  rateCardName: string | null;
  complexityProfile?: ComplexityProfile | null;
  rateCardAutoTuned?: boolean;
  rateCardTuneRecommended?: boolean;
  rateCardAutoTuneEnabled?: boolean;
  readOnly?: boolean;
};

function complexityBadgeClass(level: ComplexityProfile["level"]): string {
  if (level === "high") {
    return "bg-red-100 text-red-800";
  }
  if (level === "medium") {
    return "bg-amber-100 text-amber-900";
  }
  return "bg-green-100 text-green-800";
}

export default function EstimateRateCardPanel({
  estimateId,
  rateCardId,
  rateCardName,
  complexityProfile = null,
  rateCardAutoTuned = false,
  rateCardTuneRecommended = false,
  rateCardAutoTuneEnabled = true,
  readOnly = false,
}: EstimateRateCardPanelProps) {
  const locale = useLocale();
  const router = useRouter();
  const t = useTranslations("review");
  const tPanel = useTranslations("review.rateCardPanel");
  const [tuning, setTuning] = useState(false);
  const [tuneError, setTuneError] = useState<string | null>(null);

  async function handleGenerateFromExtraction() {
    if (!estimateId) {
      return;
    }
    setTuning(true);
    setTuneError(null);
    try {
      const generated = await apiJson<{
        name: string;
        settings: Record<string, unknown>;
      }>(`/estimates/${estimateId}/rate-card/generate`, { method: "POST" });
      await apiJson(`/estimates/${estimateId}/rate-card`, {
        method: "POST",
        body: JSON.stringify({
          name: generated.name,
          settings: generated.settings,
          activate: false,
        }),
      });
      router.refresh();
    } catch (error) {
      setTuneError(error instanceof Error ? error.message : tPanel("generateError"));
    } finally {
      setTuning(false);
    }
  }

  async function handleTuneFromExtraction() {
    if (!estimateId) {
      return;
    }
    setTuning(true);
    setTuneError(null);
    try {
      await apiJson(`/estimates/${estimateId}/rate-card/tune-from-extraction`, {
        method: "POST",
      });
      router.refresh();
    } catch (error) {
      setTuneError(error instanceof Error ? error.message : tPanel("tuneError"));
    } finally {
      setTuning(false);
    }
  }

  return (
    <div className="mb-4 rounded-lg border border-gray-200 bg-gray-50 p-4" data-tour="estimate-rate-card-panel">
      <h3 className="text-sm font-semibold text-gray-900">{tPanel("autoTitle")}</h3>
      <p className="mt-1 text-sm text-gray-600">{tPanel("autoDescription")}</p>

      {complexityProfile ? (
        <div className="mt-3 rounded-md border border-gray-200 bg-white p-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-gray-800">{tPanel("complexityTitle")}</span>
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-semibold uppercase ${complexityBadgeClass(complexityProfile.level)}`}
            >
              {tPanel(`complexityLevel.${complexityProfile.level}`)}
            </span>
            <span className="text-xs text-gray-500">
              {tPanel("complexityScore", { score: Math.round(complexityProfile.overall_score) })}
            </span>
          </div>
          {complexityProfile.drivers && complexityProfile.drivers.length > 0 ? (
            <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-gray-600">
              {complexityProfile.drivers.slice(0, 4).map((driver) => (
                <li key={driver}>{driver}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

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

      {rateCardAutoTuned ? (
        <p className="mt-2 text-xs text-green-700">{tPanel("autoTunedHint")}</p>
      ) : null}

      {rateCardTuneRecommended && !readOnly && estimateId ? (
        <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 p-3">
          <p className="text-sm text-amber-950">{tPanel("tuneRecommendedDescription")}</p>
          {tuneError ? (
            <p className="mt-2 text-sm text-red-700" role="alert">
              {tuneError}
            </p>
          ) : null}
          <button
            type="button"
            onClick={() =>
              void (rateCardAutoTuneEnabled
                ? handleTuneFromExtraction()
                : handleGenerateFromExtraction())
            }
            disabled={tuning}
            className="mt-2 rounded bg-amber-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-800 disabled:opacity-50"
          >
            {tuning
              ? tPanel("tuningFromExtraction")
              : rateCardAutoTuneEnabled
                ? tPanel("tuneFromExtraction")
                : tPanel("generateFromExtraction")}
          </button>
        </div>
      ) : null}

      {!readOnly && rateCardId && (
        <p className="mt-2 text-xs text-green-700">{tPanel("editableHint")}</p>
      )}

      {!readOnly && (
        <p className="mt-3 text-xs text-gray-500">{t("rateCardAutoRegenerateHint")}</p>
      )}
    </div>
  );
}
