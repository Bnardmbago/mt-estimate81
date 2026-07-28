"use client";

import { useCallback, useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import {
  approvePresentationDraft,
  fetchAdminPresentationStyles,
  fetchAdminPresentationTemplates,
  fetchAdminPresentationThemes,
  fetchPresentationDefaults,
  fetchPresentationDrafts,
  updatePresentationDraft,
  type PresentationDefaults,
  type PresentationDraft,
  type PresentationLocale,
  type PresentationPresetDetail,
} from "@/lib/presentation";
import PresentationBilingualReview from "./PresentationBilingualReview";
import PresentationCoverTab from "./PresentationCoverTab";
import PresentationDefaultsSection from "./PresentationDefaultsSection";
import PresentationStyleEditor from "./PresentationStyleEditor";
import PresentationTemplateEditor from "./PresentationTemplateEditor";
import PresentationThemeEditor from "./PresentationThemeEditor";

type PresentationTab = "theme" | "style" | "template" | "cover" | "defaults";

const TABS: PresentationTab[] = ["theme", "style", "template", "cover", "defaults"];

export default function PresentationAdminShell() {
  const t = useTranslations("admin.presentation");
  const locale = useLocale() as PresentationLocale;
  const [activeTab, setActiveTab] = useState<PresentationTab>("theme");
  const [themes, setThemes] = useState<PresentationPresetDetail[]>([]);
  const [styles, setStyles] = useState<PresentationPresetDetail[]>([]);
  const [templates, setTemplates] = useState<PresentationPresetDetail[]>([]);
  const [drafts, setDrafts] = useState<PresentationDraft[]>([]);
  const [defaults, setDefaults] = useState<PresentationDefaults | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reviewDraft, setReviewDraft] = useState<PresentationDraft | null>(null);
  const [approving, setApproving] = useState(false);
  const [approvalError, setApprovalError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [themeRows, styleRows, templateRows, draftRows, defaultRows] = await Promise.all([
        fetchAdminPresentationThemes(),
        fetchAdminPresentationStyles(),
        fetchAdminPresentationTemplates(),
        fetchPresentationDrafts(),
        fetchPresentationDefaults(),
      ]);
      setThemes(themeRows);
      setStyles(styleRows);
      setTemplates(templateRows);
      setDrafts(draftRows);
      setDefaults(defaultRows);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : t("loadError"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void load();
  }, [load]);

  async function approveReviewedDraft(patch: {
    theme_draft: Record<string, unknown>;
    style_draft: Record<string, unknown>;
    template_draft: Record<string, unknown>;
  }) {
    if (!reviewDraft) return;
    setApproving(true);
    setApprovalError(null);
    try {
      await updatePresentationDraft(reviewDraft.id, patch);
      await approvePresentationDraft(reviewDraft.id, locale);
      setReviewDraft(null);
      await load();
    } catch (approveError) {
      setApprovalError(approveError instanceof Error ? approveError.message : t("saveError"));
    } finally {
      setApproving(false);
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-xl font-semibold">{t("title")}</h2>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{t("description")}</p>
      </header>

      <nav className="flex flex-wrap gap-2" aria-label={t("title")}>
        {TABS.map((tab) => (
          <button
            key={tab}
            type="button"
            className={activeTab === tab ? "header-btn header-btn-active" : "header-btn"}
            aria-current={activeTab === tab ? "page" : undefined}
            onClick={() => setActiveTab(tab)}
          >
            {t(`tabs.${tab}`)}
          </button>
        ))}
      </nav>

      {error ? (
        <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">
          {error}
          <button type="button" className="ml-3 underline" onClick={() => void load()}>
            {t("retry")}
          </button>
        </div>
      ) : null}

      {loading ? <p className="text-sm text-slate-600">{t("loading")}</p> : null}

      {!loading && activeTab === "theme" ? (
        <PresentationThemeEditor presets={themes} onChanged={load} />
      ) : null}
      {!loading && activeTab === "style" ? (
        <PresentationStyleEditor presets={styles} onChanged={load} />
      ) : null}
      {!loading && activeTab === "template" ? (
        <PresentationTemplateEditor presets={templates} onChanged={load} />
      ) : null}
      {!loading && activeTab === "cover" ? (
        <PresentationCoverTab
          drafts={drafts}
          templates={templates}
          onChanged={load}
          onRequestApprove={setReviewDraft}
        />
      ) : null}
      {!loading && activeTab === "defaults" && defaults ? (
        <PresentationDefaultsSection
          defaults={defaults}
          themes={themes}
          styles={styles}
          templates={templates}
          onChanged={load}
        />
      ) : null}
      <PresentationBilingualReview
        draft={reviewDraft}
        currentLocale={locale}
        busy={approving}
        error={approvalError}
        onClose={() => {
          if (!approving) {
            setReviewDraft(null);
            setApprovalError(null);
          }
        }}
        onApprove={approveReviewedDraft}
      />
    </div>
  );
}
