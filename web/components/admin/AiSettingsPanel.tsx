"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { apiJson } from "@/lib/api";

type SystemHealth = {
  ai_provider: string;
  ai_model: string;
  hermes: string;
};

function statusBadge(status: string, t: (key: string) => string) {
  const ok = status === "ok";
  return (
    <span
      className={`inline-flex rounded px-2 py-0.5 text-xs font-medium ${
        ok ? "bg-green-100 text-green-800" : "bg-amber-100 text-amber-800"
      }`}
    >
      {ok ? t("statusOk") : t("statusIssue")}
    </span>
  );
}

export default function AiSettingsPanel() {
  const t = useTranslations("admin.aiSettings");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<SystemHealth | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await apiJson<SystemHealth>("/admin/system/health");
        setHealth(data);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : t("loadError"));
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [t]);

  if (loading) {
    return <p className="text-sm text-gray-500">{t("loading")}</p>;
  }

  if (!health) {
    return (
      <p className="text-sm text-red-600" role="alert">
        {error || t("loadError")}
      </p>
    );
  }

  return (
    <div className="space-y-6">
      <p className="text-sm text-gray-600">{t("readOnlyNote")}</p>

      <dl className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-lg border border-gray-200 p-4">
          <dt className="text-sm font-medium text-gray-500">{t("provider")}</dt>
          <dd className="mt-1 text-lg font-semibold capitalize">{health.ai_provider}</dd>
        </div>
        <div className="rounded-lg border border-gray-200 p-4">
          <dt className="text-sm font-medium text-gray-500">{t("model")}</dt>
          <dd className="mt-1 text-lg font-semibold">{health.ai_model}</dd>
        </div>
        <div className="rounded-lg border border-gray-200 p-4 sm:col-span-2">
          <dt className="text-sm font-medium text-gray-500">{t("hermesHealth")}</dt>
          <dd className="mt-2">{statusBadge(health.hermes, t)}</dd>
        </div>
      </dl>
    </div>
  );
}
