"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import type {
  ProposalCoverField,
  ProposalCoverValues,
  ProposalLocale,
} from "@/lib/proposal-types";

type Props = {
  fields: ProposalCoverField[];
  values: ProposalCoverValues;
  locale: ProposalLocale;
  disabled?: boolean;
  onSave: (values: Record<string, string>) => Promise<void>;
};

export default function ProposalCoverFields({
  fields,
  values,
  locale,
  disabled = false,
  onSave,
}: Props) {
  const t = useTranslations("proposal.cover");
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDraft(
      Object.fromEntries(
        fields.map((field) => [field.key, coverValue(values[field.key], locale)]),
      ),
    );
    setError(null);
  }, [fields, locale, values]);

  if (fields.length === 0) {
    return null;
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await onSave(draft);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : t("saveFailed"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="mt-4 rounded-lg border border-slate-200 p-4 dark:border-slate-700">
      <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
        {t("title")}
      </h3>
      <p className="mt-1 text-xs text-slate-500">
        {t("description", { locale: locale.toUpperCase() })}
      </p>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        {fields.map((field) => {
          const content = localizedContent(field, locale);
          return (
            <label key={field.key} className="text-sm">
              <span className="mb-1 block font-medium text-slate-700 dark:text-slate-200">
                {content.label || field.key}
                {field.required ? (
                  <span className="ml-1 text-red-600" aria-hidden="true">
                    *
                  </span>
                ) : null}
              </span>
              <input
                type="text"
                value={draft[field.key] || ""}
                required={Boolean(field.required)}
                disabled={disabled || saving}
                placeholder={content.default_text || undefined}
                onChange={(event) =>
                  setDraft((current) => ({
                    ...current,
                    [field.key]: event.target.value,
                  }))
                }
                className="w-full rounded border border-slate-300 bg-white px-3 py-2 dark:border-slate-600 dark:bg-slate-950"
              />
              {field.auto_fill ? (
                <span className="mt-1 block text-xs text-slate-500">
                  {t("autoFillHint")}
                </span>
              ) : null}
            </label>
          );
        })}
      </div>
      <div className="mt-3 flex items-center gap-3">
        <button
          type="button"
          disabled={disabled || saving}
          className="proposal-btn-primary rounded px-4 py-2 text-sm disabled:opacity-50"
          onClick={() => void handleSave()}
        >
          {saving ? t("saving") : t("save")}
        </button>
        {error ? (
          <p className="text-sm text-red-600" role="alert">
            {error}
          </p>
        ) : null}
      </div>
    </section>
  );
}

function localizedContent(field: ProposalCoverField, locale: ProposalLocale) {
  const fallback = locale === "en" ? "ja" : "en";
  return (
    field.content?._i18n?.[locale] ||
    field.content?._i18n?.[fallback] ||
    field.content ||
    {}
  );
}

function coverValue(
  stored: ProposalCoverValues[string] | undefined,
  locale: ProposalLocale,
): string {
  if (stored === null || stored === undefined) return "";
  if (typeof stored !== "object") return String(stored);
  const localized = stored._i18n?.[locale]?.value;
  if (localized !== null && localized !== undefined) return String(localized);
  if (stored.value !== null && stored.value !== undefined) return String(stored.value);
  return "";
}
