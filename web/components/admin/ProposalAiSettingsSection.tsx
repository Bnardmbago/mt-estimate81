"use client";

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { apiJson } from "@/lib/api";

type Purpose = "concise" | "standard" | "detailed";

type PurposePresetSummary = {
  purpose: Purpose;
  max_tokens: number;
  timeout_seconds: number;
  min_diagrams: number;
  min_tables_proposal: number;
  min_tables_poc: number;
};

type ProposalAiSettings = {
  assessment_purpose: Purpose;
  proposal_purpose: Purpose;
  poc_purpose: Purpose;
  presets: PurposePresetSummary[];
  purposes: Purpose[];
};

const inputClassName =
  "w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

export default function ProposalAiSettingsSection() {
  const t = useTranslations("admin.proposalAiSettings");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [settings, setSettings] = useState<ProposalAiSettings | null>(null);
  const [assessment, setAssessment] = useState<Purpose>("standard");
  const [proposal, setProposal] = useState<Purpose>("detailed");
  const [poc, setPoc] = useState<Purpose>("detailed");

  useEffect(() => {
    async function load() {
      try {
        const data = await apiJson<ProposalAiSettings>("/admin/proposal-ai-settings");
        setSettings(data);
        setAssessment(data.assessment_purpose);
        setProposal(data.proposal_purpose);
        setPoc(data.poc_purpose);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : t("loadError"));
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [t]);

  const presetByPurpose = useMemo(() => {
    const map = new Map<Purpose, PurposePresetSummary>();
    for (const preset of settings?.presets ?? []) {
      map.set(preset.purpose, preset);
    }
    return map;
  }, [settings]);

  function summarize(purpose: Purpose, part: "assessment" | "proposal" | "poc") {
    const preset = presetByPurpose.get(purpose);
    if (!preset) return "";
    const tables =
      part === "poc"
        ? preset.min_tables_poc
        : part === "proposal"
          ? preset.min_tables_proposal
          : 0;
    if (part === "assessment") {
      return t("summaryAssessment", {
        tokens: String(preset.max_tokens),
        timeout: String(preset.timeout_seconds),
      });
    }
    return t("summaryVisual", {
      tokens: String(preset.max_tokens),
      timeout: String(preset.timeout_seconds),
      diagrams: String(preset.min_diagrams),
      tables: String(tables),
    });
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const data = await apiJson<ProposalAiSettings>("/admin/proposal-ai-settings", {
        method: "PUT",
        body: JSON.stringify({
          assessment_purpose: assessment,
          proposal_purpose: proposal,
          poc_purpose: poc,
        }),
      });
      setSettings(data);
      setAssessment(data.assessment_purpose);
      setProposal(data.proposal_purpose);
      setPoc(data.poc_purpose);
      setSaved(true);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : t("saveError"));
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <p className="text-sm text-gray-500">{t("loading")}</p>;
  }

  if (!settings) {
    return (
      <p className="text-sm text-red-600" role="alert">
        {error || t("loadError")}
      </p>
    );
  }

  const purposes = settings.purposes;

  return (
    <section className="space-y-4 rounded-lg border border-gray-200 p-4">
      <div>
        <h3 className="text-base font-semibold text-gray-900">{t("title")}</h3>
        <p className="mt-1 text-sm text-gray-600">{t("description")}</p>
        <p className="mt-2 text-xs text-gray-500">{t("advancedHint")}</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-gray-700">{t("assessment")}</span>
          <select
            value={assessment}
            onChange={(event) => setAssessment(event.target.value as Purpose)}
            className={inputClassName}
          >
            {purposes.map((purpose) => (
              <option key={purpose} value={purpose}>
                {t(`purposes.${purpose}`)}
              </option>
            ))}
          </select>
          <span className="mt-1 block text-xs text-gray-500">
            {summarize(assessment, "assessment")}
          </span>
        </label>

        <label className="block text-sm">
          <span className="mb-1 block font-medium text-gray-700">{t("proposal")}</span>
          <select
            value={proposal}
            onChange={(event) => setProposal(event.target.value as Purpose)}
            className={inputClassName}
          >
            {purposes.map((purpose) => (
              <option key={purpose} value={purpose}>
                {t(`purposes.${purpose}`)}
              </option>
            ))}
          </select>
          <span className="mt-1 block text-xs text-gray-500">
            {summarize(proposal, "proposal")}
          </span>
        </label>

        <label className="block text-sm">
          <span className="mb-1 block font-medium text-gray-700">{t("poc")}</span>
          <select
            value={poc}
            onChange={(event) => setPoc(event.target.value as Purpose)}
            className={inputClassName}
          >
            {purposes.map((purpose) => (
              <option key={purpose} value={purpose}>
                {t(`purposes.${purpose}`)}
              </option>
            ))}
          </select>
          <span className="mt-1 block text-xs text-gray-500">{summarize(poc, "poc")}</span>
        </label>
      </div>

      {error && (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      )}
      {saved && <p className="text-sm text-green-600">{t("saved")}</p>}

      <button
        type="button"
        onClick={() => void handleSave()}
        disabled={saving}
        className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {saving ? t("saving") : t("save")}
      </button>
    </section>
  );
}
