import { apiFetch, apiJson } from "@/lib/api";
import type {
  ProposalDetail,
  ProposalExportRecord,
  ProposalLocale,
  ProposalStatusResponse,
  ProposalSummary,
} from "@/lib/proposal-types";

export async function fetchProposals(): Promise<ProposalSummary[]> {
  return apiJson<ProposalSummary[]>("/proposals");
}

export async function fetchProposal(id: string): Promise<ProposalDetail> {
  return apiJson<ProposalDetail>(`/proposals/${id}`);
}

export async function deleteProposal(id: string): Promise<void> {
  const response = await apiFetch(`/proposals/${id}`, { method: "DELETE" });
  if (!response.ok && response.status !== 204) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(
      typeof payload === "object" && payload && "error" in payload
        ? String((payload as { error: string }).error)
        : "Failed to delete proposal",
    );
  }
}

export async function fetchProposalByEstimate(
  estimateId: string,
  locale: ProposalLocale,
): Promise<ProposalDetail | null> {
  const response = await apiFetch(
    `/proposals/by-estimate/${estimateId}?locale=${locale}`,
  );
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(
      typeof payload === "object" && payload && "error" in payload
        ? String((payload as { error: string }).error)
        : "Failed to load proposal",
    );
  }
  return response.json();
}

export async function generateProposal(body: {
  estimate_id: string;
  locale: ProposalLocale;
  include_poc: boolean;
}): Promise<ProposalDetail> {
  return apiJson<ProposalDetail>("/proposals/generate", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function fetchProposalStatus(
  id: string,
): Promise<ProposalStatusResponse> {
  return apiJson<ProposalStatusResponse>(`/proposals/${id}/status`);
}

export async function patchProposalSections(
  id: string,
  sections: Array<{
    part: "assessment" | "proposal" | "poc";
    section_id: string;
    body?: string;
    bullets?: string[];
    extra?: Record<string, string>;
  }>,
): Promise<ProposalDetail> {
  return apiJson<ProposalDetail>(`/proposals/${id}/sections`, {
    method: "PATCH",
    body: JSON.stringify({ sections }),
  });
}

export async function regenerateProposal(
  id: string,
  part: "assessment" | "proposal" | "poc" | "all",
): Promise<ProposalDetail> {
  return apiJson<ProposalDetail>(`/proposals/${id}/regenerate`, {
    method: "POST",
    body: JSON.stringify({ part }),
  });
}

export async function refreshProposal(id: string): Promise<ProposalDetail> {
  return apiJson<ProposalDetail>(`/proposals/${id}/refresh`, {
    method: "POST",
  });
}

export async function finalizeProposal(id: string): Promise<ProposalDetail> {
  return apiJson<ProposalDetail>(`/proposals/${id}/finalize`, {
    method: "POST",
  });
}

export async function createProposalExport(
  id: string,
  body: {
    format: "pdf" | "docx" | "md" | "xlsx";
    variant?: "full" | "assessment" | "proposal" | "poc";
    locale?: ProposalLocale;
    project_name?: string;
  },
): Promise<ProposalExportRecord> {
  return apiJson<ProposalExportRecord>(`/proposals/${id}/export`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function fetchProposalExports(
  proposalId: string,
): Promise<ProposalExportRecord[]> {
  return apiJson<ProposalExportRecord[]>(`/proposals/${proposalId}/exports`);
}

export async function downloadProposalExport(
  proposalId: string,
  exportId: string,
  inline = false,
): Promise<Blob> {
  const qs = inline ? "?inline=1" : "";
  const response = await apiFetch(
    `/proposals/${proposalId}/exports/${exportId}/download${qs}`,
  );
  if (!response.ok) {
    throw new Error("Download failed");
  }
  return response.blob();
}

export async function deleteProposalExport(
  proposalId: string,
  exportId: string,
): Promise<void> {
  const response = await apiFetch(
    `/proposals/${proposalId}/exports/${exportId}`,
    { method: "DELETE" },
  );
  // 404 = already gone (stale UI row); treat as success
  if (!response.ok && response.status !== 204 && response.status !== 404) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(
      typeof payload === "object" && payload && "error" in payload
        ? String((payload as { error: string }).error)
        : "Failed to delete export",
    );
  }
}

export async function sendProposalExportsEmail(
  proposalId: string,
  body: {
    to_email: string;
    export_ids: string[];
    message?: string;
  },
): Promise<{ to_email: string; export_ids: string[]; sent_at: string }> {
  return apiJson(`/proposals/${proposalId}/exports/email`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}
