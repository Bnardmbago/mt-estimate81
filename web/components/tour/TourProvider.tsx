"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useTranslations } from "next-intl";
import { usePathname } from "@/i18n/navigation";
import { driver, type Driver } from "driver.js";
import "driver.js/dist/driver.css";
import type { AccountType } from "@/lib/user-types";
import { resolveTourAudience, type TourAudience } from "@/lib/tourAudience";
import {
  getTourGlobalPrefs,
  isPageTourAutoStartAllowed,
  isPageTourCompleted,
  markPageTourCompleted,
  markTourDontShowAgain,
  resetAllPageTours,
  resetPageTourForRestart,
  setTourGlobalPrefs,
  type TourGlobalPrefs,
} from "@/lib/tourPrefs";
import {
  getPageSteps,
  getTourPage,
  resolveTourPageId,
  tourSelector,
  type TourPageId,
} from "@/lib/tourSteps";
import TourWelcomeModal from "@/components/tour/TourWelcomeModal";
import TourFloatingControls from "@/components/tour/TourFloatingControls";

type TourContextValue = {
  audience: TourAudience | null;
  pageId: TourPageId | null;
  hasPageTour: boolean;
  pageCompleted: boolean;
  prefs: TourGlobalPrefs;
  isRunning: boolean;
  startTour: () => void;
  restartTour: () => void;
  exitTour: () => void;
  skipPageTour: () => void;
  resetAllTours: () => void;
  setEnabled: (enabled: boolean) => void;
};

const TourContext = createContext<TourContextValue | null>(null);

export function useTour(): TourContextValue {
  const ctx = useContext(TourContext);
  if (!ctx) {
    throw new Error("useTour must be used within TourProvider");
  }
  return ctx;
}

export function useTourOptional(): TourContextValue | null {
  return useContext(TourContext);
}

type TourProviderProps = {
  isAuthenticated: boolean;
  isAdmin: boolean;
  accountType: AccountType;
  children: ReactNode;
};

function waitForSelector(selector: string, timeoutMs = 3500): Promise<Element | null> {
  return new Promise((resolve) => {
    const existing = document.querySelector(selector);
    if (existing) {
      resolve(existing);
      return;
    }
    const started = Date.now();
    const timer = window.setInterval(() => {
      const el = document.querySelector(selector);
      if (el) {
        window.clearInterval(timer);
        resolve(el);
        return;
      }
      if (Date.now() - started > timeoutMs) {
        window.clearInterval(timer);
        resolve(null);
      }
    }, 120);
  });
}

export default function TourProvider({
  isAuthenticated,
  isAdmin,
  accountType,
  children,
}: TourProviderProps) {
  const t = useTranslations("tour");
  const pathname = usePathname();

  const audience: TourAudience | null = useMemo(() => {
    if (isAuthenticated) {
      return resolveTourAudience({ accountType, isAdmin });
    }
    if (pathname === "/welcome" || pathname === "/") return "contact";
    return null;
  }, [accountType, isAdmin, isAuthenticated, pathname]);

  const pageId = useMemo(() => resolveTourPageId(pathname), [pathname]);

  const [prefs, setPrefsState] = useState<TourGlobalPrefs>({
    enabled: true,
    dontShowAgain: false,
  });
  const [pageCompleted, setPageCompleted] = useState(false);
  const [showWelcome, setShowWelcome] = useState(false);
  const [isRunning, setIsRunning] = useState(false);

  const driverRef = useRef<Driver | null>(null);
  const runningRef = useRef(false);
  const advancingRef = useRef(false);
  const audienceRef = useRef<TourAudience | null>(null);
  const pageIdRef = useRef<TourPageId | null>(null);

  useEffect(() => {
    audienceRef.current = audience;
    pageIdRef.current = pageId;
    if (!audience) return;
    setPrefsState(getTourGlobalPrefs(audience));
    setPageCompleted(pageId ? isPageTourCompleted(audience, pageId) : false);
  }, [audience, pageId]);

  const destroyDriver = useCallback(() => {
    try {
      driverRef.current?.destroy();
    } catch {
      // ignore
    }
    driverRef.current = null;
  }, []);

  const stopRunning = useCallback(() => {
    runningRef.current = false;
    advancingRef.current = false;
    setIsRunning(false);
    destroyDriver();
  }, [destroyDriver]);

  const finishPageTour = useCallback(
    (opts?: { completed?: boolean; dontShowAgain?: boolean }) => {
      const aud = audienceRef.current;
      const page = pageIdRef.current;
      stopRunning();
      if (!aud) return;

      if (opts?.dontShowAgain) {
        markTourDontShowAgain(aud);
        setPrefsState(getTourGlobalPrefs(aud));
        return;
      }

      if (opts?.completed !== false && page) {
        markPageTourCompleted(aud, page);
        setPageCompleted(true);
      }
      setPrefsState(getTourGlobalPrefs(aud));
    },
    [stopRunning],
  );

  const runPageTour = useCallback(async () => {
    const aud = audienceRef.current;
    const page = pageIdRef.current;
    if (!aud || !page) return;

    const pageDef = getTourPage(page, aud);
    if (!pageDef) return;

    const stepDefs = getPageSteps(pageDef, aud);
    if (stepDefs.length === 0) return;

    // Wait briefly for page UI, then keep only present targets
    const present: typeof stepDefs = [];
    for (const step of stepDefs) {
      const el = await waitForSelector(
        tourSelector(step.selector),
        step.optional ? 800 : 3500,
      );
      if (el) present.push(step);
    }

    if (present.length === 0) {
      finishPageTour({ completed: true });
      return;
    }

    runningRef.current = true;
    setIsRunning(true);
    advancingRef.current = false;
    destroyDriver();

    document
      .querySelector(tourSelector(present[0].selector))
      ?.scrollIntoView({ block: "center", behavior: "smooth" });

    const total = present.length;
    const titles = present.map((s) => t(s.titleKey as Parameters<typeof t>[0]));
    const bodies = present.map((s) => t(s.bodyKey as Parameters<typeof t>[0]));

    const removeStepBadge = () => {
      document.querySelectorAll(".tour-step-badge").forEach((node) => node.remove());
    };

    const placeStepBadge = (element: Element | undefined, stepNumber: number) => {
      removeStepBadge();
      if (!element || !(element instanceof HTMLElement)) return;
      const badge = document.createElement("div");
      badge.className = "tour-step-badge";
      badge.setAttribute("aria-hidden", "true");
      badge.textContent = String(stepNumber);
      const position = window.getComputedStyle(element).position;
      if (position === "static") {
        element.dataset.tourPrevPosition = "static";
        element.style.position = "relative";
      }
      element.appendChild(badge);
    };

    const d = driver({
      showProgress: true,
      animate: true,
      overlayOpacity: 0.55,
      stagePadding: 10,
      stageRadius: 8,
      popoverOffset: 14,
      allowClose: true,
      smoothScroll: true,
      skipMissingElement: true,
      popoverClass: "tour-popover",
      nextBtnText: t("next"),
      prevBtnText: t("previous"),
      doneBtnText: t("done"),
      progressText: t("progress", { current: "{{current}}", total: "{{total}}" }),
      steps: present.map((s, index) => {
        const stepNumber = index + 1;
        const isLast = index >= total - 1;
        const nextTitle = !isLast ? titles[index + 1] : null;
        const instruction = bodies[index];
        const descriptionParts = [
          `<p class="tour-popover-instruction">${instruction}</p>`,
          `<p class="tour-popover-sequence">${t("stepSequence", { current: stepNumber, total })}</p>`,
        ];
        if (nextTitle) {
          descriptionParts.push(
            `<p class="tour-popover-next-hint">${t("nextTarget", { label: nextTitle, number: stepNumber + 1 })}</p>`,
          );
        } else {
          descriptionParts.push(`<p class="tour-popover-next-hint">${t("lastStepHint")}</p>`);
        }
        return {
          element: tourSelector(s.selector),
          popover: {
            title: t("stepTitle", { number: stepNumber, title: titles[index] }),
            description: descriptionParts.join(""),
            side: "bottom" as const,
            align: "start" as const,
            showButtons: ["next", "previous", "close"] as Array<"next" | "previous" | "close">,
          },
          onHighlighted: (element) => {
            placeStepBadge(element, stepNumber);
          },
          onDeselected: (element) => {
            if (element instanceof HTMLElement && element.dataset.tourPrevPosition === "static") {
              element.style.position = "";
              delete element.dataset.tourPrevPosition;
            }
            removeStepBadge();
          },
        };
      }),
      onCloseClick: (_el, _step, { driver: drv }) => {
        advancingRef.current = false;
        removeStepBadge();
        drv.destroy();
      },
      onDestroyed: () => {
        removeStepBadge();
        document.querySelectorAll("[data-tour-prev-position]").forEach((node) => {
          if (node instanceof HTMLElement) {
            node.style.position = "";
            delete node.dataset.tourPrevPosition;
          }
        });
        driverRef.current = null;
        if (advancingRef.current) {
          advancingRef.current = false;
          return;
        }
        if (runningRef.current) {
          finishPageTour({ completed: true });
        }
      },
    });

    driverRef.current = d;
    window.setTimeout(() => {
      if (!runningRef.current) return;
      d.drive(0);
    }, 200);
  }, [destroyDriver, finishPageTour, t]);

  // Offer this page's tour once per session when allowed
  useEffect(() => {
    stopRunning();
    setShowWelcome(false);

    if (!audience || !pageId) return;
    if (!getTourPage(pageId, audience)) return;
    if (!isPageTourAutoStartAllowed(audience, pageId)) return;

    const sessionKey = `tour:${audience}:page:${pageId}:offered`;
    try {
      if (sessionStorage.getItem(sessionKey) === "1") return;
      sessionStorage.setItem(sessionKey, "1");
    } catch {
      // ignore
    }

    const timer = window.setTimeout(() => setShowWelcome(true), 400);
    return () => window.clearTimeout(timer);
  }, [audience, pageId, stopRunning]);

  const startTour = useCallback(() => {
    setShowWelcome(false);
    if (!audience || !pageId) return;
    setTourGlobalPrefs(audience, { enabled: true, dontShowAgain: false });
    setPrefsState(getTourGlobalPrefs(audience));
    void runPageTour();
  }, [audience, pageId, runPageTour]);

  const restartTour = useCallback(() => {
    if (!audience || !pageId) return;
    resetPageTourForRestart(audience, pageId);
    try {
      sessionStorage.removeItem(`tour:${audience}:page:${pageId}:offered`);
    } catch {
      // ignore
    }
    setPrefsState(getTourGlobalPrefs(audience));
    setPageCompleted(false);
    stopRunning();
    setShowWelcome(false);
    void runPageTour();
  }, [audience, pageId, runPageTour, stopRunning]);

  const exitTour = useCallback(() => {
    // Exit without marking the page completed, so user can restart later
    stopRunning();
    setShowWelcome(false);
  }, [stopRunning]);

  const skipPageTour = useCallback(() => {
    setShowWelcome(false);
    stopRunning();
    if (audience && pageId) {
      markPageTourCompleted(audience, pageId);
      setPageCompleted(true);
    }
  }, [audience, pageId, stopRunning]);

  const resetAllTours = useCallback(() => {
    if (!audience) return;
    resetAllPageTours(audience);
    try {
      const prefix = `tour:${audience}:page:`;
      const keys: string[] = [];
      for (let i = 0; i < sessionStorage.length; i++) {
        const key = sessionStorage.key(i);
        if (key?.startsWith(prefix) && key.endsWith(":offered")) keys.push(key);
      }
      for (const key of keys) sessionStorage.removeItem(key);
    } catch {
      // ignore
    }
    setPrefsState(getTourGlobalPrefs(audience));
    setPageCompleted(false);
    stopRunning();
    setShowWelcome(false);
  }, [audience, stopRunning]);

  const setEnabled = useCallback(
    (enabled: boolean) => {
      if (!audience) return;
      const next = setTourGlobalPrefs(audience, {
        enabled,
        ...(enabled ? { dontShowAgain: false } : {}),
      });
      setPrefsState(next);
      if (!enabled) stopRunning();
    },
    [audience, stopRunning],
  );

  const pageDef =
    audience && pageId ? getTourPage(pageId, audience) : null;
  const hasPageTour = Boolean(pageDef);

  const value: TourContextValue = {
    audience,
    pageId,
    hasPageTour,
    pageCompleted,
    prefs,
    isRunning,
    startTour,
    restartTour,
    exitTour,
    skipPageTour,
    resetAllTours,
    setEnabled,
  };

  return (
    <TourContext.Provider value={value}>
      {children}
      <TourFloatingControls />
      <TourWelcomeModal
        open={showWelcome}
        audience={audience}
        pageTitle={pageDef ? t(pageDef.titleKey as Parameters<typeof t>[0]) : undefined}
        pageBody={pageDef ? t(pageDef.bodyKey as Parameters<typeof t>[0]) : undefined}
        onStart={startTour}
        onSkip={() => {
          setShowWelcome(false);
          if (audience && pageId) {
            markPageTourCompleted(audience, pageId);
            setPageCompleted(true);
          }
        }}
        onDontShowAgain={() => {
          setShowWelcome(false);
          if (audience) {
            markTourDontShowAgain(audience);
            setPrefsState(getTourGlobalPrefs(audience));
          }
        }}
      />
    </TourContext.Provider>
  );
}
