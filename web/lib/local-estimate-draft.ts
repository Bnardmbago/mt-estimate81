import type { EstimateDetail } from "@/lib/estimate-types";
import { defaultProjectNameForLocale } from "@/lib/formFields";
import type { FormTemplateDetail } from "@/lib/form-template";

/** Placeholder id for an estimate that exists only in the browser until first Save. */
export const LOCAL_ESTIMATE_DRAFT_ID = "local-draft";

export function isLocalEstimateDraft(estimate: Pick<EstimateDetail, "id">): boolean {
  return estimate.id === LOCAL_ESTIMATE_DRAFT_ID;
}

export function buildLocalEstimateDraft(
  template: FormTemplateDetail,
  locale: string,
): EstimateDetail {
  const now = new Date().toISOString();
  return {
    id: LOCAL_ESTIMATE_DRAFT_ID,
    project_name: defaultProjectNameForLocale(locale),
    client_name: "",
    status: "draft",
    locale,
    form_data: {},
    form_template_id: template.id,
    form_template_name: template.name,
    form_schema_snapshot: template.fields,
    extracted_data: null,
    maintenance_assumptions: {},
    nrc_rc_assumptions: { setup_cost_items: [], monthly_rc_items: [] },
    calculation_result: null,
    rate_card_id: null,
    rate_card_name: null,
    rate_card_version_id: null,
    rate_card_stale: false,
    complexity_profile: null,
    rate_card_auto_tuned: false,
    rate_card_tune_recommended: false,
    rate_card_auto_tune_enabled: true,
    project_start_date: null,
    theme_id: null,
    style_id: null,
    template_id: null,
    cover_values: {},
    feature_items: [],
    documents: [],
    actuals: null,
    created_at: now,
    updated_at: now,
  };
}
