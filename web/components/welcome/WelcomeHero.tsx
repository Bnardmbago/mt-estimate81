"use client";

import { useTranslations } from "next-intl";

export default function WelcomeHero() {
  const t = useTranslations("welcome");

  return (
    <section className="relative -mx-4 border-b border-slate-200 bg-white px-4 py-16 dark:border-slate-800 dark:bg-gray-900 sm:-mx-0 sm:rounded-xl sm:border sm:px-12 sm:py-20" data-tour="welcome-hero">
      <div className="mx-auto max-w-3xl text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500 dark:text-slate-400">
          AI Estimate
        </p>
        <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-900 dark:text-slate-50 sm:text-4xl">
          {t("title")}
        </h1>
        <p className="mt-4 text-base leading-relaxed text-slate-600 dark:text-slate-400 sm:text-lg">
          {t("description")}
        </p>
        <div className="mt-8">
          <a
            href="#get-estimate"
            className="inline-flex items-center justify-center rounded-lg bg-blue-600 px-6 py-3 text-sm font-medium text-white transition hover:bg-blue-700"
          >
            {t("heroCta")}
          </a>
        </div>
      </div>
    </section>
  );
}
