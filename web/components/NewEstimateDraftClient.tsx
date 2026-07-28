"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import EstimateForm from "@/components/EstimateForm";
import type { EstimateDetail } from "@/lib/estimate";
import { fetchFormTemplate } from "@/lib/form-template";
import { buildLocalEstimateDraft } from "@/lib/local-estimate-draft";

type NewEstimateDraftClientProps = {
  templateId: string;
  isAdmin?: boolean;
};

export default function NewEstimateDraftClient({
  templateId,
  isAdmin = false,
}: NewEstimateDraftClientProps) {
  const locale = useLocale();
  const t = useTranslations("estimates");
  const [estimate, setEstimate] = useState<EstimateDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const template = await fetchFormTemplate(templateId, locale);
        if (cancelled) {
          return;
        }
        setEstimate(buildLocalEstimateDraft(template, locale));
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : t("createError"));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [locale, t, templateId]);

  if (loading) {
    return <p className="text-sm text-gray-500">{t("draftLoading")}</p>;
  }

  if (error || !estimate) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-red-800">
        <h1 className="text-lg font-semibold">{t("createError")}</h1>
        {error ? <p className="mt-2 text-sm">{error}</p> : null}
        <Link
          href={`/${locale}/estimates/new`}
          className="mt-4 inline-block text-sm font-medium text-blue-600 hover:underline"
        >
          ← {t("back")}
        </Link>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <p className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
        {t("draftNotSavedHint")}
      </p>
      <EstimateForm estimate={estimate} isLocalDraft isAdmin={isAdmin} />
    </div>
  );
}
