import { apiJson } from "@/lib/api";

export type InternalDossierRateCard = {
  rate_card_id: string | null;
  name: string | null;
  version_number: number | null;
  effective_date: string | null;
  settings: Record<string, unknown>;
};

export type InternalDossierProposal = {
  id: string;
  locale: string;
  status: string;
  include_poc: boolean;
  assessment: Record<string, unknown> | null;
  proposal_body: Record<string, unknown> | null;
  poc: Record<string, unknown> | null;
};

export type InternalDossier = {
  estimate_id: string;
  project_name: string;
  client_name: string;
  status: string;
  locale: string;
  has_calculation: boolean;
  rate_card_stale: boolean;
  warnings: string[];
  report: Record<string, unknown>;
  rate_card: InternalDossierRateCard | null;
  proposals: InternalDossierProposal[];
};

export async function fetchInternalDossier(
  estimateId: string,
): Promise<InternalDossier> {
  return apiJson<InternalDossier>(`/estimates/${estimateId}/internal-dossier`);
}
