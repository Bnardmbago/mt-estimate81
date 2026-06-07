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

export type EstimateDetail = {
  id: string;
  project_name: string;
  client_name: string;
  status: string;
  locale: string;
  form_data: Record<string, unknown>;
  extracted_data: ExtractedData | null;
  maintenance_assumptions: Record<string, unknown>;
  feature_items: FeatureItem[];
  documents: EstimateDocument[];
  created_at: string;
  updated_at: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://api:8000";

export async function fetchEstimate(
  id: string,
  token: string,
): Promise<EstimateDetail | null> {
  const response = await fetch(`${API_URL}/estimates/${id}`, {
    headers: { Cookie: `access_token=${token}` },
    cache: "no-store",
  });

  if (!response.ok) {
    return null;
  }

  return response.json() as Promise<EstimateDetail>;
}

export async function createEstimate(
  locale: string,
  token: string,
): Promise<EstimateDetail | null> {
  const response = await fetch(`${API_URL}/estimates`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Cookie: `access_token=${token}`,
    },
    body: JSON.stringify({
      project_name: locale === "ja" ? "新規見積" : "New Estimate",
      client_name: locale === "ja" ? "未設定" : "TBD",
      locale,
    }),
  });

  if (!response.ok) {
    return null;
  }

  return response.json() as Promise<EstimateDetail>;
}
