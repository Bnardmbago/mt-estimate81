"use client";

import type { ReactNode } from "react";

type CollapsibleFormSectionProps = {
  id: string;
  title: string;
  description: string;
  expanded: boolean;
  onExpandedChange: (expanded: boolean) => void;
  sectionClassName: string;
  expandLabel: string;
  collapseLabel: string;
  children: ReactNode;
};

function ChevronIcon({ expanded }: { expanded: boolean }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden="true"
      className={`mt-1 h-5 w-5 shrink-0 text-gray-500 transition-transform ${
        expanded ? "rotate-180" : ""
      }`}
    >
      <path
        fillRule="evenodd"
        d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.94a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
        clipRule="evenodd"
      />
    </svg>
  );
}

export default function CollapsibleFormSection({
  id,
  title,
  description,
  expanded,
  onExpandedChange,
  sectionClassName,
  expandLabel,
  collapseLabel,
  children,
}: CollapsibleFormSectionProps) {
  return (
    <section
      id={id}
      className={`scroll-mt-24 mt-8 rounded-lg border p-5 ${sectionClassName}`}
    >
      <button
        type="button"
        onClick={() => onExpandedChange(!expanded)}
        aria-expanded={expanded}
        aria-controls={`${id}-content`}
        className="flex w-full items-start justify-between gap-3 text-left"
      >
        <div className="min-w-0">
          <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
          <p className="mt-1 text-sm text-gray-600">{description}</p>
        </div>
        <span className="sr-only">{expanded ? collapseLabel : expandLabel}</span>
        <ChevronIcon expanded={expanded} />
      </button>

      {expanded ? (
        <div id={`${id}-content`} className="mt-5 space-y-5">
          {children}
        </div>
      ) : null}
    </section>
  );
}
