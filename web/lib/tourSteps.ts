import type { TourAudience } from "@/lib/tourAudience";

export type TourPageId =
  | "welcome"
  | "estimates-list"
  | "estimates-new"
  | "estimate-detail"
  | "proposal"
  | "rate-cards"
  | "help"
  | "settings"
  | "admin";

export type TourStepDef = {
  id: string;
  /** Value for `[data-tour="..."]` */
  selector: string;
  titleKey: string;
  bodyKey: string;
  /** Soft skip when element is missing (gated UI) */
  optional?: boolean;
  /** Restrict step to these audiences (default: all that include the page) */
  audiences?: TourAudience[];
};

export type TourPageDef = {
  id: TourPageId;
  /** Audiences that get this page tour */
  audiences: TourAudience[];
  titleKey: string;
  bodyKey: string;
  steps: TourStepDef[];
};

export const TOUR_PAGES: TourPageDef[] = [
  {
    id: "welcome",
    audiences: ["contact"],
    titleKey: "pages.welcome.title",
    bodyKey: "pages.welcome.body",
    steps: [
      {
        id: "c-welcome",
        selector: "welcome-hero",
        titleKey: "steps.cWelcome.title",
        bodyKey: "steps.cWelcome.body",
      },
      {
        id: "c-request",
        selector: "welcome-get-estimate",
        titleKey: "steps.cRequest.title",
        bodyKey: "steps.cRequest.body",
      },
      {
        id: "c-form",
        selector: "contact-magic-link-form",
        titleKey: "steps.cForm.title",
        bodyKey: "steps.cForm.body",
      },
    ],
  },
  {
    id: "estimates-list",
    audiences: ["user", "admin"],
    titleKey: "pages.estimatesList.title",
    bodyKey: "pages.estimatesList.body",
    steps: [
      {
        id: "f-nav-estimates",
        selector: "nav-estimates",
        titleKey: "steps.fNavEstimates.title",
        bodyKey: "steps.fNavEstimates.body",
      },
      {
        id: "f-list",
        selector: "estimates-list-table",
        titleKey: "steps.fList.title",
        bodyKey: "steps.fList.body",
        optional: true,
      },
      {
        id: "f-new",
        selector: "estimates-new-button",
        titleKey: "steps.fNew.title",
        bodyKey: "steps.fNew.body",
      },
    ],
  },
  {
    id: "estimates-new",
    audiences: ["user", "admin"],
    titleKey: "pages.estimatesNew.title",
    bodyKey: "pages.estimatesNew.body",
    steps: [
      {
        id: "f-template",
        selector: "new-estimate-template-picker",
        titleKey: "steps.fTemplate.title",
        bodyKey: "steps.fTemplate.body",
      },
      {
        id: "f-create",
        selector: "new-estimate-create-button",
        titleKey: "steps.fCreate.title",
        bodyKey: "steps.fCreate.body",
      },
    ],
  },
  {
    id: "estimate-detail",
    audiences: ["contact", "user", "admin"],
    titleKey: "pages.estimateDetail.title",
    bodyKey: "pages.estimateDetail.body",
    steps: [
      {
        id: "est-form",
        selector: "estimate-form",
        titleKey: "steps.fForm.title",
        bodyKey: "steps.fForm.body",
      },
      {
        id: "est-rate-card",
        selector: "estimate-rate-card-panel",
        titleKey: "steps.fRateCard.title",
        bodyKey: "steps.fRateCard.body",
        optional: true,
        audiences: ["user", "admin"],
      },
      {
        id: "est-upload",
        selector: "estimate-document-upload",
        titleKey: "steps.fUpload.title",
        bodyKey: "steps.fUpload.body",
        optional: true,
      },
      {
        id: "est-extract",
        selector: "estimate-extract-button",
        titleKey: "steps.fExtract.title",
        bodyKey: "steps.fExtract.body",
        optional: true,
      },
      {
        id: "est-features",
        selector: "estimate-features-list",
        titleKey: "steps.fFeatures.title",
        bodyKey: "steps.fFeatures.body",
        optional: true,
      },
      {
        id: "est-calculate",
        selector: "estimate-calculate-button",
        titleKey: "steps.fCalculate.title",
        bodyKey: "steps.fCalculate.body",
        optional: true,
      },
      {
        id: "est-export",
        selector: "estimate-export-panel",
        titleKey: "steps.fExport.title",
        bodyKey: "steps.fExport.body",
        optional: true,
      },
      {
        id: "est-export-limit",
        selector: "contact-export-limit-notice",
        titleKey: "steps.cExportLimit.title",
        bodyKey: "steps.cExportLimit.body",
        optional: true,
        audiences: ["contact"],
      },
      {
        id: "est-open-proposal",
        selector: "estimate-open-proposal-link",
        titleKey: "steps.fOpenProposal.title",
        bodyKey: "steps.fOpenProposal.body",
        optional: true,
        audiences: ["user", "admin"],
      },
    ],
  },
  {
    id: "proposal",
    audiences: ["user", "admin"],
    titleKey: "pages.proposal.title",
    bodyKey: "pages.proposal.body",
    steps: [
      {
        id: "f-proposal-gen",
        selector: "proposal-generate-button",
        titleKey: "steps.fProposalGen.title",
        bodyKey: "steps.fProposalGen.body",
      },
      {
        id: "f-proposal-export",
        selector: "proposal-export-panel",
        titleKey: "steps.fProposalExport.title",
        bodyKey: "steps.fProposalExport.body",
        optional: true,
      },
    ],
  },
  {
    id: "rate-cards",
    audiences: ["user", "admin"],
    titleKey: "pages.rateCards.title",
    bodyKey: "pages.rateCards.body",
    steps: [
      {
        id: "f-rates",
        selector: "rate-cards-editor",
        titleKey: "steps.fRates.title",
        bodyKey: "steps.fRates.body",
      },
    ],
  },
  {
    id: "help",
    audiences: ["user", "admin"],
    titleKey: "pages.help.title",
    bodyKey: "pages.help.body",
    steps: [
      {
        id: "f-help",
        selector: "help-restart-tour",
        titleKey: "steps.fHelp.title",
        bodyKey: "steps.fHelp.body",
      },
    ],
  },
  {
    id: "settings",
    audiences: ["contact", "user", "admin"],
    titleKey: "pages.settings.title",
    bodyKey: "pages.settings.body",
    steps: [
      {
        id: "settings-tour",
        selector: "settings-tour-section",
        titleKey: "steps.settingsTour.title",
        bodyKey: "steps.settingsTour.body",
      },
    ],
  },
  {
    id: "admin",
    audiences: ["admin"],
    titleKey: "pages.admin.title",
    bodyKey: "pages.admin.body",
    steps: [
      {
        id: "a-nav-admin",
        selector: "nav-admin",
        titleKey: "steps.aNavAdmin.title",
        bodyKey: "steps.aNavAdmin.body",
      },
      {
        id: "a-users",
        selector: "admin-tab-users",
        titleKey: "steps.aUsers.title",
        bodyKey: "steps.aUsers.body",
      },
      {
        id: "a-presentation",
        selector: "admin-tab-presentation",
        titleKey: "steps.aPresentation.title",
        bodyKey: "steps.aPresentation.body",
      },
      {
        id: "a-ai",
        selector: "admin-tab-ai-settings",
        titleKey: "steps.aAi.title",
        bodyKey: "steps.aAi.body",
      },
      {
        id: "a-smtp",
        selector: "admin-tab-smtp",
        titleKey: "steps.aSmtp.title",
        bodyKey: "steps.aSmtp.body",
      },
      {
        id: "a-system",
        selector: "admin-tab-system",
        titleKey: "steps.aSystem.title",
        bodyKey: "steps.aSystem.body",
      },
      {
        id: "a-help",
        selector: "admin-help-restart-tour",
        titleKey: "steps.aHelp.title",
        bodyKey: "steps.aHelp.body",
        optional: true,
      },
    ],
  },
];

export function resolveTourPageId(pathname: string): TourPageId | null {
  const path = pathname.split("?")[0] || "/";
  if (path === "/welcome" || path === "/") return "welcome";
  if (path === "/estimates") return "estimates-list";
  if (path === "/estimates/new" || path.startsWith("/estimates/new/")) return "estimates-new";
  if (/^\/estimates\/(?!new(?:\/|$)|variance(?:\/|$))[^/]+\/?$/.test(path)) {
    return "estimate-detail";
  }
  if (path === "/proposal" || path.startsWith("/proposal/")) return "proposal";
  if (path === "/rate-cards" || path.startsWith("/rate-cards/")) return "rate-cards";
  if (path === "/help" || path.startsWith("/help/")) return "help";
  if (path === "/settings" || path.startsWith("/settings/")) return "settings";
  if (path === "/admin" || path.startsWith("/admin/")) return "admin";
  return null;
}

export function getTourPage(
  pageId: TourPageId,
  audience: TourAudience,
): TourPageDef | null {
  const page = TOUR_PAGES.find((p) => p.id === pageId);
  if (!page || !page.audiences.includes(audience)) return null;
  return page;
}

export function getPageSteps(page: TourPageDef, audience: TourAudience): TourStepDef[] {
  return page.steps.filter(
    (step) => !step.audiences || step.audiences.includes(audience),
  );
}

export function tourSelector(id: string): string {
  return `[data-tour="${id}"]`;
}
