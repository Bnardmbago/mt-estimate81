/** Client helpers for export destinations (Google / Canva). */

import { apiJson } from "@/lib/api";

export type DestinationSendResult = {
  destination: string;
  external_file_id?: string | null;
  external_url: string;
  export_id: string;
};

export async function sendEstimateExportToGoogle(
  exportId: string,
): Promise<DestinationSendResult> {
  return apiJson(`/exports/${exportId}/send-to/google`, { method: "POST" });
}

export async function sendEstimateExportToCanva(
  exportId: string,
): Promise<DestinationSendResult> {
  return apiJson(`/exports/${exportId}/send-to/canva`, { method: "POST" });
}

export async function fetchIntegrationStatus(): Promise<
  Array<{ provider: string; connected: boolean; configured: boolean }>
> {
  return apiJson("/integrations/status");
}

export function isDocxFormat(format: string): boolean {
  return format === "docx" || format === "docx_quotation" || format === "docx_internal";
}

export function isXlsxFormat(format: string): boolean {
  return format === "xlsx" || format === "xlsx_internal";
}

export function isPdfFormat(format: string): boolean {
  return format === "pdf" || format.startsWith("pdf_");
}

export function isMdFormat(format: string): boolean {
  return format === "md";
}

/** Extension family for Previous exports Format column (PDF / DOCX / XLSX / MD). */
export function formatFamilyLabel(format: string): string {
  if (isPdfFormat(format)) return "PDF";
  if (isDocxFormat(format)) return "DOCX";
  if (isXlsxFormat(format)) return "XLSX";
  if (isMdFormat(format)) return "MD";
  return format.toUpperCase();
}

export async function openGoogleAuthorize(): Promise<void> {
  const data = await apiJson<{ authorize_url: string }>("/integrations/google/connect");
  window.location.href = data.authorize_url;
}

export async function openCanvaAuthorize(): Promise<void> {
  const data = await apiJson<{ authorize_url: string }>("/integrations/canva/connect");
  window.location.href = data.authorize_url;
}

export async function ensureGoogleConnected(): Promise<boolean> {
  const status = await fetchIntegrationStatus();
  const google = status.find((s) => s.provider === "google");
  if (!google?.configured) {
    throw new Error("Google OAuth is not configured on the server");
  }
  if (!google.connected) {
    await openGoogleAuthorize();
    return false;
  }
  return true;
}

export async function ensureCanvaConnected(): Promise<boolean> {
  const status = await fetchIntegrationStatus();
  const canva = status.find((s) => s.provider === "canva");
  if (!canva?.configured) {
    throw new Error("Canva OAuth is not configured on the server");
  }
  if (!canva.connected) {
    await openCanvaAuthorize();
    return false;
  }
  return true;
}
