import type { FormFieldSchema } from "@/lib/formSchema";

export type EstimateDocument = {
  id: string;
  original_filename: string;
  file_type: string;
  storage_path: string;
  extracted_text: string | null;
  extraction_status: "pending" | "processing" | "done" | "failed";
  uploaded_at: string;
};

export type FeatureItem = {
  id: string;
  sort_order: number;
  name: string;
  description: string;
  hours: number;
  phase: string;
  role: string;
  is_ai_generated: boolean;
  created_at: string;
  updated_at: string;
};

export type ExtractedData = {
  functional_requirements: string[];
  non_functional_requirements: string[];
  user_roles: string[];
  modules: string[];
  external_systems: string[];
  risks: string[];
  gaps: string[];
  confidence_notes: string;
  complexity_profile?: ComplexityProfile;
};

export type ComplexityProfile = {
  level: "low" | "medium" | "high";
  overall_score: number;
  drivers?: string[];
  feature_count?: number;
  total_hours?: number;
  integration_count?: number;
  non_functional_count?: number;
};

export type NrcRcLineItem = {
  name: string;
  amount: number;
  category?: string | null;
  service_description?: string | null;
};

export type NrcRcAssumptions = {
  setup_cost_items: NrcRcLineItem[];
  monthly_rc_items: NrcRcLineItem[];
  source?: "derived" | "rate_card_tune" | "manual" | "rate_card";
  complexity_level?: "low" | "medium" | "high" | null;
};

export type GanttData = {
  project_start_date: string;
  project_end_date: string;
  total_working_days: number;
  phases: Array<{
    phase: string;
    start_date: string;
    end_date: string;
    duration_working_days: number;
  }>;
  tasks: Array<{
    feature_item_id: string | null;
    name: string;
    phase: string;
    role: string;
    hours: number;
    effort_days: number;
    start_date: string;
    end_date: string;
    duration_working_days: number;
  }>;
};

export type CalculationResult = {
  total_effort_hours: number;
  total_effort_days: number;
  estimated_duration_days?: number;
  gantt?: GanttData;
  phase_breakdown: Array<{ phase: string; hours: number; percentage: number }>;
  role_breakdown: Array<{
    role: string;
    hours: number;
    personnel_count?: number;
    rate_jpy: number;
    cost_jpy: number;
  }>;
  nrc: {
    labor_jpy: number;
    setup_jpy: number;
    contingency_jpy: number;
    overhead_jpy: number;
    total_jpy: number;
  };
  rc: {
    monthly_items: Array<{ name: string; amount_jpy: number }>;
    maintenance_jpy: number;
    monthly_total_jpy: number;
    annual_total_jpy: number;
  };
  rc_detailed_breakdown?: {
    line_items: Array<{
      category_key: string;
      category: string;
      service_description: string;
      monthly_jpy: number;
      annual_jpy: number;
      is_maintenance?: boolean;
    }>;
    monthly_total_jpy: number;
    annual_total_jpy: number;
    markup_rate_applied?: number;
  };
  first_year_total_jpy: number;
  rate_card_version_id: string;
  nrc_original_total_jpy?: number | null;
  discount_rate_applied?: number | null;
  discount_amount_jpy?: number | null;
  budget_comparison?: {
    client_budget_jpy: number;
    calculated_nrc_jpy: number;
    delta_jpy: number;
    status: "under" | "over" | "aligned";
  };
  delivery_schedule_advisory?: {
    delivery_schedule_status: "within_band" | "over_band" | "unknown";
    delivery_schedule_message_key?: string;
    target_working_days?: number | null;
    actual_working_days?: number;
  };
  nrc_rc_assumptions?: NrcRcAssumptions;
  nrc_rc_source?: "derived" | "rate_card_tune" | "manual" | "rate_card";
};

export type ExportRecord = {
  id: string;
  estimate_id: string;
  format: string;
  storage_path: string;
  locale: string;
  quotation_number?: string | null;
  registration_number?: string | null;
  generated_at: string;
  generated_by: string;
};

export type Actuals = {
  id: string;
  estimate_id: string;
  actual_effort_hours: number;
  actual_duration_days: number;
  actual_nrc_jpy: number;
  actual_rc_monthly_jpy: number;
  variance_notes: string | null;
  entered_by: string;
  entered_at: string;
};

export type EstimateSummary = {
  id: string;
  project_name: string;
  client_name: string;
  status: string;
  locale: string;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type EstimateDetail = {
  id: string;
  project_name: string;
  client_name: string;
  status: string;
  locale: string;
  form_data: Record<string, unknown>;
  form_template_id: string | null;
  form_template_name: string | null;
  form_schema_snapshot: FormFieldSchema[];
  extracted_data: ExtractedData | null;
  maintenance_assumptions: Record<string, unknown>;
  nrc_rc_assumptions: NrcRcAssumptions;
  calculation_result: CalculationResult | null;
  rate_card_id: string | null;
  rate_card_name: string | null;
  rate_card_version_id: string | null;
  rate_card_stale: boolean;
  complexity_profile?: ComplexityProfile | null;
  rate_card_auto_tuned?: boolean;
  rate_card_tune_recommended?: boolean;
  rate_card_auto_tune_enabled?: boolean;
  project_start_date: string | null;
  feature_items: FeatureItem[];
  documents: EstimateDocument[];
  actuals: Actuals | null;
  created_at: string;
  updated_at: string;
};

export const ESTIMATE_STATUS_KEYS = [
  "draft",
  "extracting",
  "review",
  "calculated",
  "exported",
  "completed",
] as const;

export type EstimateStatusKey = (typeof ESTIMATE_STATUS_KEYS)[number];
