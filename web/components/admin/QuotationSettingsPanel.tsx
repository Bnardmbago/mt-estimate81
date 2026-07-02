"use client";

import { FormEvent, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { apiJson } from "@/lib/api";

type QuotationSettings = {
  special_notes_title_ja: string;
  special_notes_title_en: string;
  special_notes_body_ja: string;
  special_notes_body_en: string;
};

const inputClassName =
  "w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

export default function QuotationSettingsPanel() {
  const t = useTranslations("admin.quotationSettings");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [titleJa, setTitleJa] = useState("");
  const [titleEn, setTitleEn] = useState("");
  const [bodyJa, setBodyJa] = useState("");
  const [bodyEn, setBodyEn] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const data = await apiJson<QuotationSettings>("/admin/quotation-settings");
        setTitleJa(data.special_notes_title_ja);
        setTitleEn(data.special_notes_title_en);
        setBodyJa(data.special_notes_body_ja);
        setBodyEn(data.special_notes_body_en);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : t("loadError"));
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [t]);

  async function handleSave(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setSaved(false);

    try {
      const data = await apiJson<QuotationSettings>("/admin/quotation-settings", {
        method: "PATCH",
        body: JSON.stringify({
          special_notes_title_ja: titleJa,
          special_notes_title_en: titleEn,
          special_notes_body_ja: bodyJa,
          special_notes_body_en: bodyEn,
        }),
      });
      setTitleJa(data.special_notes_title_ja);
      setTitleEn(data.special_notes_title_en);
      setBodyJa(data.special_notes_body_ja);
      setBodyEn(data.special_notes_body_en);
      setSaved(true);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : t("saveError"));
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <p className="text-sm text-gray-600">{t("loading")}</p>;
  }

  return (
    <form className="space-y-6" onSubmit={handleSave}>
      <p className="text-sm text-gray-600">{t("description")}</p>

      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-700">
        <p className="font-medium text-gray-900">{t("placeholdersTitle")}</p>
        <ul className="mt-2 list-inside list-disc space-y-1">
          <li>{t("placeholderIssueDate")}</li>
          <li>{t("placeholderSpecialPrice")}</li>
          <li>{t("placeholderOriginalPrice")}</li>
          <li>{t("placeholderDiscountPercent")}</li>
          <li>{t("placeholderDiscountAmount")}</li>
        </ul>
        <p className="mt-2 text-xs text-gray-500">{t("visibilityNote")}</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="space-y-3">
          <h3 className="text-sm font-semibold text-gray-900">{t("jaSection")}</h3>
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-gray-700">{t("titleLabel")}</span>
            <input
              type="text"
              value={titleJa}
              onChange={(event) => setTitleJa(event.target.value)}
              className={inputClassName}
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-gray-700">{t("bodyLabel")}</span>
            <textarea
              value={bodyJa}
              onChange={(event) => setBodyJa(event.target.value)}
              rows={8}
              className={inputClassName}
            />
          </label>
        </section>

        <section className="space-y-3">
          <h3 className="text-sm font-semibold text-gray-900">{t("enSection")}</h3>
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-gray-700">{t("titleLabel")}</span>
            <input
              type="text"
              value={titleEn}
              onChange={(event) => setTitleEn(event.target.value)}
              className={inputClassName}
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-gray-700">{t("bodyLabel")}</span>
            <textarea
              value={bodyEn}
              onChange={(event) => setBodyEn(event.target.value)}
              rows={8}
              className={inputClassName}
            />
          </label>
        </section>
      </div>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      {saved ? <p className="text-sm text-green-700">{t("saved")}</p> : null}

      <button
        type="submit"
        disabled={saving}
        className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {saving ? t("saving") : t("save")}
      </button>
    </form>
  );
}
