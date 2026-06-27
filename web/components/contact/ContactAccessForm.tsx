"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import TurnstileWidget from "@/components/contact/TurnstileWidget";
import { contactErrorMessage } from "@/lib/contact-errors";

type ContactAccessFormProps = {
  onSubmitted?: () => void;
};

export default function ContactAccessForm({ onSubmitted }: ContactAccessFormProps) {
  const t = useTranslations("contact");
  const locale = useLocale();
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [captchaToken, setCaptchaToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const turnstileKey = useRef(0);

  const siteKey = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY?.trim() ?? "";
  const captchaReady = siteKey ? Boolean(captchaToken) : true;

  const resetCaptcha = useCallback(() => {
    setCaptchaToken("");
    turnstileKey.current += 1;
  }, []);

  useEffect(() => {
    if (!siteKey) {
      setCaptchaToken("dev-bypass");
    }
  }, [siteKey]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const trimmedEmail = email.trim();
    const trimmedName = displayName.trim();
    const trimmedCompany = companyName.trim();

    if (!trimmedEmail || (!trimmedName && !trimmedCompany)) {
      setError(t("errorNameOrCompany"));
      return;
    }

    setLoading(true);

    try {
      const response = await fetch("/api/auth/contact/request-link", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: trimmedEmail,
          display_name: trimmedName,
          company_name: trimmedCompany,
          locale,
          captcha_token: captchaToken || "dev-bypass",
        }),
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        setError(contactErrorMessage(t, payload));
        resetCaptcha();
        return;
      }

      setSubmitted(true);
      onSubmitted?.();
    } catch {
      setError(t("errorNetwork"));
      resetCaptcha();
    } finally {
      setLoading(false);
    }
  }

  if (submitted) {
    return (
      <div className="rounded-lg border border-green-200 bg-green-50 p-6 text-center dark:border-green-900 dark:bg-green-950/40">
        <h2 className="text-lg font-semibold text-green-900 dark:text-green-100">{t("checkEmailTitle")}</h2>
        <p className="mt-2 text-sm text-green-800 dark:text-green-200">{t("checkEmailBody", { email: email.trim() })}</p>
      </div>
    );
  }

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="mx-auto max-w-md space-y-4">
      <div>
        <label htmlFor="contact-email" className="mb-1 block text-sm font-medium">
          {t("email")}
        </label>
        <input
          id="contact-email"
          type="email"
          required
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-900"
        />
      </div>
      <div>
        <label htmlFor="contact-name" className="mb-1 block text-sm font-medium">
          {t("displayName")}
        </label>
        <input
          id="contact-name"
          type="text"
          value={displayName}
          onChange={(event) => setDisplayName(event.target.value)}
          className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-900"
        />
      </div>
      <div>
        <label htmlFor="contact-company" className="mb-1 block text-sm font-medium">
          {t("companyName")}
        </label>
        <input
          id="contact-company"
          type="text"
          value={companyName}
          onChange={(event) => setCompanyName(event.target.value)}
          className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-900"
        />
      </div>
      {siteKey ? (
        <TurnstileWidget
          key={turnstileKey.current}
          siteKey={siteKey}
          onVerify={setCaptchaToken}
          onExpire={() => setCaptchaToken("")}
        />
      ) : null}
      {error ? <p className="text-sm text-red-600 dark:text-red-400">{error}</p> : null}
      <button
        type="submit"
        disabled={loading || !captchaReady}
        className="w-full rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
      >
        {loading ? t("submitting") : t("submit")}
      </button>
      <p className="text-center text-sm text-gray-500 dark:text-gray-400">
        {t("fullAccountHint")}{" "}
        <a href={`/${locale}/login`} className="font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400">
          {t("fullAccountLink")}
        </a>
      </p>
    </form>
  );
}
