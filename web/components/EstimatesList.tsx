"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { apiFetch } from "@/lib/api";
import type { EstimateSummary } from "@/lib/estimate";

type EstimatesListProps = {
  estimates: EstimateSummary[];
  locale: string;
};

function formatDate(value: string, locale: string): string {
  return new Intl.DateTimeFormat(locale === "ja" ? "ja-JP" : "en-US", {
    dateStyle: "medium",
  }).format(new Date(value));
}

export default function EstimatesList({ estimates, locale }: EstimatesListProps) {
  const t = useTranslations("estimates");
  const router = useRouter();
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleDelete(estimate: EstimateSummary) {
    setDeletingId(estimate.id);
    setError(null);

    try {
      const response = await apiFetch(`/estimates/${estimate.id}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error(t("deleteError"));
      }

      setConfirmingId(null);
      router.refresh();
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : t("deleteError"));
    } finally {
      setDeletingId(null);
    }
  }

  if (estimates.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-gray-300 bg-white p-8 text-center text-gray-500">
        {t("empty")}
      </p>
    );
  }

  return (
    <div>
      {error && (
        <p className="mb-4 text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                {t("project")}
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                {t("client")}
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                {t("statusLabel")}
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                {t("updated")}
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wide text-gray-500">
                {t("actions")}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {estimates.map((estimate) => {
              const isConfirming = confirmingId === estimate.id;
              const isDeleting = deletingId === estimate.id;

              return (
                <tr key={estimate.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm">
                    <Link
                      href={`/${locale}/estimates/${estimate.id}`}
                      className="font-medium text-blue-600 hover:underline"
                    >
                      {estimate.project_name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">{estimate.client_name}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {t(`status.${estimate.status}`)}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {formatDate(estimate.updated_at, locale)}
                  </td>
                  <td className="px-4 py-3 text-right text-sm">
                    {isConfirming ? (
                      <div className="inline-flex flex-col items-end gap-2 sm:flex-row sm:items-center">
                        <span className="max-w-xs text-left text-xs text-gray-600">
                          {t("deleteConfirm", { project: estimate.project_name })}
                        </span>
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={() => setConfirmingId(null)}
                            disabled={isDeleting}
                            className="rounded border border-gray-300 px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                          >
                            {t("deleteCancel")}
                          </button>
                          <button
                            type="button"
                            onClick={() => void handleDelete(estimate)}
                            disabled={isDeleting}
                            className="rounded bg-red-600 px-2 py-1 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50"
                          >
                            {isDeleting ? t("deleting") : t("deleteConfirmAction")}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={() => {
                          setError(null);
                          setConfirmingId(estimate.id);
                        }}
                        className="rounded border border-red-200 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-50"
                      >
                        {t("delete")}
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
