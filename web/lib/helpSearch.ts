export type HelpCategory = "all" | "articles" | "faqs" | "documentation";

export type HelpArticle = {
  id: string;
  title: string;
  summary: string;
  body: string;
};

export type HelpFaq = {
  id: string;
  question: string;
  answer: string;
};

export type HelpDocumentation = {
  id: string;
  title: string;
  summary: string;
  body: string;
};

export type HelpUserGuideStep = {
  icon?: string;
  title: string;
  description: string;
  href: string | null;
};

export type HelpSearchResult =
  | { kind: "article"; item: HelpArticle }
  | { kind: "faq"; item: HelpFaq }
  | { kind: "documentation"; item: HelpDocumentation };

function normalizeQuery(query: string): string {
  return query.trim().toLowerCase();
}

function matchesText(haystack: string, needle: string): boolean {
  return haystack.toLowerCase().includes(needle);
}

function articleMatches(article: HelpArticle, query: string): boolean {
  return (
    matchesText(article.title, query) ||
    matchesText(article.summary, query) ||
    matchesText(article.body, query)
  );
}

function faqMatches(faq: HelpFaq, query: string): boolean {
  return (
    matchesText(faq.question, query) ||
    matchesText(faq.answer, query)
  );
}

function documentationMatches(doc: HelpDocumentation, query: string): boolean {
  return (
    matchesText(doc.title, query) ||
    matchesText(doc.summary, query) ||
    matchesText(doc.body, query)
  );
}

export function filterHelpContent({
  query,
  category,
  articles,
  faqs,
  documentation,
}: {
  query: string;
  category: HelpCategory;
  articles: HelpArticle[];
  faqs: HelpFaq[];
  documentation: HelpDocumentation[];
}): HelpSearchResult[] {
  const normalizedQuery = normalizeQuery(query);

  const includeArticles = category === "all" || category === "articles";
  const includeFaqs = category === "all" || category === "faqs";
  const includeDocumentation = category === "all" || category === "documentation";

  const results: HelpSearchResult[] = [];

  if (includeArticles) {
    for (const item of articles) {
      if (!normalizedQuery || articleMatches(item, normalizedQuery)) {
        results.push({ kind: "article", item });
      }
    }
  }

  if (includeFaqs) {
    for (const item of faqs) {
      if (!normalizedQuery || faqMatches(item, normalizedQuery)) {
        results.push({ kind: "faq", item });
      }
    }
  }

  if (includeDocumentation) {
    for (const item of documentation) {
      if (!normalizedQuery || documentationMatches(item, normalizedQuery)) {
        results.push({ kind: "documentation", item });
      }
    }
  }

  return results;
}

export function resultAnchorId(result: HelpSearchResult): string {
  if (result.kind === "faq") {
    return `faq-${result.item.id}`;
  }
  return `${result.kind}-${result.item.id}`;
}
