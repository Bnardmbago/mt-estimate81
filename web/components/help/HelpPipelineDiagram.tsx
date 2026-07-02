"use client";

import { useTranslations } from "next-intl";

type PipelineStage = {
  id: string;
  title: string;
  description: string;
};

type PipelineAdminItem = {
  id: string;
  title: string;
  description: string;
};

type HelpPipelineDiagramProps = {
  namespace: "admin.help";
};

function PipelineArrow({ className = "" }: { className?: string }) {
  return (
    <div
      className={`flex shrink-0 items-center justify-center text-slate-300 dark:text-slate-600 ${className}`}
      aria-hidden
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="h-5 w-5 lg:h-4 lg:w-4"
      >
        <path d="M5 12h14" />
        <path d="m12 5 7 7-7 7" />
      </svg>
    </div>
  );
}

function PipelineArrowDown() {
  return (
    <div
      className="flex justify-center py-1 text-slate-300 dark:text-slate-600 lg:hidden"
      aria-hidden
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="h-5 w-5"
      >
        <path d="M12 5v14" />
        <path d="m19 12-7 7-7-7" />
      </svg>
    </div>
  );
}

export default function HelpPipelineDiagram({ namespace }: HelpPipelineDiagramProps) {
  const t = useTranslations(namespace);
  const stages = t.raw("pipeline.stages") as PipelineStage[];
  const adminItems = t.raw("pipeline.adminItems") as PipelineAdminItem[];

  return (
    <section className="rounded-2xl border border-slate-200/80 bg-slate-50/60 p-5 dark:border-slate-800 dark:bg-slate-900/40 sm:p-6 lg:p-8">
      <div className="max-w-3xl">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-600 dark:text-blue-400">
          {t("pipeline.eyebrow")}
        </p>
        <h2 className="mt-2 text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-50 sm:text-2xl">
          {t("pipeline.title")}
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400 sm:text-base">
          {t("pipeline.intro")}
        </p>
      </div>

      <div className="mt-8">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          {t("pipeline.flowLabel")}
        </p>
        <ol className="mt-4 flex flex-col lg:flex-row lg:flex-wrap lg:items-stretch lg:gap-y-4">
          {stages.map((stage, index) => (
            <li key={stage.id} className="contents">
              <article className="flex flex-1 flex-col rounded-xl border border-blue-200/80 bg-white p-4 shadow-sm dark:border-blue-900/50 dark:bg-gray-900 lg:min-w-[8.5rem] lg:max-w-[11rem]">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-600 text-xs font-semibold text-white">
                  {index + 1}
                </span>
                <h3 className="mt-3 text-sm font-semibold leading-snug text-slate-900 dark:text-slate-100">
                  {stage.title}
                </h3>
                <p className="mt-1.5 flex-1 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                  {stage.description}
                </p>
              </article>
              {index < stages.length - 1 ? (
                <>
                  <PipelineArrowDown />
                  <PipelineArrow className="hidden px-1 lg:flex" />
                </>
              ) : null}
            </li>
          ))}
        </ol>
      </div>

      <div className="mt-8 rounded-xl border border-amber-200/80 bg-amber-50/70 p-4 dark:border-amber-900/40 dark:bg-amber-950/20 sm:p-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-amber-800 dark:text-amber-300">
          {t("pipeline.adminLabel")}
        </p>
        <p className="mt-1 text-sm text-amber-900/80 dark:text-amber-200/80">{t("pipeline.adminIntro")}</p>
        <ul className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {adminItems.map((item) => (
            <li
              key={item.id}
              className="rounded-lg border border-amber-200/60 bg-white/80 px-3 py-3 dark:border-amber-900/30 dark:bg-gray-900/60"
            >
              <h4 className="text-sm font-medium text-slate-900 dark:text-slate-100">{item.title}</h4>
              <p className="mt-1 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                {item.description}
              </p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
