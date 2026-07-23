import type { ProposalLocale } from "@/lib/proposal-types";

export type ProposalDocLabels = {
  partAssessment: string;
  partProposal: string;
  partPoc: string;
  tocLabel: string;
  parts: string;
  oneTimeCost: string;
  monthlyCost: string;
  firstYearTotal: string;
  timelineTitle: string;
  timelineRange: (args: {
    start: string | number;
    end: string | number;
    days: string | number;
  }) => string;
  milestonesTitle: string;
  officialPocCost: string;
  effortHours: string;
  effortDays: string;
  workingDays: string;
  suggestedWindow: string;
  projectBrief: string;
  briefProjectName: string;
  briefDescription: string;
  briefBusinessProblem: string;
  briefTargetUsers: string;
  briefTechnologyStack: string;
  briefConstraints: string;
  pocTables: string;
  pocDiagrams: string;
  pocMilestones: string;
};

const EN: ProposalDocLabels = {
  partAssessment: "Assessment",
  partProposal: "Proposal",
  partPoc: "Proof of Concept",
  tocLabel: "Table of contents",
  parts: "Proposal parts",
  oneTimeCost: "One-time project cost",
  monthlyCost: "Monthly recurring cost",
  firstYearTotal: "First-year total",
  timelineTitle: "Project timeline",
  timelineRange: ({ start, end, days }) =>
    `Start ${start} · End ${end} · Working days ${days}`,
  milestonesTitle: "Milestones",
  officialPocCost: "Official Proof of Concept cost (from estimate engine)",
  effortHours: "Estimated effort (hours)",
  effortDays: "Estimated effort (days)",
  workingDays: "Estimated timeline (working days)",
  suggestedWindow: "Suggested validation window",
  projectBrief: "Project brief",
  briefProjectName: "Project name",
  briefDescription: "Project description",
  briefBusinessProblem: "Business problem",
  briefTargetUsers: "Target users",
  briefTechnologyStack: "Technology stack",
  briefConstraints: "Constraints",
  pocTables: "Tables",
  pocDiagrams: "Illustrations",
  pocMilestones: "Proof of Concept milestones",
};

const JA: ProposalDocLabels = {
  partAssessment: "プロジェクト評価",
  partProposal: "プロジェクト提案",
  partPoc: "概念実証（Proof of Concept）",
  tocLabel: "目次",
  parts: "提案の構成",
  oneTimeCost: "一次性のプロジェクト費用",
  monthlyCost: "月次の継続費用",
  firstYearTotal: "初年度合計",
  timelineTitle: "プロジェクトタイムライン",
  timelineRange: ({ start, end, days }) =>
    `開始 ${start} · 終了 ${end} · 稼働日 ${days}`,
  milestonesTitle: "マイルストーン",
  officialPocCost: "概念実証の公式費用（見積エンジン）",
  effortHours: "想定工数（時間）",
  effortDays: "想定工数（人日）",
  workingDays: "想定期間（稼働日）",
  suggestedWindow: "推奨する検証期間",
  projectBrief: "プロジェクト概要",
  briefProjectName: "プロジェクト名",
  briefDescription: "プロジェクト説明",
  briefBusinessProblem: "ビジネス課題",
  briefTargetUsers: "想定利用者",
  briefTechnologyStack: "技術スタック",
  briefConstraints: "制約条件",
  pocTables: "表",
  pocDiagrams: "図",
  pocMilestones: "概念実証マイルストーン",
};

/** Labels for in-document chrome, keyed by proposal document language (not UI locale). */
export function proposalDocLabels(locale: string | ProposalLocale): ProposalDocLabels {
  return locale === "ja" ? JA : EN;
}
