"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { contactErrorMessage } from "@/lib/contact-errors";

export default function ContactVerifyClient() {
  const t = useTranslations("contact");
  const router = useRouter();
  const params = useParams<{ locale: string }>();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = searchParams.get("token");
    if (!token) {
      setError(t("verifyMissingToken"));
      return;
    }

    async function verify() {
      try {
        const response = await fetch("/api/auth/contact/verify", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ token }),
        });
        const payload = (await response.json()) as {
          estimate_id?: string;
          error?: string;
          code?: string;
        };

        if (!response.ok || !payload.estimate_id) {
          setError(contactErrorMessage(t, payload, "verifyError"));
          return;
        }

        router.replace(`/${params.locale}/estimates/${payload.estimate_id}`);
        router.refresh();
      } catch {
        setError(t("verifyError"));
      }
    }

    void verify();
  }, [params.locale, router, searchParams, t]);

  if (error) {
    return (
      <div className="mx-auto max-w-md rounded-lg border border-red-200 bg-red-50 p-6 text-center dark:border-red-900 dark:bg-red-950/40">
        <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-md text-center text-sm text-gray-500 dark:text-gray-400">
      {t("verifying")}
    </div>
  );
}
