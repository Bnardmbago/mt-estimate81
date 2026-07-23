"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import type { ProposalLocale, ProposalSection } from "@/lib/proposal-types";
import type { ProposalTab } from "@/components/proposal/ProposalToc";

type ProposalSectionEditorProps = {
  section: ProposalSection;
  part?: ProposalTab;
  docLocale?: ProposalLocale | string;
  onSave: (next: { body?: string; bullets?: string[] }) => Promise<void>;
};

function formatRating(rating: string, locale?: string): string {
  const key = rating.trim().toLowerCase();
  if (locale === "ja") {
    if (key === "high") return "高";
    if (key === "medium") return "中";
    if (key === "low") return "低";
  }
  return rating;
}

export default function ProposalSectionEditor({
  section,
  part = "assessment",
  docLocale = "en",
  onSave,
}: ProposalSectionEditorProps) {
  const t = useTranslations("proposal");
  const [editing, setEditing] = useState(false);
  const [body, setBody] = useState(section.body || "");
  const [bulletsText, setBulletsText] = useState((section.bullets || []).join("\n"));
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setBody(section.body || "");
    setBulletsText((section.bullets || []).join("\n"));
  }, [section]);

  async function handleSave() {
    setSaving(true);
    try {
      await onSave({
        body,
        bullets: bulletsText
          .split("\n")
          .map((line) => line.trim())
          .filter(Boolean),
      });
      setEditing(false);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section
      id={section.id}
      className="scroll-mt-28 border-b border-slate-100 py-5 last:border-b-0 dark:border-slate-800"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            {section.title}
          </h3>
          {part === "assessment" && section.rating ? (
            <span className="proposal-rating mt-1 inline-block rounded px-2 py-0.5 text-xs capitalize">
              {formatRating(section.rating, docLocale)}
            </span>
          ) : null}
          {section.user_edited ? (
            <span className="ml-2 text-xs text-amber-700 dark:text-amber-300">
              {t("editedBadge")}
            </span>
          ) : null}
        </div>
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
        <div className="mt-3 space-y-3 print:hidden">
          <textarea
            className="min-h-28 w-full rounded border border-slate-300 bg-white p-3 text-sm dark:border-slate-600 dark:bg-slate-900"
            value={body}
            onChange={(e) => setBody(e.target.value)}
          />
          <textarea
            className="min-h-24 w-full rounded border border-slate-300 bg-white p-3 text-sm dark:border-slate-600 dark:bg-slate-900"
            value={bulletsText}
            onChange={(e) => setBulletsText(e.target.value)}
            placeholder={t("bulletsPlaceholder")}
          />
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
              onClick={() => setEditing(false)}
            >
              {t("cancel")}
            </button>
          </div>
        </div>
      ) : (
        <div className="mt-2 space-y-2 text-sm leading-relaxed text-slate-700 dark:text-slate-200">
          {section.body ? <p className="whitespace-pre-wrap">{section.body}</p> : null}
          {section.bullets && section.bullets.length > 0 ? (
            <ul className="list-disc space-y-1 pl-5">
              {section.bullets.map((bullet) => (
                <li key={bullet}>{bullet}</li>
              ))}
            </ul>
          ) : null}
        </div>
      )}
    </section>
  );
}
