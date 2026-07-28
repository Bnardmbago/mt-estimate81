"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import PasswordField from "@/components/PasswordField";
import { resolveReturnPath } from "@/lib/authRedirect";
import { parseApiErrorPayload } from "@/lib/api";

export default function LoginForm() {
  const t = useTranslations("login");
  const tWelcome = useTranslations("welcome");
  const router = useRouter();
  const searchParams = useSearchParams();
  const params = useParams<{ locale: string }>();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const returnTo = resolveReturnPath(params.locale, searchParams.get("next"));

  function loginErrorMessage(code: string | undefined, apiMessage: string): string {
    switch (code) {
      case "AUTH_INVALID":
        return t("errorInvalidCredentials");
      case "CONTACT_USE_MAGIC_LINK":
        return t("errorContactUseMagicLink");
      case "USER_DISABLED":
        return t("errorUserDisabled");
      case "API_UNREACHABLE":
        return t("errorApiUnreachable");
      default:
        return apiMessage || t("error");
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        const { message, code } = parseApiErrorPayload(payload, t("error"));
        setError(loginErrorMessage(code, message));
        return;
      }

      router.push(returnTo);
      router.refresh();
    } catch {
      setError(t("errorApiUnreachable"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <h1 className="mb-6 text-2xl font-semibold">{t("title")}</h1>
      {searchParams.get("next") ? (
        <p className="mb-4 text-sm text-gray-600 dark:text-gray-400">{t("signInToContinue")}</p>
      ) : null}
      <form
        onSubmit={handleSubmit}
        className="space-y-4 rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-900"
      >
        <div>
          <label htmlFor="email" className="mb-1 block text-sm font-medium">
            {t("email")}
          </label>
          <input
            id="email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <div>
          <label htmlFor="password" className="mb-1 block text-sm font-medium">
            {t("password")}
          </label>
          <PasswordField
            id="password"
            required
            autoComplete="off"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        {error && (
          <p className="text-sm text-red-600" role="alert">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "..." : t("submit")}
        </button>
      </form>
      <p className="mt-4 text-center text-sm text-gray-600 dark:text-gray-400">
        <Link
          href={`/${params.locale}/welcome`}
          className="font-medium text-blue-600 hover:text-blue-800 hover:underline dark:text-blue-400 dark:hover:text-blue-300"
        >
          {tWelcome("loginLink")} →
        </Link>
      </p>
    </div>
  );
}
