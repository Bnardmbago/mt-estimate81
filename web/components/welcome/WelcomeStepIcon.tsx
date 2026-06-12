import type { ReactNode } from "react";

type StepIconName =
  | "login"
  | "rateCard"
  | "create"
  | "upload"
  | "review"
  | "calculate"
  | "export";

const STEP_ICONS_BY_INDEX: StepIconName[] = [
  "login",
  "rateCard",
  "create",
  "upload",
  "review",
  "calculate",
  "export",
];

type WelcomeStepIconProps = {
  icon?: string;
  stepIndex: number;
  className?: string;
};

function resolveIconName(icon: string | undefined, stepIndex: number): StepIconName {
  const valid: StepIconName[] = [
    "login",
    "rateCard",
    "create",
    "upload",
    "review",
    "calculate",
    "export",
  ];
  if (icon && valid.includes(icon as StepIconName)) {
    return icon as StepIconName;
  }
  return STEP_ICONS_BY_INDEX[stepIndex] ?? "login";
}

export default function WelcomeStepIcon({
  icon,
  stepIndex,
  className = "h-6 w-6",
}: WelcomeStepIconProps) {
  const name = resolveIconName(icon, stepIndex);

  const paths: Record<StepIconName, ReactNode> = {
    login: (
      <>
        <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
        <polyline points="10 17 15 12 10 7" />
        <line x1="15" y1="12" x2="3" y2="12" />
      </>
    ),
    rateCard: (
      <>
        <rect x="2" y="5" width="20" height="14" rx="2" />
        <line x1="2" y1="10" x2="22" y2="10" />
        <line x1="6" y1="15" x2="10" y2="15" />
        <line x1="14" y1="15" x2="18" y2="15" />
      </>
    ),
    create: (
      <>
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="12" y1="18" x2="12" y2="12" />
        <line x1="9" y1="15" x2="15" y2="15" />
      </>
    ),
    upload: (
      <>
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <polyline points="17 8 12 3 7 8" />
        <line x1="12" y1="3" x2="12" y2="15" />
      </>
    ),
    review: (
      <>
        <path d="M9 11l3 3L22 4" />
        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
      </>
    ),
    calculate: (
      <>
        <rect x="4" y="2" width="16" height="20" rx="2" />
        <line x1="8" y1="6" x2="16" y2="6" />
        <line x1="8" y1="10" x2="10" y2="10" />
        <line x1="14" y1="10" x2="16" y2="10" />
        <line x1="8" y1="14" x2="10" y2="14" />
        <line x1="14" y1="14" x2="16" y2="14" />
        <line x1="8" y1="18" x2="16" y2="18" />
      </>
    ),
    export: (
      <>
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <polyline points="7 10 12 15 17 10" />
        <line x1="12" y1="15" x2="12" y2="3" />
      </>
    ),
  };

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden
    >
      {paths[name]}
    </svg>
  );
}
