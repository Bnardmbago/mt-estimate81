import { apiFetch, apiJson, parseApiErrorPayload } from "@/lib/api";

export type PresentationPresetSummary = {
  id: string;
  name: string;
  description?: string | null;
  is_default: boolean;
  is_active: boolean;
  preview?: Record<string, string | number | boolean | null> | null;
};

export type PresentationPresetDetail = PresentationPresetSummary & {
  config: Record<string, unknown>;
  logo_storage_path?: string | null;
  has_logo?: boolean;
  logo_url?: string | null;
};

export type PresentationDefaults = {
  theme_id: string;
  style_id: string;
  template_id: string;
  cover_template_id?: string | null;
};

export type PresentationLocale = "en" | "ja";
export type PresentationCatalogKind = "themes" | "styles" | "templates";

export type PresentationDraftAxis = {
  id?: string;
  name?: string;
  description?: string | null;
  config?: Record<string, unknown>;
  [key: string]: unknown;
};

export type PresentationDraft = {
  id: string;
  status: string;
  source_locale: string;
  theme_draft: PresentationDraftAxis;
  style_draft: PresentationDraftAxis;
  template_draft: PresentationDraftAxis;
  target_theme_id?: string | null;
  target_style_id?: string | null;
  target_template_id?: string | null;
  generation_meta: Record<string, unknown>;
  errors: unknown[];
  created_at: string;
  updated_at: string;
  expires_at: string;
};

export type PresentationConsistencySuggestion = {
  id: string;
  target: "theme" | "style";
  field_path: string;
  before?: unknown;
  after?: unknown;
  confidence: number;
  rationale: string;
};

export type PresentationDraftAsset = {
  id: string;
  storage_path: string;
  filename: string;
  content_type?: string | null;
  size_bytes: number;
};

export type PresentationDraftApprovalResult = {
  theme_id: string;
  style_id: string;
  template_id: string;
};

export async function fetchPresentationThemes(): Promise<PresentationPresetSummary[]> {
  return apiJson("/presentation/themes");
}

export async function fetchPresentationStyles(): Promise<PresentationPresetSummary[]> {
  return apiJson("/presentation/styles");
}

export async function fetchPresentationTemplates(): Promise<PresentationPresetSummary[]> {
  return apiJson("/presentation/templates");
}

export async function fetchPresentationTemplate(
  templateId: string,
): Promise<PresentationPresetDetail> {
  return apiJson(`/presentation/templates/${encodeURIComponent(templateId)}`);
}

export async function fetchPresentationDefaults(): Promise<PresentationDefaults> {
  return apiJson("/presentation/defaults");
}

export async function fetchAdminPresentationThemes(): Promise<PresentationPresetDetail[]> {
  return apiJson("/admin/presentation/themes");
}

export async function fetchAdminPresentationStyles(): Promise<PresentationPresetDetail[]> {
  return apiJson("/admin/presentation/styles");
}

export async function fetchAdminPresentationTemplates(): Promise<PresentationPresetDetail[]> {
  return apiJson("/admin/presentation/templates");
}

export async function setAdminPresentationDefaults(
  body: Partial<PresentationDefaults>,
): Promise<PresentationDefaults> {
  return apiJson("/admin/presentation/defaults", {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export async function setAdminPresetDefault(
  kind: "themes" | "styles" | "templates",
  id: string,
): Promise<PresentationPresetDetail> {
  return apiJson(`/admin/presentation/${kind}/${id}/set-default`, {
    method: "POST",
  });
}

export async function updateAdminPreset(
  kind: "themes" | "styles" | "templates",
  id: string,
  body: {
    name?: string;
    description?: string | null;
    is_active?: boolean;
    config?: Record<string, unknown>;
  },
): Promise<PresentationPresetDetail> {
  return apiJson(`/admin/presentation/${kind}/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function createAdminPreset(
  kind: "themes" | "styles" | "templates",
  body: {
    id: string;
    name: string;
    description?: string | null;
    config?: Record<string, unknown>;
    is_active?: boolean;
    is_default?: boolean;
  },
): Promise<PresentationPresetDetail> {
  return apiJson(`/admin/presentation/${kind}`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function deleteAdminPreset(
  kind: "themes" | "styles" | "templates",
  id: string,
): Promise<void> {
  const response = await apiFetch(`/admin/presentation/${kind}/${id}`, {
    method: "DELETE",
  });
  if (!response.ok && response.status !== 204) {
    const payload = await response.json().catch(() => ({}));
    const { message } = parseApiErrorPayload(payload, "Failed to delete preset");
    throw new Error(message);
  }
}

export async function uploadThemeLogo(themeId: string, file: File): Promise<PresentationPresetDetail> {
  const form = new FormData();
  form.append("file", file);
  const response = await apiFetch(`/admin/presentation/themes/${themeId}/logo`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const { message } = parseApiErrorPayload(payload, "Logo upload failed");
    throw new Error(message);
  }
  return response.json();
}

export async function deleteThemeLogo(themeId: string): Promise<PresentationPresetDetail> {
  return apiJson(`/admin/presentation/themes/${themeId}/logo`, {
    method: "DELETE",
  });
}

export async function fetchPresentationDrafts(): Promise<PresentationDraft[]> {
  return apiJson("/admin/presentation/drafts");
}

export async function fetchPresentationDraft(draftId: string): Promise<PresentationDraft> {
  return apiJson(`/admin/presentation/drafts/${draftId}`);
}

export async function createPresentationDraft(
  body: {
    source_locale?: PresentationLocale;
    target_theme_id?: string | null;
    target_style_id?: string | null;
    target_template_id?: string | null;
  } = {},
): Promise<PresentationDraft> {
  return apiJson("/admin/presentation/drafts", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function createPresentationDraftFromReference(
  file: File,
  options: {
    source_locale: PresentationLocale;
    target_theme_id?: string | null;
    target_style_id?: string | null;
    target_template_id?: string | null;
  },
): Promise<PresentationDraft> {
  const form = new FormData();
  form.append("file", file);
  form.append("source_locale", options.source_locale);
  if (options.target_theme_id) form.append("target_theme_id", options.target_theme_id);
  if (options.target_style_id) form.append("target_style_id", options.target_style_id);
  if (options.target_template_id) form.append("target_template_id", options.target_template_id);
  return apiForm<PresentationDraft>("/admin/presentation/drafts/from-reference", form);
}

export async function updatePresentationDraft(
  draftId: string,
  body: {
    theme_draft?: PresentationDraftAxis;
    style_draft?: PresentationDraftAxis;
    template_draft?: PresentationDraftAxis;
  },
): Promise<PresentationDraft> {
  return apiJson(`/admin/presentation/drafts/${draftId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function uploadPresentationDraftAsset(
  draftId: string,
  file: File,
): Promise<PresentationDraftAsset> {
  const form = new FormData();
  form.append("file", file);
  return apiForm<PresentationDraftAsset>(
    `/admin/presentation/drafts/${draftId}/assets`,
    form,
  );
}

export async function uploadPresentationTemplateAsset(
  templateId: string,
  file: File,
): Promise<PresentationDraftAsset> {
  const form = new FormData();
  form.append("file", file);
  return apiForm<PresentationDraftAsset>(
    `/admin/presentation/templates/${encodeURIComponent(templateId)}/assets`,
    form,
  );
}

export async function deletePresentationDraftAsset(
  draftId: string,
  assetId: string,
): Promise<void> {
  const response = await apiFetch(
    `/admin/presentation/drafts/${draftId}/assets/${encodeURIComponent(assetId)}`,
    { method: "DELETE" },
  );
  if (!response.ok && response.status !== 204) {
    const payload = await response.json().catch(() => ({}));
    const { message } = parseApiErrorPayload(payload, "Failed to delete asset");
    throw new Error(message);
  }
}

export async function deletePresentationTemplateAsset(
  templateId: string,
  assetId: string,
): Promise<void> {
  const response = await apiFetch(
    `/admin/presentation/templates/${encodeURIComponent(templateId)}/assets/${encodeURIComponent(assetId)}`,
    { method: "DELETE" },
  );
  if (!response.ok && response.status !== 204) {
    const payload = await response.json().catch(() => ({}));
    const { message } = parseApiErrorPayload(payload, "Failed to delete asset");
    throw new Error(message);
  }
}

export function presentationAssetUrl(
  ownerKind: "draft" | "template",
  ownerId: string,
  assetId: string,
): string {
  return ownerKind === "template"
    ? `/admin/presentation/templates/${encodeURIComponent(ownerId)}/assets/${encodeURIComponent(assetId)}`
    : `/admin/presentation/drafts/${encodeURIComponent(ownerId)}/assets/${encodeURIComponent(assetId)}`;
}

export async function checkPresentationDraftConsistency(
  draftId: string,
): Promise<PresentationConsistencySuggestion[]> {
  const response = await apiJson<{ suggestions: PresentationConsistencySuggestion[] }>(
    `/admin/presentation/drafts/${draftId}/consistency`,
    { method: "POST" },
  );
  return response.suggestions;
}

export async function applyPresentationDraftSuggestions(
  draftId: string,
  suggestionIds?: string[],
): Promise<PresentationDraft> {
  return apiJson(`/admin/presentation/drafts/${draftId}/apply-suggestions`, {
    method: "POST",
    body: JSON.stringify({ suggestion_ids: suggestionIds }),
  });
}

export async function approvePresentationDraft(
  draftId: string,
  sourceLocale?: PresentationLocale,
): Promise<PresentationDraftApprovalResult> {
  return apiJson(`/admin/presentation/drafts/${draftId}/approve`, {
    method: "POST",
    body: JSON.stringify(sourceLocale ? { source_locale: sourceLocale } : {}),
  });
}

export async function discardPresentationDraft(draftId: string): Promise<void> {
  const response = await apiFetch(`/admin/presentation/drafts/${draftId}`, {
    method: "DELETE",
  });
  if (!response.ok && response.status !== 204) {
    const payload = await response.json().catch(() => ({}));
    const { message } = parseApiErrorPayload(payload, "Failed to discard draft");
    throw new Error(message);
  }
}

async function apiForm<T>(path: string, form: FormData): Promise<T> {
  const response = await apiFetch(path, { method: "POST", body: form });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const { message } = parseApiErrorPayload(payload, "Upload failed");
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}
