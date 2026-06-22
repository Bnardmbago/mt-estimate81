import type {
  EstimateDetail,
  EstimateSummary,
} from "@/lib/estimate-types";
import { type ApiFetchResult, serverApiJson } from "@/lib/server-api";

export type {
  Actuals,
  CalculationResult,
  EstimateDetail,
  EstimateDocument,
  EstimateStatusKey,
  EstimateSummary,
  ExportRecord,
  ExtractedData,
  FeatureItem,
  GanttData,
} from "@/lib/estimate-types";

export type { ApiFetchResult };

export async function fetchEstimates(
  token: string,
): Promise<EstimateSummary[] | null> {
  const result = await serverApiJson<EstimateSummary[]>("/estimates", token);

  if (result.status === "unauthorized") {
    return null;
  }

  if (result.status !== "ok" || !Array.isArray(result.data)) {
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
  formTemplateId?: string,
): Promise<EstimateDetail | null> {
  const body: {
    project_name: string;
    locale: string;
    form_template_id?: string;
  } = {
    project_name: locale === "ja" ? "新規見積" : "New Estimate",
    locale,
  };
  if (formTemplateId) {
    body.form_template_id = formTemplateId;
  }

  const result = await serverApiJson<EstimateDetail>("/estimates", token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  return result.status === "ok" ? result.data : null;
}
