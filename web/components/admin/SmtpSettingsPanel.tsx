"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import PasswordField from "@/components/PasswordField";
import { apiJson } from "@/lib/api";

type SMTPSettings = {
  smtp_host: string;
  smtp_port: number;
  smtp_user: string;
  smtp_from: string;
  smtp_use_tls: boolean;
  smtp_password_configured: boolean;
  smtp_password_hint: string | null;
  smtp_configured: boolean;
  env_fallback: boolean;
};

type ConnectionTestResult = {
  success: boolean;
  message: string;
};

const inputClassName =
  "w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

export default function SmtpSettingsPanel() {
  const t = useTranslations("admin.smtpSettings");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [settings, setSettings] = useState<SMTPSettings | null>(null);
  const [smtpHost, setSmtpHost] = useState("");
  const [smtpPort, setSmtpPort] = useState("587");
  const [smtpUser, setSmtpUser] = useState("");
  const [smtpPassword, setSmtpPassword] = useState("");
  const [smtpFrom, setSmtpFrom] = useState("");
  const [smtpUseTls, setSmtpUseTls] = useState(true);
  const [testResult, setTestResult] = useState<ConnectionTestResult | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await apiJson<SMTPSettings>("/admin/smtp-settings");
        setSettings(data);
        setSmtpHost(data.smtp_host);
        setSmtpPort(String(data.smtp_port));
        setSmtpUser(data.smtp_user);
        setSmtpFrom(data.smtp_from);
        setSmtpUseTls(data.smtp_use_tls);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : t("loadError"));
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [t]);

  async function handleTestConnection() {
    setTesting(true);
    setTestResult(null);

    const payload: Record<string, string | boolean | number> = {
      smtp_host: smtpHost.trim(),
      smtp_port: Number(smtpPort),
      smtp_user: smtpUser.trim(),
      smtp_from: smtpFrom.trim(),
      smtp_use_tls: smtpUseTls,
    };

    if (smtpPassword.trim()) {
      payload.smtp_password = smtpPassword.trim();
    }

    try {
      const result = await apiJson<ConnectionTestResult>("/admin/smtp-settings/test-connection", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setTestResult(result);
    } catch (testError) {
      setTestResult({
        success: false,
        message: testError instanceof Error ? testError.message : t("testError"),
      });
    } finally {
      setTesting(false);
    }
  }

  async function handleSave(event: React.FormEvent) {
    event.preventDefault();
    if (!settings) return;

    setSaving(true);
    setError(null);
    setSaved(false);

    const payload: Record<string, string | boolean | number> = {
      smtp_host: smtpHost.trim(),
      smtp_port: Number(smtpPort),
      smtp_user: smtpUser.trim(),
      smtp_from: smtpFrom.trim(),
      smtp_use_tls: smtpUseTls,
    };

    if (smtpPassword.trim()) {
      payload.smtp_password = smtpPassword.trim();
    }

    try {
      const data = await apiJson<SMTPSettings>("/admin/smtp-settings", {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      setSettings(data);
      setSmtpHost(data.smtp_host);
      setSmtpPort(String(data.smtp_port));
      setSmtpUser(data.smtp_user);
      setSmtpFrom(data.smtp_from);
      setSmtpUseTls(data.smtp_use_tls);
      setSmtpPassword("");
      setTestResult(null);
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
      {settings.env_fallback && (
        <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
          {t("envFallbackHint")}
        </p>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-gray-700">{t("smtpHost")}</span>
          <input
            type="text"
            value={smtpHost}
            onChange={(event) => {
              setSmtpHost(event.target.value);
              setTestResult(null);
            }}
            placeholder="smtp.example.com"
            className={inputClassName}
            autoComplete="off"
          />
        </label>

        <label className="block text-sm">
          <span className="mb-1 block font-medium text-gray-700">{t("smtpPort")}</span>
          <input
            type="number"
            min={1}
            max={65535}
            value={smtpPort}
            onChange={(event) => {
              setSmtpPort(event.target.value);
              setTestResult(null);
            }}
            className={inputClassName}
          />
        </label>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-gray-700">{t("smtpUser")}</span>
          <input
            type="text"
            value={smtpUser}
            onChange={(event) => {
              setSmtpUser(event.target.value);
              setTestResult(null);
            }}
            className={inputClassName}
            autoComplete="off"
          />
        </label>

        <div className="block text-sm">
          <label className="mb-1 block font-medium text-gray-700">{t("smtpPassword")}</label>
          <PasswordField
            value={smtpPassword}
            onChange={(event) => {
              setSmtpPassword(event.target.value);
              setTestResult(null);
            }}
            placeholder={t("passwordPlaceholder")}
            className={inputClassName}
            autoComplete="off"
          />
          <span className="mt-1 block text-xs text-gray-500">
            {settings.smtp_password_configured
              ? t("passwordConfigured", { hint: settings.smtp_password_hint ?? "****" })
              : t("passwordNotConfigured")}
          </span>
        </div>
      </div>

      <label className="block text-sm">
        <span className="mb-1 block font-medium text-gray-700">{t("smtpFrom")}</span>
        <input
          type="email"
          value={smtpFrom}
          onChange={(event) => {
            setSmtpFrom(event.target.value);
            setTestResult(null);
          }}
          placeholder="estimates@yourcompany.com"
          className={inputClassName}
          autoComplete="off"
        />
      </label>

      <label className="flex items-center gap-2 text-sm text-gray-700">
        <input
          type="checkbox"
          checked={smtpUseTls}
          onChange={(event) => {
            setSmtpUseTls(event.target.checked);
            setTestResult(null);
          }}
          className="rounded border-gray-300"
        />
        {t("smtpUseTls")}
      </label>

      <div className="rounded-lg border border-gray-200 p-4">
        <dt className="text-sm font-medium text-gray-500">{t("configuredStatus")}</dt>
        <dd className="mt-2">
          <span
            className={`inline-flex rounded px-2 py-0.5 text-xs font-medium ${
              settings.smtp_configured
                ? "bg-green-100 text-green-800"
                : "bg-amber-100 text-amber-800"
            }`}
          >
            {settings.smtp_configured ? t("statusConfigured") : t("statusNotConfigured")}
          </span>
        </dd>
      </div>

      <button
        type="button"
        onClick={() => void handleTestConnection()}
        disabled={testing || !smtpHost.trim()}
        className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
      >
        {testing ? t("testing") : t("testConnection")}
      </button>

      {testResult && (
        <p
          className={`text-sm ${testResult.success ? "text-green-700" : "text-red-600"}`}
          role="status"
        >
          {testResult.success
            ? t("testSuccess")
            : t("testFailed", { message: testResult.message })}
        </p>
      )}

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
