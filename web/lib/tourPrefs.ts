import type { TourAudience } from "@/lib/tourAudience";
import type { TourPageId } from "@/lib/tourSteps";

export type TourGlobalPrefs = {
  enabled: boolean;
  dontShowAgain: boolean;
};

const GLOBAL_DEFAULTS: TourGlobalPrefs = {
  enabled: true,
  dontShowAgain: false,
};

function globalKey(audience: TourAudience): string {
  return `tour:${audience}:global`;
}

function pageKey(audience: TourAudience, pageId: TourPageId): string {
  return `tour:${audience}:page:${pageId}`;
}

function readJson<T>(key: string): T | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return null;
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

function writeJson(key: string, value: unknown): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // ignore quota / private mode
  }
}

export function getTourGlobalPrefs(audience: TourAudience): TourGlobalPrefs {
  const stored = readJson<Partial<TourGlobalPrefs>>(globalKey(audience));
  // Migrate legacy prefs shape if present
  const legacy = readJson<{
    enabled?: boolean;
    dontShowAgain?: boolean;
    completed?: boolean;
  }>(`tour:${audience}:prefs`);
  if (!stored && legacy) {
    return {
      enabled: legacy.enabled ?? GLOBAL_DEFAULTS.enabled,
      dontShowAgain: legacy.dontShowAgain ?? GLOBAL_DEFAULTS.dontShowAgain,
    };
  }
  if (!stored) return { ...GLOBAL_DEFAULTS };
  return {
    enabled: stored.enabled ?? GLOBAL_DEFAULTS.enabled,
    dontShowAgain: stored.dontShowAgain ?? GLOBAL_DEFAULTS.dontShowAgain,
  };
}

export function setTourGlobalPrefs(
  audience: TourAudience,
  patch: Partial<TourGlobalPrefs>,
): TourGlobalPrefs {
  const next = { ...getTourGlobalPrefs(audience), ...patch };
  writeJson(globalKey(audience), next);
  return next;
}

export function isPageTourCompleted(audience: TourAudience, pageId: TourPageId): boolean {
  const stored = readJson<{ completed?: boolean }>(pageKey(audience, pageId));
  return Boolean(stored?.completed);
}

export function markPageTourCompleted(audience: TourAudience, pageId: TourPageId): void {
  writeJson(pageKey(audience, pageId), { completed: true });
}

export function clearPageTourCompleted(audience: TourAudience, pageId: TourPageId): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(pageKey(audience, pageId));
  } catch {
    // ignore
  }
}

export function isPageTourAutoStartAllowed(
  audience: TourAudience,
  pageId: TourPageId,
): boolean {
  const global = getTourGlobalPrefs(audience);
  if (!global.enabled || global.dontShowAgain) return false;
  return !isPageTourCompleted(audience, pageId);
}

export function markTourDontShowAgain(audience: TourAudience): void {
  setTourGlobalPrefs(audience, { dontShowAgain: true, enabled: false });
}

export function resetPageTourForRestart(
  audience: TourAudience,
  pageId: TourPageId,
): void {
  setTourGlobalPrefs(audience, { enabled: true, dontShowAgain: false });
  clearPageTourCompleted(audience, pageId);
}

export function resetAllPageTours(audience: TourAudience): void {
  setTourGlobalPrefs(audience, { enabled: true, dontShowAgain: false });
  if (typeof window === "undefined") return;
  const prefix = `tour:${audience}:page:`;
  try {
    const keys: string[] = [];
    for (let i = 0; i < window.localStorage.length; i++) {
      const key = window.localStorage.key(i);
      if (key?.startsWith(prefix)) keys.push(key);
    }
    for (const key of keys) window.localStorage.removeItem(key);
  } catch {
    // ignore
  }
}
