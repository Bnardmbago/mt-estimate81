"use client";

import { useTranslations } from "next-intl";
import type { ProposalLocale } from "@/lib/proposal-types";

type Props = {
  value: ProposalLocale;
  disabled?: boolean;
  onChange: (locale: ProposalLocale) => void;
};

export default function ProposalExportLocaleSelector({
  value,
  disabled = false,
  onChange,
}: Props) {
  const t = useTranslations("proposal.exportLocale");

  return (
    <fieldset>
      <legend className="mb-2 text-sm font-medium text-slate-700 dark:text-slate-200">
        {t("label")}
      </legend>
      <div className="flex flex-wrap gap-4">
        {(["ja", "en"] as const).map((locale) => (
          <label
            key={locale}
            className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200"
          >
            <input
              type="radio"
              name="proposal-export-locale"
              checked={value === locale}
              disabled={disabled}
              onChange={() => onChange(locale)}
              className="border-slate-300 text-indigo-600"
            />
            {t(locale === "ja" ? "ja" : "en")}
          </label>
        ))}
      </div>
      <p className="mt-1 text-xs text-slate-500">{t("defaultHint")}</p>
    </fieldset>
  );
}
