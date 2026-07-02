"use client";

import { useTranslations } from "next-intl";
import WelcomeStepIcon from "@/components/welcome/WelcomeStepIcon";
import type { HelpUserGuideStep } from "@/lib/helpSearch";

type UserGuideTrack = {
  id: string;
  title: string;
  description: string;
  steps: HelpUserGuideStep[];
};

type HelpUserGuideDiagramProps = {
  namespace: "admin.help";
};

function TrackStep({
  step,
  index,
}: {
  step: HelpUserGuideStep;
  index: number;
}) {
  return (
    <li className="relative flex gap-3 pb-6 last:pb-0">
      <div className="relative flex flex-col items-center">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600 dark:bg-blue-950/60 dark:text-blue-400">
          <WelcomeStepIcon icon={step.icon} stepIndex={index} className="h-4 w-4" />
        </div>
        <span
          className="absolute top-9 bottom-0 w-px bg-slate-200 dark:bg-slate-700 last:hidden"
          aria-hidden
        />
      </div>
      <div className="min-w-0 flex-1 pt-0.5">
        <div className="flex items-baseline gap-2">
          <span className="text-xs font-semibold text-blue-600 dark:text-blue-400">
            {index + 1}
          </span>
          <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{step.title}</h4>
        </div>
        <p className="mt-1 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
          {step.description}
        </p>
      </div>
    </li>
  );
}

function UserGuideTrackColumn({ track }: { track: UserGuideTrack }) {
  return (
    <article className="flex h-full flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-gray-900 sm:p-6">
      <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">{track.title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
        {track.description}
      </p>
      <ol className="mt-5">
        {track.steps.map((step, index) => (
          <TrackStep key={`${track.id}-${index}`} step={step} index={index} />
        ))}
      </ol>
    </article>
  );
}

export default function HelpUserGuideDiagram({ namespace }: HelpUserGuideDiagramProps) {
  const t = useTranslations(namespace);
  const tracks = t.raw("userGuide.tracks") as UserGuideTrack[];

  return (
    <section className="rounded-2xl border border-slate-200/80 bg-white p-5 dark:border-slate-800 dark:bg-gray-900/40 sm:p-6 lg:p-8">
      <div className="max-w-3xl">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-600 dark:text-blue-400">
          {t("userGuide.eyebrow")}
        </p>
        <h2 className="mt-2 text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-50 sm:text-2xl">
          {t("userGuide.title")}
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400 sm:text-base">
          {t("userGuide.intro")}
        </p>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2 lg:gap-8">
        {tracks.map((track) => (
          <UserGuideTrackColumn key={track.id} track={track} />
        ))}
      </div>
    </section>
  );
}
