"use client";

import { useTranslations } from "next-intl";

type FormulaRow = {
  metric: string;
  formula: string;
  notes?: string;
};

type FormulaSection = {
  title: string;
  description?: string;
  rows: FormulaRow[];
};

type FormulaSectionKey =
  | "effort"
  | "nrc"
  | "rc"
  | "discount"
  | "gantt"
  | "rateCard"
  | "contactAccess"
  | "variance";

const SECTION_ORDER: FormulaSectionKey[] = [
  "effort",
  "nrc",
  "rc",
  "discount",
  "gantt",
  "rateCard",
  "contactAccess",
  "variance",
];

function FormulaTable({
  title,
  description,
  rows,
  columns,
}: FormulaSection & {
  columns: { metric: string; formula: string; notes: string };
}) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-gray-900 sm:p-6">
      <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{title}</h3>
      {description ? (
        <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
          {description}
        </p>
      ) : null}
      <div className="mt-4 overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
        <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-700">
          <thead className="bg-slate-50 dark:bg-slate-800/80">
            <tr>
              <th className="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">
                {columns.metric}
              </th>
              <th className="min-w-[12rem] px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">
                {columns.formula}
              </th>
              <th className="min-w-[10rem] px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">
                {columns.notes}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 bg-white dark:divide-slate-700 dark:bg-gray-900">
            {rows.map((row, index) => (
              <tr
                key={`${title}-${index}`}
                className="transition-colors hover:bg-slate-50/80 dark:hover:bg-slate-800/40"
              >
                <td className="whitespace-nowrap px-4 py-3 font-medium text-slate-900 dark:text-slate-100">
                  {row.metric}
                </td>
                <td className="break-words px-4 py-3 font-mono text-xs leading-relaxed text-slate-800 dark:text-slate-200">
                  {row.formula}
                </td>
                <td className="break-words px-4 py-3 text-slate-600 dark:text-slate-400">
                  {row.notes ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default function FormulasReference() {
  const t = useTranslations("admin.formulas");

  const columns = {
    metric: t("columns.metric"),
    formula: t("columns.formula"),
    notes: t("columns.notes"),
  };

  const sections: FormulaSection[] = SECTION_ORDER.map((key) => ({
    title: t(`${key}.title`),
    description: t.has(`${key}.description`) ? t(`${key}.description`) : undefined,
    rows: t.raw(`${key}.rows`) as FormulaRow[],
  }));

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">{t("title")}</h2>
        <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">{t("intro")}</p>
      </div>
      {sections.map((section) => (
        <FormulaTable key={section.title} {...section} columns={columns} />
      ))}
    </div>
  );
}
