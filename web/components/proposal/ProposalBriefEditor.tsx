"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import type { ProposalDocLabels } from "@/lib/proposal-doc-labels";
import type { ProposalProjectBrief } from "@/lib/proposal-types";

const BRIEF_FIELDS: Array<keyof ProposalProjectBrief> = [
  "project_name",
  "project_description",
  "business_problem",
  "target_users",
  "technology_stack",
  "constraints",
];

type ProposalBriefEditorProps = {
  brief: ProposalProjectBrief;
  labels: ProposalDocLabels;
  onSave: (next: ProposalProjectBrief) => Promise<void>;
};

function fieldLabel(
  key: keyof ProposalProjectBrief,
  labels: ProposalDocLabels,
): string {
  switch (key) {
    case "project_name":
      return labels.briefProjectName;
    case "project_description":
      return labels.briefDescription;
    case "business_problem":
      return labels.briefBusinessProblem;
    case "target_users":
      return labels.briefTargetUsers;
    case "technology_stack":
      return labels.briefTechnologyStack;
    case "constraints":
      return labels.briefConstraints;
    default:
      return key;
  }
}

export default function ProposalBriefEditor({
  brief,
  labels,
  onSave,
}: ProposalBriefEditorProps) {
  const t = useTranslations("proposal");
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<ProposalProjectBrief>(brief);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setDraft(brief);
  }, [brief]);

  async function handleSave() {
    setSaving(true);
    try {
      await onSave(draft);
      setEditing(false);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section
      id="project_brief"
      className="proposal-box mb-6 scroll-mt-28 rounded-lg border p-4"
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <h3 className="proposal-doc-heading text-lg font-semibold">
          {labels.projectBrief}
        </h3>
        {!editing ? (
          <button
            type="button"
            className="proposal-link text-sm hover:underline print:hidden"
            onClick={() => setEditing(true)}
          >
            {t("edit")}
          </button>
        ) : null}
      </div>
      {editing ? (
        <div className="space-y-3 print:hidden">
          {BRIEF_FIELDS.map((key) => (
            <label key={key} className="block text-sm">
              <span className="mb-1 block text-slate-600 dark:text-slate-300">
                {fieldLabel(key, labels)}
              </span>
              <textarea
                className="min-h-16 w-full rounded border border-slate-300 bg-white p-2 text-sm dark:border-slate-600 dark:bg-slate-900"
                value={draft[key] || ""}
                onChange={(e) =>
                  setDraft((prev) => ({ ...prev, [key]: e.target.value }))
                }
              />
            </label>
          ))}
          <div className="flex gap-2">
            <button
              type="button"
              disabled={saving}
              className="proposal-btn-primary rounded px-3 py-1.5 text-sm disabled:opacity-50"
              onClick={() => void handleSave()}
            >
              {saving ? t("saving") : t("save")}
            </button>
            <button
              type="button"
              className="rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-600"
              onClick={() => {
                setDraft(brief);
                setEditing(false);
              }}
            >
              {t("cancel")}
            </button>
          </div>
        </div>
      ) : (
        <dl className="space-y-3 text-sm">
          {BRIEF_FIELDS.map((key) => (
            <div key={key}>
              <dt className="font-medium text-slate-700 dark:text-slate-200">
                {fieldLabel(key, labels)}
              </dt>
              <dd className="mt-0.5 whitespace-pre-wrap text-slate-700 dark:text-slate-300">
                {brief[key] || "—"}
              </dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  );
}
