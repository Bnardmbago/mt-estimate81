"use client";

import HelpKnowledgePanel from "@/components/help/HelpKnowledgePanel";
import HelpPipelineDiagram from "@/components/help/HelpPipelineDiagram";
import HelpUserGuideDiagram from "@/components/help/HelpUserGuideDiagram";
import TourRestartButton from "@/components/tour/TourRestartButton";
import { useTranslations } from "next-intl";

export default function AdminHelpReference() {
  const t = useTranslations("tour");

  return (
    <div className="space-y-8">
      <section
        data-tour="admin-help-restart-tour"
        className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-gray-900"
      >
        <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
          {t("helpRestartTitle")}
        </h2>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
          {t("helpRestartDescription")}
        </p>
        <div className="mt-3">
          <TourRestartButton />
        </div>
      </section>
      <HelpPipelineDiagram namespace="admin.help" />
      <HelpUserGuideDiagram namespace="admin.help" />
      <HelpKnowledgePanel namespace="admin.help" searchInputId="admin-help-search" />
    </div>
  );
}
