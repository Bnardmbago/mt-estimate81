"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import {
  fetchInternalDossier,
  type InternalDossier,
} from "@/lib/internal-dossier";

type InternalDossierClientProps = {
  estimateId: string;
  locale: string;
};

export default function InternalDossierClient({
  estimateId,
  locale,
}: InternalDossierClientProps) {
  const t = useTranslations("internalDossier");
  const [dossier, setDossier] = useState<InternalDossier | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchInternalDossier(estimateId)
      .then((data) => {
        if (!cancelled) {
          setDossier(data);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : t("loadError"));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [estimateId, t]);

  return (
    <div className="space-y-4">
      <div>
        <Link
          href={`/${locale}/estimates/${estimateId}`}
          className="mb-2 inline-block text-sm text-gray-500 hover:text-blue-600 dark:text-gray-400 dark:hover:text-blue-400"
        >
          ← {t("backToEstimate")}
        </Link>
        <h1 className="text-2xl font-semibold">{t("title")}</h1>
      </div>

      <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
        {t("banner")}
      </div>

      {loading ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">{t("loading")}</p>
      ) : error ? (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : dossier ? (
        <div className="rounded-lg border border-gray-200 bg-white p-4 text-sm text-gray-700 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200">
          <p className="font-medium">{dossier.project_name}</p>
          <p className="text-gray-500 dark:text-gray-400">{dossier.client_name}</p>
        </div>
      ) : null}
    </div>
  );
}
