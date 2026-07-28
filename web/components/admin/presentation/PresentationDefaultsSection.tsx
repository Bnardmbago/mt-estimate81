"use client";

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import {
  setAdminPresentationDefaults,
  type PresentationDefaults,
  type PresentationPresetDetail,
} from "@/lib/presentation";
import { templateHasCoverConfig } from "@/lib/cover-template-defaults";

type Props = {
  defaults: PresentationDefaults;
  themes: PresentationPresetDetail[];
  styles: PresentationPresetDetail[];
  templates: PresentationPresetDetail[];
  onChanged: () => Promise<void>;
};

const NO_COVER = "";

export default function PresentationDefaultsSection({
  defaults,
  themes,
  styles,
  templates,
  onChanged,
}: Props) {
  const t = useTranslations("admin.presentation");
  const [value, setValue] = useState({
    ...defaults,
    cover_template_id: defaults.cover_template_id || NO_COVER,
  });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const coverPresets = useMemo(
    () => templates.filter((row) => templateHasCoverConfig(row.config) && row.is_active),
    [templates],
  );

  useEffect(() => {
    setValue({
      ...defaults,
      cover_template_id: defaults.cover_template_id || NO_COVER,
    });
  }, [defaults]);

  async function save() {
    setSaving(true);
    setMessage(null);
    try {
      await setAdminPresentationDefaults({
        theme_id: value.theme_id,
        style_id: value.style_id,
        template_id: value.template_id,
        cover_template_id: value.cover_template_id || null,
      });
      await onChanged();
      setMessage(t("saved"));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : t("saveError"));
    } finally {
      setSaving(false);
    }
  }

  const selectClass =
    "w-full rounded border border-slate-300 px-3 py-2 dark:border-slate-600 dark:bg-slate-950";

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
      <h3 className="text-base font-semibold">{t("defaultsTitle")}</h3>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{t("defaultsDescription")}</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <label className="text-sm">
          <span className="mb-1 block">{t("defaultTheme")}</span>
          <select
            className={selectClass}
            value={value.theme_id}
            onChange={(event) => setValue({ ...value, theme_id: event.target.value })}
          >
            {themes.map((row) => (
              <option key={row.id} value={row.id}>
                {row.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1 block">{t("defaultStyle")}</span>
          <select
            className={selectClass}
            value={value.style_id}
            onChange={(event) => setValue({ ...value, style_id: event.target.value })}
          >
            {styles.map((row) => (
              <option key={row.id} value={row.id}>
                {row.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1 block">{t("defaultTemplate")}</span>
          <select
            className={selectClass}
            value={value.template_id}
            onChange={(event) => setValue({ ...value, template_id: event.target.value })}
          >
            {templates.map((row) => (
              <option key={row.id} value={row.id}>
                {row.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1 block">{t("defaultCover")}</span>
          <select
            className={selectClass}
            value={value.cover_template_id || NO_COVER}
            onChange={(event) =>
              setValue({ ...value, cover_template_id: event.target.value })
            }
          >
            <option value={NO_COVER}>{t("defaultCoverNone")}</option>
            {coverPresets.map((row) => (
              <option key={row.id} value={row.id}>
                {row.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      {message ? <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">{message}</p> : null}
      <button type="button" className="header-btn mt-4" disabled={saving} onClick={() => void save()}>
        {saving ? t("saving") : t("saveDefaults")}
      </button>
    </section>
  );
}
