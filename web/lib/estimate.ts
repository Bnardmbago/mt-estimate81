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
  first_year_total_jpy: number;
  rate_card_version_id: string;
};

export type ExportRecord = {
  id: string;
  estimate_id: string;
  format: string;
  storage_path: string;
  locale: string;
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
  extracted_data: ExtractedData | null;
  maintenance_assumptions: Record<string, unknown>;
  calculation_result: CalculationResult | null;
  rate_card_id: string | null;
  rate_card_name: string | null;
  rate_card_version_id: string | null;
  rate_card_stale: boolean;
  project_start_date: string | null;
  feature_items: FeatureItem[];
  documents: EstimateDocument[];
  actuals: Actuals | null;
  created_at: string;
  updated_at: string;
};

import {
  type ApiFetchResult,
  serverApiJson,
} from "@/lib/server-api";

export type { ApiFetchResult };

export async function fetchEstimates(
  token: string,
): Promise<EstimateSummary[]> {
  const result = await serverApiJson<EstimateSummary[]>("/estimates", token);

  if (result.status !== "ok") {
    return [];
  }

  return result.data;
}

export async function fetchEstimateResult(
  id: string,
  token: string,
  locale?: string,
): Promise<ApiFetchResult<EstimateDetail>> {
  const query = locale ? `?display_locale=${encodeURIComponent(locale)}` : "";
  const headers = locale
    ? {
        "X-Display-Locale": locale,
        "X-Content-Locale": locale,
      }
    : undefined;

  return serverApiJson<EstimateDetail>(`/estimates/${id}${query}`, token, {
    headers,
  });
}

export async function fetchEstimate(
  id: string,
  token: string,
  locale?: string,
): Promise<EstimateDetail | null> {
  const result = await fetchEstimateResult(id, token, locale);
  return result.status === "ok" ? result.data : null;
}

export async function createEstimate(
  locale: string,
  token: string,
): Promise<EstimateDetail | null> {
  const result = await serverApiJson<EstimateDetail>("/estimates", token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      project_name: locale === "ja" ? "新規見積" : "New Estimate",
      locale,
    }),
  });

  return result.status === "ok" ? result.data : null;
}
