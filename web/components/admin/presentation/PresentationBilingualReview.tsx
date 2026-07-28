"use client";

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import type { PresentationDraft, PresentationLocale } from "@/lib/presentation";

type Props = {
  draft: PresentationDraft | null;
  currentLocale: PresentationLocale;
  busy: boolean;
  error: string | null;
  onClose: () => void;
  onApprove: (patch: {
    theme_draft: Record<string, unknown>;
    style_draft: Record<string, unknown>;
    template_draft: Record<string, unknown>;
  }) => Promise<void>;
};

type LocalizedValues = { name?: string; description?: string; label?: string; default_text?: string };
type AxisKey = "theme" | "style" | "template";
type AxisEdits = Record<AxisKey, { name: string; description: string }>;

export default function PresentationBilingualReview({
  draft,
  currentLocale,
  busy,
  error,
  onClose,
  onApprove,
}: Props) {
  const t = useTranslations("admin.presentation.cover");
  const [edits, setEdits] = useState<AxisEdits>({
    theme: { name: "", description: "" },
    style: { name: "", description: "" },
    template: { name: "", description: "" },
  });

  useEffect(() => {
    if (!draft) return;
    const source = draft.source_locale as PresentationLocale;
    setEdits({
      theme: axisEditValues(draft.theme_draft, source),
      style: axisEditValues(draft.style_draft, source),
      template: axisEditValues(draft.template_draft, source),
    });
  }, [draft]);

  const axes = useMemo(() => {
    if (!draft) return [];
    return [
      { key: "theme" as const, payload: draft.theme_draft },
      { key: "style" as const, payload: draft.style_draft },
      { key: "template" as const, payload: draft.template_draft },
    ];
  }, [draft]);

  if (!draft) return null;

  const sourceLocale = draft.source_locale as PresentationLocale;
  const fields = coverFields(draft);
  const missingSourceNames = (["theme", "style", "template"] as const).filter(
    (key) => !edits[key].name.trim(),
  );
  const patched = {
    theme_draft: applyAxisEdit(draft.theme_draft, sourceLocale, edits.theme),
    style_draft: applyAxisEdit(draft.style_draft, sourceLocale, edits.style),
    template_draft: applyAxisEdit(draft.template_draft, sourceLocale, edits.template),
  };
  const missing = countMissing({
    ...draft,
    theme_draft: patched.theme_draft,
    style_draft: patched.style_draft,
    template_draft: patched.template_draft,
  });
  const canApprove = missingSourceNames.length === 0 && !busy;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4" role="dialog" aria-modal="true" aria-labelledby="bilingual-review-title">
      <div className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-xl bg-white p-5 shadow-xl dark:bg-slate-900">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="bilingual-review-title" className="text-lg font-semibold">{t("bilingualReviewTitle")}</h2>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{t("bilingualReviewHint")}</p>
          </div>
          <button type="button" className="header-btn-icon" aria-label={t("close")} onClick={onClose}>×</button>
        </div>

        {missingSourceNames.length > 0 ? (
          <p className="mt-4 rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
            {t("sourceNamesRequired")}
          </p>
        ) : missing > 0 ? (
          <p className="mt-4 rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
            {t("translationPending", { count: missing })}
          </p>
        ) : (
          <p className="mt-4 rounded border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-200">
            {t("translationsReady")}
          </p>
        )}

        <section className="mt-4 space-y-3 rounded border border-slate-200 p-3 dark:border-slate-700">
          <h3 className="text-sm font-semibold">{t("axisNamesTitle", { locale: sourceLocale.toUpperCase() })}</h3>
          <p className="text-xs text-slate-500">{t("axisNamesHint")}</p>
          {axes.map(({ key }) => (
            <div key={key} className="grid gap-2 sm:grid-cols-2">
              <label className="text-sm">
                <span className="mb-1 block">{t(`reviewAxes.${key}`)} · {t("name")}</span>
                <input
                  className="w-full rounded border border-slate-300 px-3 py-2 dark:border-slate-600 dark:bg-slate-950"
                  value={edits[key].name}
                  disabled={busy}
                  onChange={(event) =>
                    setEdits((current) => ({
                      ...current,
                      [key]: { ...current[key], name: event.target.value },
                    }))
                  }
                />
              </label>
              <label className="text-sm">
                <span className="mb-1 block">{t(`reviewAxes.${key}`)} · {t("description")}</span>
                <input
                  className="w-full rounded border border-slate-300 px-3 py-2 dark:border-slate-600 dark:bg-slate-950"
                  value={edits[key].description}
                  disabled={busy}
                  onChange={(event) =>
                    setEdits((current) => ({
                      ...current,
                      [key]: { ...current[key], description: event.target.value },
                    }))
                  }
                />
              </label>
            </div>
          ))}
        </section>

        <div className="mt-4 overflow-x-auto">
          <div className="grid min-w-[640px] grid-cols-[10rem_1fr_1fr] border border-slate-200 text-sm dark:border-slate-700">
            <div className="bg-slate-100 p-2 font-semibold dark:bg-slate-800">{t("reviewItem")}</div>
            <LocaleHeading locale="en" current={currentLocale} />
            <LocaleHeading locale="ja" current={currentLocale} />
            {axes.map(({ key }) => {
              const payload =
                key === "theme"
                  ? patched.theme_draft
                  : key === "style"
                    ? patched.style_draft
                    : patched.template_draft;
              const values = localizedAxis(payload, sourceLocale);
              return (
                <ReviewRow
                  key={key}
                  label={t(`reviewAxes.${key}`)}
                  en={`${values.en.name || t("missing")} · ${values.en.description || "—"}`}
                  ja={`${values.ja.name || t("missing")} · ${values.ja.description || "—"}`}
                />
              );
            })}
            {fields.map((field) => (
              <ReviewRow
                key={field.key}
                label={t("reviewField", { key: field.key })}
                en={`${field.en.label || t("missing")} · ${field.en.default_text || "—"}`}
                ja={`${field.ja.label || t("missing")} · ${field.ja.default_text || "—"}`}
              />
            ))}
          </div>
        </div>

        {error ? <p className="mt-4 text-sm text-red-600">{error}</p> : null}
        <div className="mt-5 flex justify-end gap-2">
          <button type="button" className="header-btn" disabled={busy} onClick={onClose}>{t("cancel")}</button>
          <button
            type="button"
            className="header-btn header-btn-active"
            disabled={!canApprove}
            onClick={() => void onApprove(patched)}
          >
            {busy ? t("approving") : t("approveAndActivate")}
          </button>
        </div>
      </div>
    </div>
  );
}

function LocaleHeading({ locale, current }: { locale: PresentationLocale; current: PresentationLocale }) {
  return (
    <div className="border-l border-slate-200 bg-slate-100 p-2 font-semibold dark:border-slate-700 dark:bg-slate-800">
      {locale.toUpperCase()}
      {locale === current ? <span className="ml-2 text-xs text-blue-600">●</span> : null}
    </div>
  );
}

function ReviewRow({ label, en, ja }: { label: string; en: string; ja: string }) {
  return (
    <>
      <div className="border-t border-slate-200 p-2 font-medium dark:border-slate-700">{label}</div>
      <div className="border-l border-t border-slate-200 p-2 dark:border-slate-700">{en}</div>
      <div className="border-l border-t border-slate-200 p-2 dark:border-slate-700">{ja}</div>
    </>
  );
}

function axisEditValues(payload: Record<string, unknown>, sourceLocale: PresentationLocale) {
  const localized = localizedAxis(payload, sourceLocale)[sourceLocale];
  return {
    name: String(localized.name || payload.name || ""),
    description: String(localized.description ?? payload.description ?? ""),
  };
}

function applyAxisEdit(
  payload: Record<string, unknown>,
  sourceLocale: PresentationLocale,
  edit: { name: string; description: string },
) {
  const next = structuredClone(payload);
  const name = edit.name.trim();
  const description = edit.description;
  next.name = name;
  next.description = description;
  const content =
    next.content && typeof next.content === "object" && !Array.isArray(next.content)
      ? { ...(next.content as Record<string, unknown>) }
      : {};
  const i18nRaw = content._i18n;
  const i18n =
    i18nRaw && typeof i18nRaw === "object" && !Array.isArray(i18nRaw)
      ? { ...(i18nRaw as Record<string, unknown>) }
      : {};
  const localeValues =
    i18n[sourceLocale] && typeof i18n[sourceLocale] === "object" && !Array.isArray(i18n[sourceLocale])
      ? { ...(i18n[sourceLocale] as Record<string, unknown>) }
      : {};
  i18n[sourceLocale] = { ...localeValues, name, description };
  content._i18n = i18n;
  next.content = content;
  return next;
}

function localizedAxis(payload: Record<string, unknown>, sourceLocale: PresentationLocale) {
  const content = payload.content as { _i18n?: Partial<Record<PresentationLocale, LocalizedValues>> } | undefined;
  const legacy = { name: String(payload.name || ""), description: String(payload.description || "") };
  return {
    en: content?._i18n?.en || (sourceLocale === "en" ? legacy : {}),
    ja: content?._i18n?.ja || (sourceLocale === "ja" ? legacy : {}),
  };
}

function coverFields(draft: PresentationDraft) {
  const config = draft.template_draft.config as Record<string, unknown> | undefined;
  const fields = Array.isArray(config?.cover_fields) ? config.cover_fields : [];
  return fields.flatMap((raw) => {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) return [];
    const field = raw as Record<string, unknown>;
    const content = field.content as { _i18n?: Partial<Record<PresentationLocale, LocalizedValues>> } | undefined;
    return [{
      key: String(field.key || ""),
      en: content?._i18n?.en || {},
      ja: content?._i18n?.ja || {},
    }];
  });
}

function countMissing(draft: PresentationDraft) {
  let missing = 0;
  for (const payload of [draft.theme_draft, draft.style_draft, draft.template_draft]) {
    const localized = localizedAxis(payload, draft.source_locale as PresentationLocale);
    for (const locale of ["en", "ja"] as const) {
      if (!localized[locale].name) missing += 1;
      if (localized[locale].description === undefined) missing += 1;
    }
  }
  for (const field of coverFields(draft)) {
    if (!field.en.label) missing += 1;
    if (!field.ja.label) missing += 1;
  }
  return missing;
}
