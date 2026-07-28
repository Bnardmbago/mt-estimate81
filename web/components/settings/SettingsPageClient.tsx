"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import LogoutButton from "@/components/LogoutButton";
import PasswordField from "@/components/PasswordField";
import ConnectedAccountsPanel from "@/components/settings/ConnectedAccountsPanel";
import { useTheme } from "@/components/ThemeProvider";
import { apiFetch, apiJson, parseApiErrorPayload } from "@/lib/api";
import type { AccountType, UserProfile } from "@/lib/user-types";

type SettingsPageClientProps = {
  locale: string;
  profile: UserProfile;
};

const inputClassName =
  "w-full rounded border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-950";

export default function SettingsPageClient({ locale, profile }: SettingsPageClientProps) {
  const t = useTranslations("settings");
  const router = useRouter();
  const { theme, setTheme, mounted } = useTheme();
  const isContact = profile.account_type === "contact";
  const accountType = profile.account_type as AccountType;

  const [displayName, setDisplayName] = useState(profile.display_name);
  const [preferredLocale, setPreferredLocale] = useState<"ja" | "en">(
    profile.preferred_locale === "en" ? "en" : "ja",
  );
  const [profileBusy, setProfileBusy] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [profileSuccess, setProfileSuccess] = useState<string | null>(null);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordBusy, setPasswordBusy] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSuccess, setPasswordSuccess] = useState<string | null>(null);

  async function saveProfile(event: React.FormEvent) {
    event.preventDefault();
    setProfileBusy(true);
    setProfileError(null);
    setProfileSuccess(null);
    try {
      const updated = await apiJson<UserProfile>("/auth/me", {
        method: "PATCH",
        body: JSON.stringify({
          display_name: displayName.trim(),
          preferred_locale: preferredLocale,
        }),
      });
      setProfileSuccess(t("profileSaved"));
      if (updated.preferred_locale !== locale) {
        router.push(`/${updated.preferred_locale}/settings`);
        router.refresh();
      } else {
        router.refresh();
      }
    } catch (err) {
      setProfileError(err instanceof Error ? err.message : t("profileSaveError"));
    } finally {
      setProfileBusy(false);
    }
  }

  async function savePassword(event: React.FormEvent) {
    event.preventDefault();
    setPasswordError(null);
    setPasswordSuccess(null);
    if (newPassword !== confirmPassword) {
      setPasswordError(t("passwordMismatch"));
      return;
    }
    setPasswordBusy(true);
    try {
      const response = await apiFetch("/auth/change-password", {
        method: "POST",
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        const { message } = parseApiErrorPayload(payload, t("passwordSaveError"));
        throw new Error(message);
      }
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setPasswordSuccess(t("passwordSaved"));
    } catch (err) {
      setPasswordError(err instanceof Error ? err.message : t("passwordSaveError"));
    } finally {
      setPasswordBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
          {t("title")}
        </h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{t("description")}</p>
      </div>

      <section className="space-y-3 rounded-lg border border-slate-200 p-4 dark:border-slate-700">
        <h2 className="text-base font-semibold">{t("profileTitle")}</h2>
        <form onSubmit={(e) => void saveProfile(e)} className="space-y-3">
          <label className="block text-sm">
            <span className="mb-1 block font-medium">{t("fullName")}</span>
            <input
              className={inputClassName}
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              required
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium">{t("email")}</span>
            <input className={inputClassName} value={profile.email} readOnly disabled />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium">{t("language")}</span>
            <select
              className={inputClassName}
              value={preferredLocale}
              onChange={(e) => setPreferredLocale(e.target.value as "ja" | "en")}
            >
              <option value="ja">{t("languageJa")}</option>
              <option value="en">{t("languageEn")}</option>
            </select>
          </label>
          {profileError ? (
            <p className="text-sm text-red-600" role="alert">
              {profileError}
            </p>
          ) : null}
          {profileSuccess ? (
            <p className="text-sm text-emerald-700" role="status">
              {profileSuccess}
            </p>
          ) : null}
          <button
            type="submit"
            disabled={profileBusy}
            className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {profileBusy ? t("saving") : t("saveProfile")}
          </button>
        </form>
      </section>

      <section className="space-y-3 rounded-lg border border-slate-200 p-4 dark:border-slate-700">
        <h2 className="text-base font-semibold">{t("themeTitle")}</h2>
        <p className="text-sm text-slate-600 dark:text-slate-300">{t("themeDescription")}</p>
        {mounted ? (
          <div className="flex gap-4 text-sm">
            <label className="inline-flex items-center gap-2">
              <input
                type="radio"
                name="theme"
                checked={theme === "light"}
                onChange={() => setTheme("light")}
              />
              {t("themeLight")}
            </label>
            <label className="inline-flex items-center gap-2">
              <input
                type="radio"
                name="theme"
                checked={theme === "dark"}
                onChange={() => setTheme("dark")}
              />
              {t("themeDark")}
            </label>
          </div>
        ) : null}
      </section>

      {!isContact ? (
        <section className="space-y-3 rounded-lg border border-slate-200 p-4 dark:border-slate-700">
          <h2 className="text-base font-semibold">{t("passwordTitle")}</h2>
          <form onSubmit={(e) => void savePassword(e)} className="space-y-3">
            <label className="block text-sm">
              <span className="mb-1 block font-medium">{t("currentPassword")}</span>
              <PasswordField
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className={inputClassName}
                autoComplete="current-password"
                required
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium">{t("newPassword")}</span>
              <PasswordField
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className={inputClassName}
                autoComplete="new-password"
                minLength={8}
                required
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium">{t("confirmPassword")}</span>
              <PasswordField
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className={inputClassName}
                autoComplete="new-password"
                minLength={8}
                required
              />
            </label>
            {passwordError ? (
              <p className="text-sm text-red-600" role="alert">
                {passwordError}
              </p>
            ) : null}
            {passwordSuccess ? (
              <p className="text-sm text-emerald-700" role="status">
                {passwordSuccess}
              </p>
            ) : null}
            <button
              type="submit"
              disabled={passwordBusy}
              className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {passwordBusy ? t("saving") : t("changePassword")}
            </button>
          </form>
        </section>
      ) : null}

      {!isContact ? (
        <div className="rounded-lg border border-slate-200 p-4 dark:border-slate-700">
          <ConnectedAccountsPanel />
        </div>
      ) : null}

      <section className="rounded-lg border border-slate-200 p-4 dark:border-slate-700">
        <h2 className="mb-3 text-base font-semibold">{t("sessionTitle")}</h2>
        <LogoutButton locale={locale} accountType={accountType} />
      </section>
    </div>
  );
}
