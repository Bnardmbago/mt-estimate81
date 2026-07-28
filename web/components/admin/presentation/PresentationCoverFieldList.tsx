"use client";

import { useTranslations } from "next-intl";
import { normalizeGeometry } from "@/lib/cover-geometry";
import type { CoverField } from "./PresentationCoverPreview";
import PresentationTextStyleControls from "./PresentationTextStyleControls";

type Props = {
  fields: CoverField[];
  locale: "en" | "ja";
  selectedKey: string | null;
  onSelect: (key: string) => void;
  onChange: (fields: CoverField[]) => void;
};

export default function PresentationCoverFieldList({
  fields,
  locale,
  selectedKey,
  onSelect,
  onChange,
}: Props) {
  const t = useTranslations("admin.presentation.cover");
  const hasExplicitTitle = fields.some((field) => field.emphasis === "title");

  function update(index: number, patch: Partial<CoverField>) {
    onChange(fields.map((field, fieldIndex) => fieldIndex === index ? { ...field, ...patch } : field));
  }

  function updateContent(index: number, patch: { label?: string; default_text?: string }) {
    const field = fields[index];
    const i18n = field.content?._i18n || {};
    const current = i18n[locale] || {};
    update(index, {
      content: {
        ...(field.content || {}),
        _i18n: {
          ...i18n,
          [locale]: { ...current, ...patch },
        },
      },
    });
  }

  function move(index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= fields.length) return;
    const next = [...fields];
    [next[index], next[target]] = [next[target], next[index]];
    onChange(next);
  }

  function addField() {
    let suffix = fields.length + 1;
    while (fields.some((field) => field.key === `field_${suffix}`)) suffix += 1;
    onChange([
      ...fields,
      {
        key: `field_${suffix}`,
        content: { _i18n: { [locale]: { label: t("newFieldLabel"), default_text: "" } } },
        required: false,
      },
    ]);
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">{t("coverFields")}</h3>
          <p className="mt-1 text-xs text-slate-500">{t("fieldLocaleHint", { locale: locale.toUpperCase() })}</p>
        </div>
        <button type="button" className="header-btn text-xs" onClick={addField}>{t("addField")}</button>
      </div>
      {fields.length === 0 ? (
        <p className="mt-3 text-sm text-slate-500">{t("noFields")}</p>
      ) : (
        <ol className="mt-3 space-y-3">
          {fields.map((field, index) => {
            const localized = field.content?._i18n?.[locale] || {};
            return (
              <li
                key={field.key}
                className={`rounded border p-3 ${
                  selectedKey === field.key
                    ? "border-blue-500 ring-1 ring-blue-500"
                    : "border-slate-200 dark:border-slate-700"
                }`}
                role="button"
                tabIndex={0}
                aria-pressed={selectedKey === field.key}
                onClick={() => onSelect(field.key)}
                onKeyDown={(event) => {
                  if (
                    event.target === event.currentTarget &&
                    (event.key === "Enter" || event.key === " ")
                  ) {
                    event.preventDefault();
                    onSelect(field.key);
                  }
                }}
              >
                <div className="flex items-start gap-3">
                  <span className="mt-2 rounded bg-slate-100 px-2 py-1 text-xs dark:bg-slate-800">{index + 1}</span>
                  <div className="grid min-w-0 flex-1 gap-3 sm:grid-cols-2">
                    <TextInput
                      label={t("fieldKey")}
                      value={field.key}
                      onChange={(key) => {
                        update(index, { key });
                        if (selectedKey === field.key) onSelect(key);
                      }}
                    />
                    <TextInput
                      label={t("fieldLabel")}
                      value={localized.label || ""}
                      onChange={(label) => updateContent(index, { label })}
                    />
                    <TextInput
                      label={t("defaultText")}
                      value={localized.default_text || ""}
                      onChange={(default_text) => updateContent(index, { default_text })}
                    />
                    <TextInput
                      label={t("autoFill")}
                      value={field.auto_fill || ""}
                      placeholder={t("autoFillPlaceholder")}
                      onChange={(auto_fill) => update(index, { auto_fill: auto_fill || undefined })}
                    />
                    <label className="flex items-center gap-2 text-xs">
                      <input
                        type="checkbox"
                        checked={Boolean(field.required)}
                        onChange={(event) => update(index, { required: event.target.checked })}
                      />
                      {t("required")}
                    </label>
                  </div>
                  <div className="flex shrink-0 flex-col gap-1">
                    <button
                      type="button"
                      className="header-btn-icon text-xs"
                      aria-label={t("moveUp")}
                      disabled={index === 0}
                      onClick={(event) => {
                        event.stopPropagation();
                        move(index, -1);
                      }}
                    >
                      ↑
                    </button>
                    <button
                      type="button"
                      className="header-btn-icon text-xs"
                      aria-label={t("moveDown")}
                      disabled={index === fields.length - 1}
                      onClick={(event) => {
                        event.stopPropagation();
                        move(index, 1);
                      }}
                    >
                      ↓
                    </button>
                    <button
                      type="button"
                      className="header-btn-icon text-xs text-red-700"
                      aria-label={t("removeField")}
                      onClick={(event) => {
                        event.stopPropagation();
                        if (window.confirm(t("removeFieldConfirm"))) {
                          onChange(fields.filter((_, fieldIndex) => fieldIndex !== index));
                        }
                      }}
                    >
                      ×
                    </button>
                  </div>
                </div>
                {selectedKey === field.key ? (
                  <PresentationTextStyleControls
                    field={field}
                    onChange={(patch) => update(index, patch)}
                    onResetGeometry={() => {
                      const withoutGeometry = { ...field };
                      delete withoutGeometry.geometry;
                      onChange(fields.map((candidate, fieldIndex) =>
                        fieldIndex === index ? withoutGeometry : candidate
                      ));
                    }}
                    onCreateGeometry={() => update(index, {
                      geometry: normalizeGeometry({
                        x_pct: 10,
                        y_pct: Math.min(80, 12 + index * 10),
                        width_pct: 80,
                        height_pct: field.emphasis === "title" || (!hasExplicitTitle && index === 0) ? 14 : 8,
                        z_index: index + 1,
                      }),
                    })}
                  />
                ) : null}
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}

function TextInput({
  label,
  value,
  placeholder,
  onChange,
}: {
  label: string;
  value: string;
  placeholder?: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="text-xs">
      <span className="mb-1 block font-medium">{label}</span>
      <input
        className="w-full rounded border border-slate-300 px-2 py-1.5 dark:border-slate-600 dark:bg-slate-950"
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}
