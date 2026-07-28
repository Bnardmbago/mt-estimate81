"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import PresentationSelectors, {
  NO_COVER_PRESET,
  templateHasCover,
} from "@/components/proposal/PresentationSelectors";
import ProposalCoverFields from "@/components/proposal/ProposalCoverFields";
import {
  fetchPresentationDefaults,
  fetchPresentationStyles,
  fetchPresentationTemplate,
  fetchPresentationTemplates,
  fetchPresentationThemes,
  type PresentationPresetSummary,
} from "@/lib/presentation";
import type {
  ProposalCoverField,
  ProposalCoverValues,
  ProposalLocale,
} from "@/lib/proposal-types";

export type EstimatePresentationState = {
  themeId: string;
  styleId: string;
  templateId: string;
  coverPresetId: string;
  includeCover: boolean | null;
  coverValues: ProposalCoverValues;
};

type Props = {
  value: EstimatePresentationState;
  locale: ProposalLocale;
  disabled?: boolean;
  onChange: (value: EstimatePresentationState) => void;
};

export default function EstimatePresentationControls({
  value,
  locale,
  disabled = false,
  onChange,
}: Props) {
  const t = useTranslations("export");
  const [themes, setThemes] = useState<PresentationPresetSummary[]>([]);
  const [styles, setStyles] = useState<PresentationPresetSummary[]>([]);
  const [templates, setTemplates] = useState<PresentationPresetSummary[]>([]);
  const [coverFields, setCoverFields] = useState<ProposalCoverField[]>([]);
  const [loadingTemplate, setLoadingTemplate] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void Promise.all([
      fetchPresentationThemes(),
      fetchPresentationStyles(),
      fetchPresentationTemplates(),
      fetchPresentationDefaults().catch(() => null),
    ])
      .then(([themeRows, styleRows, templateRows, defaults]) => {
        if (cancelled) return;
        setThemes(themeRows);
        setStyles(styleRows);
        setTemplates(templateRows);
        const nextTemplateId =
          value.templateId ||
          templateRows.find((row) => row.is_default)?.id ||
          templateRows[0]?.id ||
          "";
        const defaultCover =
          value.coverPresetId ||
          defaults?.cover_template_id ||
          (templateRows.find((row) => row.id === nextTemplateId && templateHasCover(row))?.id ??
            NO_COVER_PRESET);
        onChange({
          ...value,
          themeId:
            value.themeId ||
            themeRows.find((row) => row.is_default)?.id ||
            themeRows[0]?.id ||
            "",
          styleId:
            value.styleId ||
            styleRows.find((row) => row.is_default)?.id ||
            styleRows[0]?.id ||
            "",
          templateId: nextTemplateId,
          coverPresetId: defaultCover,
          includeCover: defaultCover ? true : false,
        });
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
    // Initial catalog load only; value updates are handled by controlled callbacks.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!value.coverPresetId) {
      setCoverFields([]);
      setLoadingTemplate(false);
      return;
    }
    let cancelled = false;
    setLoadingTemplate(true);
    void fetchPresentationTemplate(value.coverPresetId)
      .then((detail) => {
        if (cancelled) return;
        setCoverFields(asCoverFields(detail.config.cover_fields));
      })
      .catch(() => {
        if (!cancelled) setCoverFields([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingTemplate(false);
      });
    return () => {
      cancelled = true;
    };
  }, [value.coverPresetId]);

  if (themes.length === 0 || styles.length === 0 || templates.length === 0) {
    return null;
  }

  return (
    <section className="mb-4 rounded-lg border border-slate-200 p-4 dark:border-slate-700">
      <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
        {t("presentationTitle")}
      </h3>
      <div className="mt-3">
        <PresentationSelectors
          themes={themes}
          styles={styles}
          templates={templates}
          themeId={value.themeId}
          styleId={value.styleId}
          templateId={value.templateId}
          coverPresetId={value.coverPresetId || NO_COVER_PRESET}
          disabled={disabled}
          compact
          showCoverPreset
          onThemeChange={(themeId) => onChange({ ...value, themeId })}
          onStyleChange={(styleId) => onChange({ ...value, styleId })}
          onTemplateChange={(templateId) => onChange({ ...value, templateId })}
          onCoverPresetChange={(coverPresetId) =>
            onChange({
              ...value,
              coverPresetId,
              includeCover: Boolean(coverPresetId),
            })
          }
        />
      </div>
      {value.coverPresetId ? (
        <ProposalCoverFields
          fields={coverFields}
          values={value.coverValues}
          locale={locale}
          disabled={disabled || loadingTemplate}
          onSave={async (coverValues) => {
            onChange({ ...value, coverValues });
          }}
        />
      ) : null}
    </section>
  );
}

function asCoverFields(value: unknown): ProposalCoverField[] {
  if (!Array.isArray(value)) return [];
  return value.filter(
    (field): field is ProposalCoverField =>
      typeof field === "object" &&
      field !== null &&
      typeof (field as { key?: unknown }).key === "string",
  );
}
