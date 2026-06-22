import type { ExtractedData } from "@/lib/estimate-types";

const I18N_KEY = "_i18n";
const SUPPORTED_LOCALES = ["ja", "en"] as const;

type LocalizedBucket = Record<string, unknown>;

function normalizeLocale(
  locale: string | null | undefined,
  fallback: string,
): string {
  if (locale && SUPPORTED_LOCALES.includes(locale as (typeof SUPPORTED_LOCALES)[number])) {
    return locale;
  }
  if (SUPPORTED_LOCALES.includes(fallback as (typeof SUPPORTED_LOCALES)[number])) {
    return fallback;
  }
  return "ja";
}

function splitLocalizedPayload(
  data: Record<string, unknown> | null | undefined,
): { legacy: LocalizedBucket; i18n: Record<string, LocalizedBucket> } {
  if (!data) {
    return { legacy: {}, i18n: {} };
  }

  const i18nValue = data[I18N_KEY];
  if (i18nValue && typeof i18nValue === "object" && !Array.isArray(i18nValue)) {
    const legacy: LocalizedBucket = {};
    for (const [key, value] of Object.entries(data)) {
      if (key !== I18N_KEY) {
        legacy[key] = value;
      }
    }

    const i18n: Record<string, LocalizedBucket> = {};
    for (const [locale, values] of Object.entries(i18nValue as Record<string, unknown>)) {
      if (
        SUPPORTED_LOCALES.includes(locale as (typeof SUPPORTED_LOCALES)[number]) &&
        values &&
        typeof values === "object" &&
        !Array.isArray(values)
      ) {
        i18n[locale] = values as LocalizedBucket;
      }
    }

    return { legacy, i18n };
  }

  return { legacy: { ...data }, i18n: {} };
}

export function resolveLocalizedDict(
  data: Record<string, unknown> | null | undefined,
  displayLocale: string,
  fallbackLocale: string,
): Record<string, unknown> {
  const { legacy, i18n } = splitLocalizedPayload(data);
  const resolvedDisplay = normalizeLocale(displayLocale, fallbackLocale);
  const resolvedFallback = normalizeLocale(fallbackLocale, resolvedDisplay);

  for (const locale of [resolvedDisplay, resolvedFallback]) {
    if (i18n[locale]) {
      return { ...i18n[locale] };
    }
  }

  const firstBucket = Object.values(i18n)[0];
  if (firstBucket) {
    return { ...firstBucket };
  }

  return { ...legacy };
}

export function emptyExtractedData(): ExtractedData {
  return {
    functional_requirements: [],
    non_functional_requirements: [],
    user_roles: [],
    modules: [],
    external_systems: [],
    risks: [],
    gaps: [],
    confidence_notes: "",
  };
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item): item is string => typeof item === "string");
}

export function resolveExtractedData(
  data: Record<string, unknown> | ExtractedData | null | undefined,
  displayLocale: string,
  fallbackLocale: string,
): ExtractedData {
  const resolved = resolveLocalizedDict(
    data as Record<string, unknown> | null | undefined,
    displayLocale,
    fallbackLocale,
  );

  return {
    ...emptyExtractedData(),
    functional_requirements: asStringArray(resolved.functional_requirements),
    non_functional_requirements: asStringArray(resolved.non_functional_requirements),
    user_roles: asStringArray(resolved.user_roles),
    modules: asStringArray(resolved.modules),
    external_systems: asStringArray(resolved.external_systems),
    risks: asStringArray(resolved.risks),
    gaps: asStringArray(resolved.gaps),
    confidence_notes:
      typeof resolved.confidence_notes === "string" ? resolved.confidence_notes : "",
  };
}
