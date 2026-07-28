export type ProposalLocale = "en" | "ja";

export type ProposalCoverField = {
  key: string;
  required?: boolean;
  emphasis?: string | null;
  auto_fill?: string | boolean | null;
  content?: {
    _i18n?: Partial<
      Record<ProposalLocale, { label?: string; default_text?: string }>
    >;
    label?: string;
    default_text?: string;
  };
};

export type ProposalCoverValues = Record<
  string,
  | string
  | number
  | null
  | {
      value?: unknown;
      _i18n?: Partial<Record<ProposalLocale, { value?: unknown }>>;
    }
>;

export type ProposalSection = {
  id: string;
  title: string;
  body?: string;
  bullets?: string[];
  rating?: string;
  user_edited?: boolean;
  feature_ids?: string[];
  drivers?: string[];
  poc_recommended?: boolean;
};

export type ProposalProjectBrief = {
  project_name?: string;
  project_description?: string;
  business_problem?: string;
  target_users?: string;
  technology_stack?: string;
  constraints?: string;
};

export type ProposalTable = {
  id: string;
  title: string;
  headers?: string[];
  rows?: string[][];
};

export type ProposalDiagram = {
  id: string;
  title: string;
  engine?: string;
  source: string;
};

export type ProposalMilestone = {
  id: string;
  name: string;
  date?: string | null;
};

export type ProposalPartBlob = {
  sections?: ProposalSection[];
  project_brief?: ProposalProjectBrief;
  tables?: ProposalTable[];
  diagrams?: ProposalDiagram[];
  milestones?: ProposalMilestone[];
  brief_user_edited?: boolean;
  poc_recommended?: boolean;
  summary_cost_note?: string;
  official?: {
    selected_feature_ids?: string[];
    selected_features?: Array<{ id: string; name?: string; hours?: number }>;
    total_effort_hours?: number;
    total_effort_days?: number;
    estimated_one_time_cost_jpy?: number;
    estimated_timeline_working_days?: number;
    warning?: string;
  };
  suggested_validation_window?: string;
};

export type ProposalExportRecord = {
  id: string;
  format: string;
  variant: string;
  locale: string;
  revision: number;
  generated_at: string;
  theme_id?: string | null;
  style_id?: string | null;
  template_id?: string | null;
  destination?: string | null;
  external_file_id?: string | null;
  external_url?: string | null;
  manually_edited_at?: string | null;
};

export type ProposalDetail = {
  id: string;
  estimate_id: string;
  locale: string;
  include_poc: boolean;
  status: string;
  source_snapshot: {
    project_name?: string;
    client_name?: string;
    costs?: Record<string, number | null | undefined>;
    gantt?: {
      project_start_date?: string;
      project_end_date?: string;
      total_working_days?: number;
      phases?: Array<{
        phase: string;
        start_date: string;
        end_date: string;
        duration_working_days: number;
      }>;
      tasks?: Array<{
        feature_item_id?: string | null;
        name: string;
        phase: string;
        role: string;
        hours: number;
        effort_days?: number;
        personnel_count?: number;
        start_date: string;
        end_date: string;
        duration_working_days: number;
      }>;
    };
    features?: Array<{ id: string; name: string; hours: number }>;
  };
  assessment: ProposalPartBlob | null;
  proposal_body: ProposalPartBlob | null;
  poc: ProposalPartBlob | null;
  diagrams: ProposalDiagram[];
  milestones: ProposalMilestone[];
  generation_meta: {
    run_id?: string;
    parts?: Record<string, { status?: string; error?: string | null }>;
    error?: string;
  };
  source_fingerprint: string;
  source_stale: boolean;
  theme_id?: string | null;
  style_id?: string | null;
  template_id?: string | null;
  theme_name?: string | null;
  style_name?: string | null;
  template_name?: string | null;
  presentation_meta?: Record<string, unknown>;
  presentation_css_vars?: Record<string, string>;
  presentation_layout_class?: string;
  cover_values: ProposalCoverValues;
  created_at: string;
  updated_at: string;
  finalized_at: string | null;
  exports: ProposalExportRecord[];
};

export type ProposalSummary = {
  id: string;
  estimate_id: string;
  project_name: string;
  client_name: string;
  locale: string;
  include_poc: boolean;
  status: string;
  updated_at: string;
  source_stale: boolean;
  theme_id?: string | null;
  style_id?: string | null;
  template_id?: string | null;
};

export type ProposalStatusResponse = {
  id: string;
  status: string;
  generation_meta: ProposalDetail["generation_meta"];
  assessment_ready: boolean;
  proposal_ready: boolean;
  poc_ready: boolean;
};

export type EstimatePickerItem = {
  id: string;
  project_name: string;
  client_name: string;
  status: string;
};
