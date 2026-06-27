"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import type { HelpUserGuideStep } from "@/lib/helpSearch";
import WelcomeStepIcon from "@/components/welcome/WelcomeStepIcon";

function GuideStepCard({
  step,
  index,
  total,
  stepCtaLabel,
}: {
  step: HelpUserGuideStep;
  index: number;
  total: number;
  stepCtaLabel: string;
}) {
  const isLastAlone = total % 3 === 1 && index === total - 1;

  return (
    <li
      className={`flex ${isLastAlone ? "lg:col-span-3 lg:mx-auto lg:max-w-sm xl:max-w-md" : ""}`}
    >
      <article className="flex h-full w-full flex-col rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm transition hover:border-blue-200 hover:shadow-md dark:border-slate-700 dark:bg-gray-900 dark:hover:border-blue-800 sm:p-6">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600 dark:bg-blue-950/60 dark:text-blue-400">
            <WelcomeStepIcon icon={step.icon} stepIndex={index} className="h-5 w-5" />
          </div>
          <span className="flex h-7 min-w-[1.75rem] items-center justify-center rounded-full bg-blue-600 px-2 text-xs font-semibold text-white">
            {index + 1}
          </span>
        </div>

        <h3 className="text-base font-semibold leading-snug text-slate-900 dark:text-slate-100">
          {step.title}
        </h3>
        <p className="mt-2 flex-1 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
          {step.description}
        </p>

        {step.href ? (
          step.href.startsWith("#") ? (
            <a
              href={step.href}
              className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
            >
              {stepCtaLabel}
              <span aria-hidden>→</span>
            </a>
          ) : (
            <Link
              href={step.href}
              className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
            >
              {stepCtaLabel}
              <span aria-hidden>→</span>
            </Link>
          )
        ) : (
          <div className="mt-4 h-5" aria-hidden />
        )}
      </article>
    </li>
  );
}

export default function WelcomeGuideSection() {
  const t = useTranslations("welcome");
  const steps = t.raw("userGuide.steps") as HelpUserGuideStep[];

  return (
    <section className="py-16 sm:py-20">
      <div className="mx-auto max-w-6xl rounded-2xl border border-slate-200/80 bg-slate-50/60 px-4 py-10 dark:border-slate-800 dark:bg-slate-900/40 sm:px-8 sm:py-12 lg:px-12">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-600 dark:text-blue-400">
            {t("userGuide.eyebrow")}
          </p>
          <h2 className="mt-3 text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50 sm:text-3xl">
            {t("userGuide.title")}
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-slate-600 dark:text-slate-400 sm:text-base">
            {t("userGuide.intro")}
          </p>
        </div>

        <ol className="mt-10 grid grid-cols-1 gap-5 sm:grid-cols-2 sm:gap-6 lg:grid-cols-3 lg:gap-6">
          {steps.map((step, index) => (
            <GuideStepCard
              key={`${step.title}-${index}`}
              step={step}
              index={index}
              total={steps.length}
              stepCtaLabel={t("userGuide.stepCta")}
            />
          ))}
        </ol>
      </div>
    </section>
  );
}
