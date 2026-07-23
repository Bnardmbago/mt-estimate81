"use client";

import type { ProposalTable } from "@/lib/proposal-types";

type ProposalDataTableProps = {
  table: ProposalTable;
};

export default function ProposalDataTable({ table }: ProposalDataTableProps) {
  const headers = table.headers || [];
  const rows = table.rows || [];
  return (
    <div className="my-4 overflow-x-auto rounded-lg border border-[color:var(--proposal-border,#e2e8f0)]">
      <table className="min-w-full text-sm">
        <caption className="proposal-doc-heading mb-0 border-b-0 bg-[color:var(--proposal-primary-light,#e8eef4)] px-3 py-2 text-left text-sm font-semibold">
          {table.title}
        </caption>
        {headers.length ? (
          <thead>
            <tr className="bg-[color:var(--proposal-primary,#1e3a5f)] text-white">
              {headers.map((header) => (
                <th key={header} className="px-3 py-2 text-left font-medium">
                  {header}
                </th>
              ))}
            </tr>
          </thead>
        ) : null}
        <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
          {rows.map((row, rowIdx) => (
            <tr key={`${table.id}-${rowIdx}`} className="bg-white dark:bg-slate-900">
              {row.map((cell, cellIdx) => (
                <td key={`${table.id}-${rowIdx}-${cellIdx}`} className="px-3 py-2">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
