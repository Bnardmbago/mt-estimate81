"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { apiFetch, apiJson } from "@/lib/api";
import type { ExportRecord } from "@/lib/estimate";

type ExportFormat = "pdf" | "xlsx" | "md";

type ExportPanelProps = {
  estimateId: string;
  locale: string;
  estimateUpdatedAt: string;
};

const FORMAT_OPTIONS: ExportFormat[] = ["pdf", "xlsx", "md"];

const formatLabelKey: Record<ExportFormat, "formatPdf" | "formatXlsx" | "formatMd"> = {
  pdf: "formatPdf",
  xlsx: "formatXlsx",
  md: "formatMd",
};

function formatTimestamp(value: string, locale: string): string {
  const date = new Date(value);
  return date.toLocaleString(locale === "ja" ? "ja-JP" : "en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function ExportPanel({
  estimateId,
  locale,
  estimateUpdatedAt,
}: ExportPanelProps) {
  const router = useRouter();
  const t = useTranslations("export");
  const [exports, setExports] = useState<ExportRecord[]>([]);
  const [selectedFormats, setSelectedFormats] = useState<Set<ExportFormat>>(
    () => new Set(["pdf"]),
  );
  const [exporting, setExporting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadExports = useCallback(async () => {
    try {
      const records = await apiJson<ExportRecord[]>(`/estimates/${estimateId}/exports`);
      setExports(records);
    } catch {
      setExports([]);
    } finally {
      setLoading(false);
    }
  }, [estimateId]);

  useEffect(() => {
    void loadExports();
  }, [loadExports]);

  const latestExportAt = useMemo(() => {
    if (exports.length === 0) {
      return null;
    }
    return exports.reduce((latest, record) => {
      return new Date(record.generated_at) > new Date(latest) ? record.generated_at : latest;
    }, exports[0].generated_at);
  }, [exports]);

  const isStale = useMemo(() => {
    if (!latestExportAt) {
      return false;
    }
    return new Date(estimateUpdatedAt) > new Date(latestExportAt);
  }, [estimateUpdatedAt, latestExportAt]);

  function toggleFormat(format: ExportFormat) {
    setSelectedFormats((current) => {
      const next = new Set(current);
      if (next.has(format)) {
        if (next.size > 1) {
          next.delete(format);
        }
      } else {
        next.add(format);
      }
      return next;
    });
  }

  async function handleExport() {
    if (selectedFormats.size === 0) {
      return;
    }

    setExporting(true);
    setError(null);

    try {
      for (const format of selectedFormats) {
        const response = await apiFetch(`/estimates/${estimateId}/export`, {
          method: "POST",
          body: JSON.stringify({ format, locale }),
        });

        if (!response.ok) {
          const payload = await response.json().catch(() => ({}));
          const message =
            typeof payload.detail === "object"
              ? payload.detail.error
              : payload.detail || response.statusText;
          throw new Error(message || t("exportError"));
        }
      }

      await loadExports();
      router.refresh();
    } catch (exportError) {
      setError(exportError instanceof Error ? exportError.message : t("exportError"));
    } finally {
      setExporting(false);
    }
  }

  return (
    <section className="mt-8 border-t border-gray-200 pt-8">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold">{t("title")}</h2>
            {isStale && (
              <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800">
                {t("staleBadge")}
              </span>
            )}
          </div>
          <p className="text-sm text-gray-500">{t("description")}</p>
        </div>
        <button
          type="button"
          onClick={() => void handleExport()}
          disabled={exporting || selectedFormats.size === 0}
          className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {exporting ? t("exporting") : t("exportButton")}
        </button>
      </div>

      <div className="mb-4 flex flex-wrap gap-4">
        {FORMAT_OPTIONS.map((format) => (
          <label key={format} className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={selectedFormats.has(format)}
              onChange={() => toggleFormat(format)}
              className="rounded border-gray-300"
            />
            {t(formatLabelKey[format])}
          </label>
        ))}
      </div>

      {error && (
        <p className="mb-4 text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      <div>
        <h3 className="mb-2 text-sm font-medium text-gray-700">{t("downloadsTitle")}</h3>
        {loading ? (
          <p className="text-sm text-gray-500">{t("loading")}</p>
        ) : exports.length === 0 ? (
          <p className="text-sm text-gray-500">{t("empty")}</p>
        ) : (
          <ul className="divide-y divide-gray-100 rounded-md border border-gray-200">
            {exports.map((record) => (
              <li
                key={record.id}
                className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="text-sm text-gray-700">
                  <span className="font-medium uppercase">{record.format}</span>
                  <span className="mx-2 text-gray-400">·</span>
                  <span>{record.locale.toUpperCase()}</span>
                  <span className="mx-2 text-gray-400">·</span>
                  <span className="text-gray-500">
                    {formatTimestamp(record.generated_at, locale)}
                  </span>
                </div>
                <a
                  href={`/api/exports/${record.id}/download`}
                  className="text-sm font-medium text-indigo-600 hover:text-indigo-800"
                >
                  {t("download")}
                </a>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
