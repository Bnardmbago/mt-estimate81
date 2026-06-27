"use client";

import { useTranslations } from "next-intl";
import ContactAccessForm from "@/components/contact/ContactAccessForm";
import WelcomeGuideSection from "@/components/welcome/WelcomeGuideSection";
import WelcomeHero from "@/components/welcome/WelcomeHero";

export default function WelcomePageContent() {
  const t = useTranslations("welcome");

  return (
    <div className="welcome-page -mx-4 sm:mx-0">
      <WelcomeHero />
      <WelcomeGuideSection />
      <section
        id="get-estimate"
        className="scroll-mt-20 border-t border-slate-200 py-16 dark:border-slate-800"
      >
        <div className="mx-auto max-w-2xl px-4 sm:px-0">
          <div className="mb-8 text-center">
            <h2 className="text-2xl font-semibold text-slate-900 dark:text-slate-100 sm:text-3xl">
              {t("getEstimateTitle")}
            </h2>
            <p className="mt-3 text-sm text-slate-600 dark:text-slate-400 sm:text-base">
              {t("getEstimateDescription")}
            </p>
          </div>
          <ContactAccessForm />
        </div>
      </section>
    </div>
  );
}
