"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { apiFetch, apiJson } from "@/lib/api";

type QuotationSettings = {
  special_notes_title_ja: string;
  special_notes_title_en: string;
  special_notes_body_ja: string;
  special_notes_body_en: string;
  invoice_registration_number: string;
  contact_person: string;
  company_postal_code: string;
  company_address: string;
  company_tel: string;
  company_email: string;
  bank_details_ja: string;
  bank_details_en: string;
  has_custom_logo: boolean;
  logo_url: string;
};

const inputClassName =
  "w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

export default function QuotationSettingsPanel() {
  const t = useTranslations("admin.quotationSettings");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [titleJa, setTitleJa] = useState("");
  const [titleEn, setTitleEn] = useState("");
  const [bodyJa, setBodyJa] = useState("");
  const [bodyEn, setBodyEn] = useState("");
  const [registrationNumber, setRegistrationNumber] = useState("");
  const [contactPerson, setContactPerson] = useState("");
  const [postalCode, setPostalCode] = useState("");
  const [address, setAddress] = useState("");
  const [tel, setTel] = useState("");
  const [email, setEmail] = useState("");
  const [bankJa, setBankJa] = useState("");
  const [bankEn, setBankEn] = useState("");
  const [hasCustomLogo, setHasCustomLogo] = useState(false);
  const [logoPreviewUrl, setLogoPreviewUrl] = useState("/api/admin/quotation-settings/logo");

  function applySettings(data: QuotationSettings) {
    setTitleJa(data.special_notes_title_ja);
    setTitleEn(data.special_notes_title_en);
    setBodyJa(data.special_notes_body_ja);
    setBodyEn(data.special_notes_body_en);
    setRegistrationNumber(data.invoice_registration_number);
    setContactPerson(data.contact_person);
    setPostalCode(data.company_postal_code);
    setAddress(data.company_address);
    setTel(data.company_tel);
    setEmail(data.company_email);
    setBankJa(data.bank_details_ja);
    setBankEn(data.bank_details_en);
    setHasCustomLogo(data.has_custom_logo);
    setLogoPreviewUrl(`/api/admin/quotation-settings/logo?t=${Date.now()}`);
  }

  useEffect(() => {
    async function load() {
      try {
        const data = await apiJson<QuotationSettings>("/admin/quotation-settings");
        applySettings(data);
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
          invoice_registration_number: registrationNumber,
          contact_person: contactPerson,
          company_postal_code: postalCode,
          company_address: address,
          company_tel: tel,
          company_email: email,
          bank_details_ja: bankJa,
          bank_details_en: bankEn,
        }),
      });
      applySettings(data);
      setSaved(true);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : t("saveError"));
    } finally {
      setSaving(false);
    }
  }

  async function handleLogoUpload(file: File | null) {
    if (!file) {
      return;
    }
    setUploadingLogo(true);
    setError(null);
    setSaved(false);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await apiFetch("/admin/quotation-settings/logo", {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(
          (payload && typeof payload === "object" && "detail" in payload
            ? (payload as { detail?: { error?: string } }).detail?.error
            : null) || t("logoUploadError"),
        );
      }
      const data = (await response.json()) as QuotationSettings;
      applySettings(data);
      setSaved(true);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : t("logoUploadError"));
    } finally {
      setUploadingLogo(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }

  async function handleLogoReset() {
    setUploadingLogo(true);
    setError(null);
    setSaved(false);
    try {
      const data = await apiJson<QuotationSettings>("/admin/quotation-settings/logo", {
        method: "DELETE",
      });
      applySettings(data);
      setSaved(true);
    } catch (resetError) {
      setError(resetError instanceof Error ? resetError.message : t("logoResetError"));
    } finally {
      setUploadingLogo(false);
    }
  }

  if (loading) {
    return <p className="text-sm text-gray-600">{t("loading")}</p>;
  }

  return (
    <form className="space-y-6" onSubmit={handleSave}>
      <p className="text-sm text-gray-600">{t("description")}</p>

      <section className="space-y-4 rounded-lg border border-gray-200 bg-white p-4">
        <h3 className="text-sm font-semibold text-gray-900">{t("companySection")}</h3>

        <div className="flex flex-wrap items-start gap-4">
          <div className="rounded border border-gray-200 bg-gray-50 p-3">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={logoPreviewUrl}
              alt={t("logoPreviewAlt")}
              className="h-16 w-auto max-w-[180px] object-contain"
            />
          </div>
          <div className="space-y-2 text-sm">
            <p className="font-medium text-gray-700">{t("logoLabel")}</p>
            <p className="text-xs text-gray-500">{t("logoHint")}</p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={uploadingLogo}
                onClick={() => fileInputRef.current?.click()}
                className="rounded border border-gray-300 bg-white px-3 py-1.5 text-sm hover:bg-gray-50 disabled:opacity-50"
              >
                {uploadingLogo ? t("logoUploading") : t("logoUpload")}
              </button>
              {hasCustomLogo ? (
                <button
                  type="button"
                  disabled={uploadingLogo}
                  onClick={() => void handleLogoReset()}
                  className="rounded border border-gray-300 bg-white px-3 py-1.5 text-sm hover:bg-gray-50 disabled:opacity-50"
                >
                  {t("logoReset")}
                </button>
              ) : null}
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".png,.jpg,.jpeg,.svg,.webp,image/png,image/jpeg,image/svg+xml,image/webp"
              className="hidden"
              onChange={(event) => void handleLogoUpload(event.target.files?.[0] ?? null)}
            />
          </div>
        </div>

        <label className="block max-w-md text-sm">
          <span className="mb-1 block font-medium text-gray-700">{t("postalCodeLabel")}</span>
          <input
            type="text"
            value={postalCode}
            onChange={(event) => setPostalCode(event.target.value)}
            className={inputClassName}
            placeholder={t("postalCodePlaceholder")}
          />
        </label>

        <label className="block max-w-xl text-sm">
          <span className="mb-1 block font-medium text-gray-700">{t("addressLabel")}</span>
          <textarea
            value={address}
            onChange={(event) => setAddress(event.target.value)}
            rows={3}
            className={inputClassName}
            placeholder={t("addressPlaceholder")}
          />
          <span className="mt-1 block text-xs text-gray-500">{t("addressHint")}</span>
        </label>

        <div className="grid gap-4 sm:grid-cols-2 max-w-xl">
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-gray-700">{t("telLabel")}</span>
            <input
              type="text"
              value={tel}
              onChange={(event) => setTel(event.target.value)}
              className={inputClassName}
              placeholder={t("telPlaceholder")}
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-gray-700">{t("emailLabel")}</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className={inputClassName}
              placeholder={t("emailPlaceholder")}
            />
          </label>
        </div>
      </section>

      <section className="space-y-4 rounded-lg border border-gray-200 bg-white p-4">
        <h3 className="text-sm font-semibold text-gray-900">{t("bankSection")}</h3>
        <div className="grid gap-6 lg:grid-cols-2">
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-gray-700">{t("bankJaLabel")}</span>
            <textarea
              value={bankJa}
              onChange={(event) => setBankJa(event.target.value)}
              rows={4}
              className={inputClassName}
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-gray-700">{t("bankEnLabel")}</span>
            <textarea
              value={bankEn}
              onChange={(event) => setBankEn(event.target.value)}
              rows={4}
              className={inputClassName}
            />
          </label>
        </div>
      </section>

      <label className="block max-w-md text-sm">
        <span className="mb-1 block font-medium text-gray-700">
          {t("registrationNumberLabel")}
        </span>
        <input
          type="text"
          value={registrationNumber}
          onChange={(event) => setRegistrationNumber(event.target.value)}
          className={inputClassName}
          placeholder={t("registrationNumberPlaceholder")}
        />
        <span className="mt-1 block text-xs text-gray-500">{t("registrationNumberHint")}</span>
      </label>

      <label className="block max-w-md text-sm">
        <span className="mb-1 block font-medium text-gray-700">
          {t("contactPersonLabel")}
        </span>
        <input
          type="text"
          value={contactPerson}
          onChange={(event) => setContactPerson(event.target.value)}
          className={inputClassName}
          placeholder={t("contactPersonPlaceholder")}
        />
        <span className="mt-1 block text-xs text-gray-500">{t("contactPersonHint")}</span>
      </label>

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
