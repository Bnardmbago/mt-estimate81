"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import type { PresentationConsistencySuggestion } from "@/lib/presentation";

type Props = {
  suggestions: PresentationConsistencySuggestion[];
  busy: boolean;
  onApply: (ids?: string[]) => Promise<void>;
  onDismiss: () => void;
  onReset: () => Promise<void>;
};

export default function PresentationConsistencyPanel({
  suggestions,
  busy,
  onApply,
  onDismiss,
  onReset,
}: Props) {
  const t = useTranslations("admin.presentation.cover");
  const [selected, setSelected] = useState<string[]>(suggestions.map((item) => item.id));

  if (suggestions.length === 0) {
    return (
      <section className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm dark:border-emerald-900 dark:bg-emerald-950/30">
        <div className="flex items-center justify-between gap-3">
          <p>{t("consistencyClear")}</p>
          <button type="button" className="header-btn text-xs" disabled={busy} onClick={() => void onReset()}>
            {t("checkAgain")}
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/30">
      <h3 className="text-sm font-semibold">{t("consistencyTitle")}</h3>
      <p className="mt-1 text-xs text-slate-600 dark:text-slate-300">{t("consistencyHint")}</p>
      <ul className="mt-3 space-y-2">
        {suggestions.map((suggestion) => (
          <li key={suggestion.id} className="rounded border border-amber-200 bg-white/70 p-3 dark:border-amber-900 dark:bg-slate-900/60">
            <label className="flex items-start gap-3 text-sm">
              <input
                type="checkbox"
                className="mt-1"
                checked={selected.includes(suggestion.id)}
                onChange={(event) =>
                  setSelected((current) =>
                    event.target.checked
                      ? [...current, suggestion.id]
                      : current.filter((id) => id !== suggestion.id),
                  )
                }
              />
              <span className="min-w-0">
                <span className="font-medium">{suggestion.target} · {suggestion.field_path}</span>
                <span className="mt-1 block text-xs text-slate-600 dark:text-slate-300">
                  {suggestion.rationale}
                </span>
                <code className="mt-1 block break-all text-xs">
                  {formatValue(suggestion.before)} → {formatValue(suggestion.after)}
                </code>
              </span>
            </label>
          </li>
        ))}
      </ul>
      <div className="mt-3 flex flex-wrap gap-2">
        <button type="button" className="header-btn text-xs" disabled={busy} onClick={() => void onApply()}>
          {t("applyAll")}
        </button>
        <button
          type="button"
          className="header-btn text-xs"
          disabled={busy || selected.length === 0}
          onClick={() => void onApply(selected)}
        >
          {t("applySelected", { count: selected.length })}
        </button>
        <button type="button" className="header-btn text-xs" disabled={busy} onClick={onDismiss}>
          {t("dismiss")}
        </button>
        <button type="button" className="header-btn text-xs" disabled={busy} onClick={() => void onReset()}>
          {t("reset")}
        </button>
      </div>
    </section>
  );
}

function formatValue(value: unknown) {
  if (value === undefined || value === null || value === "") return "—";
  return typeof value === "string" ? value : JSON.stringify(value);
}
