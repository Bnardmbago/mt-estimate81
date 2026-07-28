"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { apiFetch, apiJson } from "@/lib/api";

type ConnectionStatus = {
  provider: string;
  connected: boolean;
  configured: boolean;
};

export default function ConnectedAccountsPanel() {
  const t = useTranslations("settings.connectedAccounts");
  const searchParams = useSearchParams();
  const [rows, setRows] = useState<ConnectionStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busyProvider, setBusyProvider] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiJson<ConnectionStatus[]>("/integrations/status");
      setRows(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("loadError"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const oauth = searchParams.get("oauth");
    const provider = searchParams.get("provider");
    if (oauth === "ok" && provider) {
      setMessage(t("connectSuccess", { provider }));
      void load();
    } else if (oauth === "error" && provider) {
      setError(t("connectError", { provider }));
    }
  }, [searchParams, t, load]);

  async function connect(provider: "google" | "canva") {
    setBusyProvider(provider);
    setError(null);
    try {
      const data = await apiJson<{ authorize_url: string }>(
        `/integrations/${provider}/connect`,
      );
      window.location.href = data.authorize_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : t("connectError", { provider }));
      setBusyProvider(null);
    }
  }

  async function disconnect(provider: "google" | "canva") {
    setBusyProvider(provider);
    setError(null);
    try {
      const response = await apiFetch(`/integrations/${provider}`, {
        method: "DELETE",
      });
      if (!response.ok && response.status !== 204) {
        throw new Error(t("disconnectError", { provider }));
      }
      setMessage(t("disconnectSuccess", { provider }));
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("disconnectError", { provider }));
    } finally {
      setBusyProvider(null);
    }
  }

  return (
    <section className="space-y-3">
      <div>
        <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
          {t("title")}
        </h2>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{t("description")}</p>
      </div>

      {loading ? <p className="text-sm text-slate-500">{t("loading")}</p> : null}
      {error ? (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : null}
      {message ? (
        <p className="text-sm text-emerald-700 dark:text-emerald-300" role="status">
          {message}
        </p>
      ) : null}

      <ul className="divide-y divide-slate-200 rounded-md border border-slate-200 dark:divide-slate-700 dark:border-slate-700">
        {(["google", "canva"] as const).map((provider) => {
          const row = rows.find((r) => r.provider === provider);
          const connected = row?.connected ?? false;
          const configured = row?.configured ?? false;
          return (
            <li
              key={provider}
              className="flex flex-wrap items-center justify-between gap-3 px-4 py-3"
            >
              <div>
                <p className="font-medium text-slate-800 dark:text-slate-100">
                  {t(`providers.${provider}`)}
                </p>
                <p className="text-xs text-slate-500">
                  {!configured
                    ? t("notConfigured")
                    : connected
                      ? t("connected")
                      : t("notConnected")}
                </p>
              </div>
              <div className="flex gap-2">
                {connected ? (
                  <button
                    type="button"
                    disabled={busyProvider === provider}
                    onClick={() => void disconnect(provider)}
                    className="rounded border border-slate-300 px-3 py-1.5 text-sm disabled:opacity-50 dark:border-slate-600"
                  >
                    {t("disconnect")}
                  </button>
                ) : (
                  <button
                    type="button"
                    disabled={!configured || busyProvider === provider}
                    onClick={() => void connect(provider)}
                    className="rounded bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
                  >
                    {t("connect")}
                  </button>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
