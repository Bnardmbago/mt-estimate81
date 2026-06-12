"use client";

import { useLocale } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";

export default function LocaleSwitcher() {
  const locale = useLocale() as Locale;
  const pathname = usePathname();
  const otherLocale: Locale = locale === "ja" ? "en" : "ja";

  return (
    <Link
      href={pathname}
      locale={otherLocale}
      className="header-btn uppercase tracking-wide"
    >
      {otherLocale}
    </Link>
  );
}
