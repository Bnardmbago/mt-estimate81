"use client";

import { useCallback } from "react";
import { useLocale, useTranslations } from "next-intl";

export const KNOWN_PHASE_KEYS = [
  "requirement",
  "design",
  "development",
  "testing",
  "deployment",
] as const;

export type KnownPhaseKey = (typeof KNOWN_PHASE_KEYS)[number];

const KNOWN_ROLE_KEYS = [
  "pm",
  "project_manager",
  "developer",
  "senior_developer",
  "frontend_developer",
  "backend_developer",
  "full_stack_developer",
  "qa",
  "qa_engineer",
  "designer",
  "ui_designer",
  "ux_designer",
  "architect",
  "devops",
  "business_analyst",
  "tech_lead",
] as const;

const KNOWN_SETUP_ITEM_KEYS = ["infrastructure", "tooling", "third_party"] as const;

export function normalizePhaseKey(phase: string): string {
  return phase.trim().toLowerCase();
}

export function normalizeRoleKey(role: string): string {
  return role.trim().toLowerCase().replace(/[\s-]+/g, "_");
}

export function formatJpy(value: number, locale: string): string {
  return `¥${value.toLocaleString(locale === "ja" ? "ja-JP" : "en-US")}`;
}

export function formatNumber(value: number, locale: string): string {
  return value.toLocaleString(locale === "ja" ? "ja-JP" : "en-US");
}

export function formatDisplayDate(value: string, locale: string): string {
  const [year, month, day] = value.split("-").map(Number);
  const date = new Date(year, month - 1, day);
  return date.toLocaleDateString(locale === "ja" ? "ja-JP" : "en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function useDisplayLabels() {
  const locale = useLocale();
  const tRateCards = useTranslations("rateCards");

  const translatePhase = useCallback(
    (phase: string) => {
      const key = normalizePhaseKey(phase);
      if ((KNOWN_PHASE_KEYS as readonly string[]).includes(key)) {
        return tRateCards(`phaseLabels.${key}` as "phaseLabels.requirement");
      }
      return phase;
    },
    [tRateCards],
  );

  const translateRole = useCallback(
    (role: string) => {
      const key = normalizeRoleKey(role);
      if ((KNOWN_ROLE_KEYS as readonly string[]).includes(key)) {
        return tRateCards(`roleNames.${key}` as "roleNames.developer");
      }
      return role;
    },
    [tRateCards],
  );

  const translateSetupItem = useCallback(
    (name: string) => {
      const key = normalizeRoleKey(name);
      if ((KNOWN_SETUP_ITEM_KEYS as readonly string[]).includes(key)) {
        return tRateCards(`setupItemNames.${key}` as "setupItemNames.infrastructure");
      }
      return name;
    },
    [tRateCards],
  );

  return {
    locale,
    translatePhase,
    translateRole,
    translateSetupItem,
    formatJpy: (value: number) => formatJpy(value, locale),
    formatNumber: (value: number) => formatNumber(value, locale),
    formatDisplayDate: (value: string) => formatDisplayDate(value, locale),
  };
}

export function isKnownPhaseKey(phase: string): phase is KnownPhaseKey {
  return (KNOWN_PHASE_KEYS as readonly string[]).includes(normalizePhaseKey(phase));
}
