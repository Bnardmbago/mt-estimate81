"use client";

import { proposalDocLabels } from "@/lib/proposal-doc-labels";
import type { ProposalDetail } from "@/lib/proposal-types";

export type ProposalTab = "assessment" | "proposal" | "poc";

type TocEntry = {
  id: string;
  title: string;
  part: ProposalTab;
  level: 1 | 2;
};

type ProposalTocProps = {
  proposal: ProposalDetail;
  activeTab: ProposalTab;
  onNavigate: (part: ProposalTab, sectionId?: string) => void;
};

export function buildMasterToc(proposal: ProposalDetail): TocEntry[] {
  const labels = proposalDocLabels(proposal.locale);
  const entries: TocEntry[] = [];
  if (proposal.assessment) {
    entries.push({
      id: "assessment",
      title: labels.partAssessment,
      part: "assessment",
      level: 1,
    });
    for (const section of proposal.assessment.sections || []) {
      entries.push({
        id: section.id,
        title: section.title,
        part: "assessment",
        level: 2,
      });
    }
  }
  if (proposal.proposal_body) {
    entries.push({
      id: "proposal",
      title: labels.partProposal,
      part: "proposal",
      level: 1,
    });
    for (const section of proposal.proposal_body.sections || []) {
      entries.push({
        id: section.id,
        title: section.title,
        part: "proposal",
        level: 2,
      });
    }
  }
  if (proposal.include_poc && proposal.poc) {
    entries.push({ id: "poc", title: labels.partPoc, part: "poc", level: 1 });
    if (proposal.poc.project_brief) {
      entries.push({
        id: "project_brief",
        title: labels.projectBrief,
        part: "poc",
        level: 2,
      });
    }
    for (const section of proposal.poc.sections || []) {
      entries.push({
        id: section.id,
        title: section.title,
        part: "poc",
        level: 2,
      });
    }
  }
  return entries;
}

export default function ProposalToc({
  proposal,
  activeTab,
  onNavigate,
}: ProposalTocProps) {
  const labels = proposalDocLabels(proposal.locale);
  const entries = buildMasterToc(proposal);

  if (!entries.length) {
    return null;
  }

  return (
    <nav
      aria-label={labels.tocLabel}
      className="sticky top-20 max-h-[calc(100vh-6rem)] overflow-y-auto rounded-lg border border-slate-200 bg-white p-4 text-sm dark:border-slate-700 dark:bg-slate-900 print:hidden"
    >
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
        {labels.tocLabel}
      </h2>
      <ol className="space-y-1">
        {entries.map((entry) => {
          const isPartActive = entry.part === activeTab && entry.level === 1;
          return (
            <li
              key={`${entry.part}-${entry.id}`}
              className={entry.level === 2 ? "ml-3" : ""}
            >
              <button
                type="button"
                className={`proposal-toc-link w-full text-left ${
                  isPartActive
                    ? "proposal-toc-active"
                    : "text-slate-700 dark:text-slate-200"
                }`}
                onClick={() =>
                  onNavigate(entry.part, entry.level === 2 ? entry.id : undefined)
                }
              >
                {entry.title}
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
