"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import PasswordField from "@/components/PasswordField";
import { apiJson } from "@/lib/api";

type OAuthAppSettings = {
  google_oauth_client_id: string;
  google_oauth_redirect_uri: string;
  google_oauth_client_secret_configured: boolean;
  google_oauth_client_secret_hint: string | null;
  google_configured: boolean;
  canva_client_id: string;
  canva_redirect_uri: string;
  canva_client_secret_configured: boolean;
  canva_client_secret_hint: string | null;
  canva_configured: boolean;
  canva_template_proposal_en: string;
  canva_template_proposal_ja: string;
  canva_template_poc_en: string;
  canva_template_poc_ja: string;
};

const inputClassName =
  "w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-950";

export default function OAuthAppSettingsPanel() {
  const t = useTranslations("admin.oauthApps");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [settings, setSettings] = useState<OAuthAppSettings | null>(null);

  const [googleClientId, setGoogleClientId] = useState("");
  const [googleSecret, setGoogleSecret] = useState("");
  const [googleRedirect, setGoogleRedirect] = useState("");
  const [canvaClientId, setCanvaClientId] = useState("");
  const [canvaSecret, setCanvaSecret] = useState("");
  const [canvaRedirect, setCanvaRedirect] = useState("");
  const [tplProposalEn, setTplProposalEn] = useState("");
  const [tplProposalJa, setTplProposalJa] = useState("");
  const [tplPocEn, setTplPocEn] = useState("");
  const [tplPocJa, setTplPocJa] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const data = await apiJson<OAuthAppSettings>("/admin/oauth-app-settings");
        setSettings(data);
        setGoogleClientId(data.google_oauth_client_id);
        setGoogleRedirect(data.google_oauth_redirect_uri);
        setCanvaClientId(data.canva_client_id);
        setCanvaRedirect(data.canva_redirect_uri);
        setTplProposalEn(data.canva_template_proposal_en);
        setTplProposalJa(data.canva_template_proposal_ja);
        setTplPocEn(data.canva_template_poc_en);
        setTplPocJa(data.canva_template_poc_ja);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : t("loadError"));
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [t]);

  async function handleSave(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setSaved(false);
    const payload: Record<string, string | boolean> = {
      google_oauth_client_id: googleClientId.trim(),
      google_oauth_redirect_uri: googleRedirect.trim(),
      canva_client_id: canvaClientId.trim(),
      canva_redirect_uri: canvaRedirect.trim(),
      canva_template_proposal_en: tplProposalEn.trim(),
      canva_template_proposal_ja: tplProposalJa.trim(),
      canva_template_poc_en: tplPocEn.trim(),
      canva_template_poc_ja: tplPocJa.trim(),
    };
    if (googleSecret.trim()) payload.google_oauth_client_secret = googleSecret.trim();
    if (canvaSecret.trim()) payload.canva_client_secret = canvaSecret.trim();

    try {
      const data = await apiJson<OAuthAppSettings>("/admin/oauth-app-settings", {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      setSettings(data);
      setGoogleSecret("");
      setCanvaSecret("");
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

  return (
    <section className="max-w-2xl space-y-4">
      <div>
        <h2 className="text-lg font-semibold">{t("title")}</h2>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">{t("description")}</p>
      </div>

      {error ? (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : null}
      {saved ? (
        <p className="text-sm text-emerald-700" role="status">
          {t("saved")}
        </p>
      ) : null}

      <form onSubmit={(e) => void handleSave(e)} className="space-y-6">
        <fieldset className="space-y-3 rounded border border-gray-200 p-4 dark:border-gray-700">
          <legend className="px-1 text-sm font-semibold">{t("googleTitle")}</legend>
          <p className="text-xs text-gray-500">
            {settings?.google_configured ? t("googleConfigured") : t("googleNotConfigured")}
            {settings?.google_oauth_client_secret_hint
              ? ` · ${t("secretHint")}: ${settings.google_oauth_client_secret_hint}`
              : null}
          </p>
          <label className="block text-sm">
            <span className="mb-1 block font-medium">{t("clientId")}</span>
            <input
              className={inputClassName}
              value={googleClientId}
              onChange={(e) => setGoogleClientId(e.target.value)}
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium">{t("clientSecret")}</span>
            <PasswordField
              value={googleSecret}
              onChange={(event) => setGoogleSecret(event.target.value)}
              placeholder={
                settings?.google_oauth_client_secret_configured
                  ? t("secretLeaveBlank")
                  : undefined
              }
              className={inputClassName}
              autoComplete="off"
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium">{t("redirectUri")}</span>
            <input
              className={inputClassName}
              value={googleRedirect}
              onChange={(e) => setGoogleRedirect(e.target.value)}
            />
          </label>
        </fieldset>

        <fieldset className="space-y-3 rounded border border-gray-200 p-4 dark:border-gray-700">
          <legend className="px-1 text-sm font-semibold">{t("canvaTitle")}</legend>
          <p className="text-xs text-gray-500">
            {settings?.canva_configured ? t("canvaConfigured") : t("canvaNotConfigured")}
            {settings?.canva_client_secret_hint
              ? ` · ${t("secretHint")}: ${settings.canva_client_secret_hint}`
              : null}
          </p>
          <label className="block text-sm">
            <span className="mb-1 block font-medium">{t("clientId")}</span>
            <input
              className={inputClassName}
              value={canvaClientId}
              onChange={(e) => setCanvaClientId(e.target.value)}
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium">{t("clientSecret")}</span>
            <PasswordField
              value={canvaSecret}
              onChange={(event) => setCanvaSecret(event.target.value)}
              placeholder={
                settings?.canva_client_secret_configured ? t("secretLeaveBlank") : undefined
              }
              className={inputClassName}
              autoComplete="off"
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium">{t("redirectUri")}</span>
            <input
              className={inputClassName}
              value={canvaRedirect}
              onChange={(e) => setCanvaRedirect(e.target.value)}
            />
          </label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="mb-1 block font-medium">{t("templateProposalEn")}</span>
              <input
                className={inputClassName}
                value={tplProposalEn}
                onChange={(e) => setTplProposalEn(e.target.value)}
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium">{t("templateProposalJa")}</span>
              <input
                className={inputClassName}
                value={tplProposalJa}
                onChange={(e) => setTplProposalJa(e.target.value)}
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium">{t("templatePocEn")}</span>
              <input
                className={inputClassName}
                value={tplPocEn}
                onChange={(e) => setTplPocEn(e.target.value)}
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium">{t("templatePocJa")}</span>
              <input
                className={inputClassName}
                value={tplPocJa}
                onChange={(e) => setTplPocJa(e.target.value)}
              />
            </label>
          </div>
        </fieldset>

        <button
          type="submit"
          disabled={saving}
          className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {saving ? t("saving") : t("save")}
        </button>
      </form>
    </section>
  );
}
