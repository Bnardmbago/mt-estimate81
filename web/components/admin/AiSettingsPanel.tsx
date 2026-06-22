"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { apiJson } from "@/lib/api";

type AISettings = {
  ai_provider: "openai" | "anthropic";
  ai_model: string;
  openai_api_key_configured: boolean;
  openai_api_key_hint: string | null;
  anthropic_api_key_configured: boolean;
  anthropic_api_key_hint: string | null;
  openai_models: string[];
  anthropic_models: string[];
  hermes: string;
};

type ConnectionTestResult = {
  success: boolean;
  message: string;
};

const inputClassName =
  "w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

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

function ConnectionTestMessage({
  result,
  t,
}: {
  result: ConnectionTestResult | null;
  t: (key: string, values?: Record<string, string>) => string;
}) {
  if (!result) return null;

  return (
    <p
      className={`mt-2 text-sm ${result.success ? "text-green-700" : "text-red-600"}`}
      role="status"
    >
      {result.success
        ? t("testSuccess")
        : t("testFailed", { message: result.message })}
    </p>
  );
}

export default function AiSettingsPanel() {
  const t = useTranslations("admin.aiSettings");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [settings, setSettings] = useState<AISettings | null>(null);
  const [provider, setProvider] = useState<"openai" | "anthropic">("openai");
  const [model, setModel] = useState("");
  const [openaiApiKey, setOpenaiApiKey] = useState("");
  const [anthropicApiKey, setAnthropicApiKey] = useState("");
  const [testingOpenai, setTestingOpenai] = useState(false);
  const [testingAnthropic, setTestingAnthropic] = useState(false);
  const [openaiTestResult, setOpenaiTestResult] = useState<ConnectionTestResult | null>(null);
  const [anthropicTestResult, setAnthropicTestResult] = useState<ConnectionTestResult | null>(
    null,
  );

  useEffect(() => {
    async function load() {
      try {
        const data = await apiJson<AISettings>("/admin/ai-settings");
        setSettings(data);
        setProvider(data.ai_provider);
        setModel(data.ai_model);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : t("loadError"));
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [t]);

  const modelOptions =
    provider === "anthropic"
      ? settings?.anthropic_models ?? []
      : settings?.openai_models ?? [];

  const anthropicModelForTest =
    provider === "anthropic"
      ? model
      : settings?.anthropic_models.includes("claude-haiku-4-5")
        ? "claude-haiku-4-5"
        : settings?.anthropic_models[0] ?? "";

  async function handleTestConnection(target: "openai" | "anthropic") {
    if (!settings) return;

    const isOpenai = target === "openai";
    const typedKey = isOpenai ? openaiApiKey.trim() : anthropicApiKey.trim();
    const configured = isOpenai
      ? settings.openai_api_key_configured
      : settings.anthropic_api_key_configured;

    if (!typedKey && !configured) {
      const result = { success: false, message: t("testNoKey") };
      if (isOpenai) {
        setOpenaiTestResult(result);
      } else {
        setAnthropicTestResult(result);
      }
      return;
    }

    if (isOpenai) {
      setTestingOpenai(true);
      setOpenaiTestResult(null);
    } else {
      setTestingAnthropic(true);
      setAnthropicTestResult(null);
    }

    try {
      const payload: Record<string, string> = { provider: target };
      if (typedKey) {
        payload.api_key = typedKey;
      }
      if (!isOpenai) {
        payload.model = anthropicModelForTest;
      }

      const result = await apiJson<ConnectionTestResult & { provider: string }>(
        "/admin/ai-settings/test-connection",
        {
          method: "POST",
          body: JSON.stringify(payload),
        },
      );

      const testResult = { success: result.success, message: result.message };
      if (isOpenai) {
        setOpenaiTestResult(testResult);
      } else {
        setAnthropicTestResult(testResult);
      }
    } catch (testError) {
      const testResult = {
        success: false,
        message: testError instanceof Error ? testError.message : t("testError"),
      };
      if (isOpenai) {
        setOpenaiTestResult(testResult);
      } else {
        setAnthropicTestResult(testResult);
      }
    } finally {
      if (isOpenai) {
        setTestingOpenai(false);
      } else {
        setTestingAnthropic(false);
      }
    }
  }

  async function handleSave(event: React.FormEvent) {
    event.preventDefault();
    if (!settings) return;

    setSaving(true);
    setError(null);
    setSaved(false);

    const payload: Record<string, string | boolean> = {
      ai_provider: provider,
      ai_model: model,
    };

    if (openaiApiKey.trim()) {
      payload.openai_api_key = openaiApiKey.trim();
    }
    if (anthropicApiKey.trim()) {
      payload.anthropic_api_key = anthropicApiKey.trim();
    }

    try {
      const data = await apiJson<AISettings>("/admin/ai-settings", {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      setSettings(data);
      setProvider(data.ai_provider);
      setModel(data.ai_model);
      setOpenaiApiKey("");
      setAnthropicApiKey("");
      setOpenaiTestResult(null);
      setAnthropicTestResult(null);
      setSaved(true);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : t("saveError"));
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <p className="text-sm text-gray-500">{t("loading")}</p>;
  }

  if (!settings) {
    return (
      <p className="text-sm text-red-600" role="alert">
        {error || t("loadError")}
      </p>
    );
  }

  return (
    <form className="space-y-6" onSubmit={handleSave}>
      <p className="text-sm text-gray-600">{t("description")}</p>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-gray-700">{t("provider")}</span>
          <select
            value={provider}
            onChange={(event) => {
              const nextProvider = event.target.value as "openai" | "anthropic";
              setProvider(nextProvider);
              const nextModels =
                nextProvider === "anthropic" ? settings.anthropic_models : settings.openai_models;
              if (!nextModels.includes(model)) {
                setModel(nextModels[0] ?? "");
              }
            }}
            className={inputClassName}
          >
            <option value="openai">{t("providerOpenai")}</option>
            <option value="anthropic">{t("providerAnthropic")}</option>
          </select>
        </label>

        <label className="block text-sm">
          <span className="mb-1 block font-medium text-gray-700">{t("model")}</span>
          <select
            value={model}
            onChange={(event) => setModel(event.target.value)}
            className={inputClassName}
          >
            {modelOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="block text-sm">
          <label className="mb-1 block font-medium text-gray-700">{t("openaiApiKey")}</label>
          <input
            type="password"
            value={openaiApiKey}
            onChange={(event) => {
              setOpenaiApiKey(event.target.value);
              setOpenaiTestResult(null);
            }}
            placeholder={t("apiKeyPlaceholder")}
            className={inputClassName}
            autoComplete="off"
          />
          <span className="mt-1 block text-xs text-gray-500">
            {settings.openai_api_key_configured
              ? t("apiKeyConfigured", { hint: settings.openai_api_key_hint ?? "****" })
              : t("apiKeyNotConfigured")}
          </span>
          <button
            type="button"
            onClick={() => void handleTestConnection("openai")}
            disabled={testingOpenai}
            className="mt-2 rounded border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            {testingOpenai ? t("testing") : t("testConnection")}
          </button>
          <ConnectionTestMessage result={openaiTestResult} t={t} />
        </div>

        <div className="block text-sm">
          <label className="mb-1 block font-medium text-gray-700">{t("anthropicApiKey")}</label>
          <input
            type="password"
            value={anthropicApiKey}
            onChange={(event) => {
              setAnthropicApiKey(event.target.value);
              setAnthropicTestResult(null);
            }}
            placeholder={t("apiKeyPlaceholder")}
            className={inputClassName}
            autoComplete="off"
          />
          <span className="mt-1 block text-xs text-gray-500">
            {settings.anthropic_api_key_configured
              ? t("apiKeyConfigured", { hint: settings.anthropic_api_key_hint ?? "****" })
              : t("apiKeyNotConfigured")}
          </span>
          <button
            type="button"
            onClick={() => void handleTestConnection("anthropic")}
            disabled={testingAnthropic}
            className="mt-2 rounded border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            {testingAnthropic ? t("testing") : t("testConnection")}
          </button>
          <ConnectionTestMessage result={anthropicTestResult} t={t} />
        </div>
      </div>

      <div className="rounded-lg border border-gray-200 p-4">
        <dt className="text-sm font-medium text-gray-500">{t("hermesHealth")}</dt>
        <dd className="mt-2">{statusBadge(settings.hermes, t)}</dd>
      </div>

      {error && (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      )}
      {saved && <p className="text-sm text-green-600">{t("saved")}</p>}

      <button
        type="submit"
        disabled={saving}
        className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {saving ? t("saving") : t("save")}
      </button>
    </form>
  );
}
