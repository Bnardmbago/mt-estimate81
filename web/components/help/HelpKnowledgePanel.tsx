"use client";

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import {
  filterHelpContent,
  resultAnchorId,
  type HelpArticle,
  type HelpCategory,
  type HelpDocumentation,
  type HelpFaq,
  type HelpSearchResult,
} from "@/lib/helpSearch";

const CATEGORY_ORDER: HelpCategory[] = ["all", "articles", "faqs", "documentation"];

type HelpNamespace = "help" | "admin.help";

type HelpKnowledgePanelProps = {
  namespace: HelpNamespace;
  searchInputId: string;
};

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}

function categoryLabelKey(category: HelpCategory): "all" | "articles" | "faqs" | "documentation" {
  return category;
}

function ResultCard({
  result,
  categoryLabels,
}: {
  result: HelpSearchResult;
  categoryLabels: Record<HelpCategory, string>;
}) {
  if (result.kind === "faq") {
    return <FaqItem faq={result.item} />;
  }

  const item = result.item as HelpArticle | HelpDocumentation;
  const badge =
    result.kind === "article" ? categoryLabels.articles : categoryLabels.documentation;

  return (
    <article
      id={resultAnchorId(result)}
      className="scroll-mt-24 rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-gray-900"
    >
      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {badge}
      </p>
      <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">{item.title}</h3>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{item.summary}</p>
      <p className="mt-3 text-sm leading-relaxed text-slate-700 dark:text-slate-300">{item.body}</p>
    </article>
  );
}

function FaqItem({ faq }: { faq: HelpFaq }) {
  return (
    <details
      id={`faq-${faq.id}`}
      className="group scroll-mt-24 rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-gray-900"
    >
      <summary className="cursor-pointer list-none px-5 py-4 text-base font-medium text-slate-900 marker:content-none dark:text-slate-100 [&::-webkit-details-marker]:hidden">
        <span className="flex items-start justify-between gap-3">
          <span>{faq.question}</span>
          <span
            aria-hidden
            className="mt-0.5 shrink-0 text-slate-400 transition group-open:rotate-180"
          >
            ▾
          </span>
        </span>
      </summary>
      <div className="border-t border-slate-100 px-5 py-4 text-sm leading-relaxed text-slate-700 dark:border-slate-800 dark:text-slate-300">
        {faq.answer}
      </div>
    </details>
  );
}

export default function HelpKnowledgePanel({ namespace, searchInputId }: HelpKnowledgePanelProps) {
  const t = useTranslations(namespace);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<HelpCategory>("all");
  const debouncedQuery = useDebouncedValue(query, 200);

  const articles = t.raw("articles") as HelpArticle[];
  const faqs = t.raw("faqs") as HelpFaq[];
  const documentation = t.raw("documentation") as HelpDocumentation[];

  const results = useMemo(
    () =>
      filterHelpContent({
        query: debouncedQuery,
        category,
        articles,
        faqs,
        documentation,
      }),
    [debouncedQuery, category, articles, faqs, documentation],
  );

  const categoryLabels = useMemo(
    () =>
      Object.fromEntries(
        CATEGORY_ORDER.map((key) => [key, t(`categories.${categoryLabelKey(key)}`)]),
      ) as Record<HelpCategory, string>,
    [t],
  );

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="max-w-2xl">
        <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">{t("title")}</h2>
        <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400 sm:text-base">
          {t("description")}
        </p>
      </div>

      <div className="space-y-4">
        <div className="relative">
          <label htmlFor={searchInputId} className="sr-only">
            {t("search.placeholder")}
          </label>
          <input
            id={searchInputId}
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={t("search.placeholder")}
            className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3 pr-24 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-600 dark:bg-gray-900 dark:text-slate-100"
          />
          {query ? (
            <button
              type="button"
              onClick={() => setQuery("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 rounded px-2 py-1 text-xs font-medium text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:hover:bg-slate-800 dark:hover:text-slate-200"
            >
              {t("search.clear")}
            </button>
          ) : null}
        </div>

        <div className="-mx-1 overflow-x-auto px-1 pb-1">
          <div className="flex min-w-max gap-2">
            {CATEGORY_ORDER.map((key) => {
              const active = category === key;
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => setCategory(key)}
                  className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                    active
                      ? "border border-blue-600 bg-blue-600 text-white"
                      : "border border-slate-300 bg-white text-slate-700 hover:border-slate-400 hover:bg-slate-50 dark:border-slate-600 dark:bg-gray-900 dark:text-slate-200 dark:hover:bg-slate-800"
                  }`}
                >
                  {categoryLabels[key]}
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-slate-500 dark:text-slate-400">
          <p>{t("search.resultCount", { count: results.length })}</p>
          {!debouncedQuery ? <p>{t("search.browseAll")}</p> : null}
        </div>
      </div>

      <div aria-live="polite" className="space-y-4">
        {results.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center dark:border-slate-700 dark:bg-gray-900">
            <p className="text-sm text-slate-600 dark:text-slate-400">
              {t("search.noResults", { query: debouncedQuery })}
            </p>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {results.map((result) => (
              <div
                key={resultAnchorId(result)}
                className={result.kind === "faq" ? "md:col-span-2" : undefined}
              >
                <ResultCard result={result} categoryLabels={categoryLabels} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
