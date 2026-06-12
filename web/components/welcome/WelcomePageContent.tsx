"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import WelcomeGuideSection from "@/components/welcome/WelcomeGuideSection";
import WelcomeHero from "@/components/welcome/WelcomeHero";

export default function WelcomePageContent() {
  const t = useTranslations("welcome");

  return (
    <div className="welcome-page -mx-4 sm:mx-0">
      <WelcomeHero />
      <WelcomeGuideSection />
      <section className="border-t border-slate-200 py-16 dark:border-slate-800">
        <div className="mx-auto max-w-5xl rounded-xl border border-slate-200 bg-slate-50 px-6 py-10 text-center dark:border-slate-700 dark:bg-slate-900/50 sm:px-12">
          <p className="text-sm font-medium text-slate-600 dark:text-slate-400">{t("footerCta")}</p>
          <Link
            href="/login"
            className="mt-4 inline-flex items-center justify-center rounded-lg bg-blue-600 px-6 py-3 text-sm font-medium text-white transition hover:bg-blue-700"
          >
            {t("footerCtaButton")}
          </Link>
          <p className="mt-6 text-sm text-slate-500 dark:text-slate-400">
            <Link href="/help" className="font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400">
              {t("helpLink")}
            </Link>
          </p>
        </div>
      </section>
    </div>
  );
}
