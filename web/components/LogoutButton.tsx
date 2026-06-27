"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";

import type { AccountType } from "@/lib/user-types";

type LogoutButtonProps = {
  locale: string;
  accountType?: AccountType;
};

export default function LogoutButton({ locale, accountType = "full" }: LogoutButtonProps) {
  const t = useTranslations("nav");
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  async function handleLogout() {
    setLoading(true);

    try {
      await fetch("/api/auth/logout", {
        method: "POST",
        credentials: "include",
      });
      router.push(accountType === "contact" ? `/${locale}/contact` : `/${locale}/login`);
      router.refresh();
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      type="button"
      onClick={() => void handleLogout()}
      disabled={loading}
      className="header-btn"
    >
      {loading ? "..." : t("logout")}
    </button>
  );
}
