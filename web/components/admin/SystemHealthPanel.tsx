"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { apiJson } from "@/lib/api";

type SystemHealth = {
  database: string;
  hermes: string;
  ai_provider: string;
  ai_model: string;
  openai_api_key_configured: boolean;
  anthropic_api_key_configured: boolean;
  stuck_extractions: number;
  storage_usage_bytes: number;
  app_version: string;
};

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function statusBadge(status: string, t: (key: string) => string) {
  const ok = status === "ok";
  return (
    <span
      className={`inline-flex rounded px-2 py-0.5 text-xs font-medium ${
        ok ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
      }`}
    >
      {ok ? t("statusOk") : status === "unreachable" ? t("statusUnreachable") : t("statusError")}
    </span>
  );
}

export default function SystemHealthPanel() {
  const t = useTranslations("admin.system");
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
      <dl className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-lg border border-gray-200 p-4">
          <dt className="text-sm font-medium text-gray-500">{t("database")}</dt>
          <dd className="mt-2">{statusBadge(health.database, t)}</dd>
        </div>
        <div className="rounded-lg border border-gray-200 p-4">
          <dt className="text-sm font-medium text-gray-500">{t("hermes")}</dt>
          <dd className="mt-2">{statusBadge(health.hermes, t)}</dd>
        </div>
        <div className="rounded-lg border border-gray-200 p-4">
          <dt className="text-sm font-medium text-gray-500">{t("appVersion")}</dt>
          <dd className="mt-1 text-lg font-semibold">{health.app_version}</dd>
        </div>
        <div className="rounded-lg border border-gray-200 p-4">
          <dt className="text-sm font-medium text-gray-500">{t("storageUsage")}</dt>
          <dd className="mt-1 text-lg font-semibold">{formatBytes(health.storage_usage_bytes)}</dd>
        </div>
        <div className="rounded-lg border border-gray-200 p-4 sm:col-span-2">
          <dt className="text-sm font-medium text-gray-500">{t("stuckExtractions")}</dt>
          <dd className="mt-1">
            <span
              className={`text-lg font-semibold ${
                health.stuck_extractions > 0 ? "text-red-600" : "text-green-600"
              }`}
            >
              {health.stuck_extractions}
            </span>
            {health.stuck_extractions > 0 && (
              <p className="mt-1 text-sm text-red-600">{t("stuckWarning")}</p>
            )}
          </dd>
        </div>
      </dl>

      <section className="rounded-lg border border-gray-200 p-4">
        <h3 className="mb-2 text-sm font-medium text-gray-500">{t("aiConfig")}</h3>
        <dl className="grid gap-2 text-sm text-gray-700 sm:grid-cols-2">
          <div>
            <dt className="font-medium text-gray-500">{t("provider")}</dt>
            <dd className="capitalize">{health.ai_provider}</dd>
          </div>
          <div>
            <dt className="font-medium text-gray-500">{t("model")}</dt>
            <dd>{health.ai_model}</dd>
          </div>
          <div>
            <dt className="font-medium text-gray-500">{t("openaiCredentials")}</dt>
            <dd>{health.openai_api_key_configured ? t("configured") : t("notConfigured")}</dd>
          </div>
          <div>
            <dt className="font-medium text-gray-500">{t("anthropicCredentials")}</dt>
            <dd>{health.anthropic_api_key_configured ? t("configured") : t("notConfigured")}</dd>
          </div>
        </dl>
      </section>
    </div>
  );
}
