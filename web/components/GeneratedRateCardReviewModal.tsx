"use client";

import { useTranslations } from "next-intl";

const DEVELOPMENT_APPROACH_OPTIONS = [
  "traditional",
  "ai_assisted",
  "hybrid",
  "low_code",
] as const;

type DevelopmentApproach = (typeof DEVELOPMENT_APPROACH_OPTIONS)[number];

type RoleRate = {
  name: string;
  hourly_rate_jpy: number;
  daily_rate_jpy?: number;
};

type LineItem = {
  name: string;
  amount_jpy: number;
};

export type GeneratedRateCardSettings = {
  development_approach: DevelopmentApproach;
  roles: RoleRate[];
  phases: Array<{ name: string; percentage: number }>;
  contingency_rate: number;
  overhead_rate: number;
  tax_rate: number;
  productivity: { hours_per_feature_default: number };
  setup_cost_items: LineItem[];
  monthly_rc_items: LineItem[];
};

export type GeneratedRateCardPreview = {
  name: string;
  settings: GeneratedRateCardSettings;
  generation_notes: string;
  used_defaults: boolean;
  default_fields: string[];
};

type GeneratedRateCardReviewModalProps = {
  open: boolean;
  preview: GeneratedRateCardPreview | null;
  saving: boolean;
  saveLabel?: string;
  onClose: () => void;
  onChange: (preview: GeneratedRateCardPreview) => void;
  onSave: () => void;
};

const inputClassName =
  "w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500";

export default function GeneratedRateCardReviewModal({
  open,
  preview,
  saving,
  saveLabel,
  onClose,
  onChange,
  onSave,
}: GeneratedRateCardReviewModalProps) {
  const t = useTranslations("review.rateCardPanel");
  const tRateCards = useTranslations("rateCards");

  if (!open || !preview) {
    return null;
  }

  const { settings } = preview;

  function updateSettings(next: Partial<GeneratedRateCardSettings>) {
    if (!preview) {
      return;
    }
    onChange({
      ...preview,
      settings: { ...settings, ...next },
    });
  }

  function updateRole(index: number, field: "name" | "hourly_rate_jpy", value: string) {
    const roles = [...settings.roles];
    const role = { ...roles[index] };
    if (field === "name") {
      role.name = value;
    } else {
      role.hourly_rate_jpy = value === "" ? 0 : Number(value);
    }
    roles[index] = role;
    updateSettings({ roles });
  }

  function updateRate(field: "contingency_rate" | "overhead_rate" | "tax_rate", value: string) {
    const numeric = value === "" ? 0 : Number(value) / 100;
    updateSettings({ [field]: numeric });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div
        className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-lg bg-white p-6 shadow-lg"
        role="dialog"
        aria-labelledby="generated-rate-card-title"
      >
        <h3 id="generated-rate-card-title" className="text-lg font-semibold text-gray-900">
          {t("reviewModalTitle")}
        </h3>
        <p className="mt-1 text-sm text-gray-600">{t("reviewModalDescription")}</p>

        {preview.used_defaults && (
          <p className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
            {t("usedDefaultsNotice")}
          </p>
        )}

        {preview.generation_notes && (
          <p className="mt-3 text-sm text-gray-600">{preview.generation_notes}</p>
        )}

        <div className="mt-4 space-y-4">
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-gray-700">{tRateCards("cardName")}</span>
            <input
              type="text"
              value={preview.name}
              onChange={(event) => onChange({ ...preview, name: event.target.value })}
              className={inputClassName}
            />
          </label>

          <label className="block text-sm">
            <span className="mb-1 block font-medium text-gray-700">
              {tRateCards("developmentApproach")}
            </span>
            <select
              value={settings.development_approach}
              onChange={(event) =>
                updateSettings({
                  development_approach: event.target.value as DevelopmentApproach,
                })
              }
              className={inputClassName}
            >
              {DEVELOPMENT_APPROACH_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {tRateCards(`developmentApproachOptions.${option}.label`)}
                </option>
              ))}
            </select>
          </label>

          <div>
            <h4 className="mb-2 text-sm font-medium text-gray-800">{tRateCards("roles")}</h4>
            <div className="space-y-2">
              {settings.roles.map((role, index) => (
                <div key={`role-${index}`} className="grid gap-2 sm:grid-cols-2">
                  <input
                    type="text"
                    value={role.name}
                    onChange={(event) => updateRole(index, "name", event.target.value)}
                    className={inputClassName}
                    placeholder={tRateCards("roleName")}
                  />
                  <input
                    type="number"
                    value={role.hourly_rate_jpy}
                    onChange={(event) => updateRole(index, "hourly_rate_jpy", event.target.value)}
                    className={inputClassName}
                    placeholder={tRateCards("hourlyRate")}
                  />
                </div>
              ))}
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-gray-700">{tRateCards("contingency")}</span>
              <input
                type="number"
                min="0"
                max="100"
                value={Math.round(settings.contingency_rate * 100)}
                onChange={(event) => updateRate("contingency_rate", event.target.value)}
                className={inputClassName}
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-gray-700">{tRateCards("overhead")}</span>
              <input
                type="number"
                min="0"
                max="100"
                value={Math.round(settings.overhead_rate * 100)}
                onChange={(event) => updateRate("overhead_rate", event.target.value)}
                className={inputClassName}
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-gray-700">{tRateCards("tax")}</span>
              <input
                type="number"
                min="0"
                max="100"
                value={Math.round(settings.tax_rate * 100)}
                onChange={(event) => updateRate("tax_rate", event.target.value)}
                className={inputClassName}
              />
            </label>
          </div>

          <label className="block text-sm">
            <span className="mb-1 block font-medium text-gray-700">
              {t("productivityDefaultHours")}
            </span>
            <input
              type="number"
              min="1"
              value={settings.productivity.hours_per_feature_default}
              onChange={(event) =>
                updateSettings({
                  productivity: {
                    hours_per_feature_default:
                      event.target.value === "" ? 1 : Number(event.target.value),
                  },
                })
              }
              className={`${inputClassName} max-w-xs`}
            />
          </label>
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="rounded border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50 disabled:opacity-50"
          >
            {t("reviewCancel")}
          </button>
          <button
            type="button"
            onClick={onSave}
            disabled={saving || !preview.name.trim()}
            className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {saving ? t("reviewSaving") : (saveLabel ?? t("reviewSave"))}
          </button>
        </div>
      </div>
    </div>
  );
}
