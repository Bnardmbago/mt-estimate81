"use client";

import { useEffect, useMemo, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import {
  createPresentationDraftFromReference,
  deleteAdminPreset,
  discardPresentationDraft,
  fetchPresentationDraft,
  updateAdminPreset,
  type PresentationDraft,
  type PresentationLocale,
  type PresentationPresetDetail,
} from "@/lib/presentation";
import {
  DEFAULT_COVER_TEMPLATE_CONFIG,
  templateHasCoverConfig,
} from "@/lib/cover-template-defaults";
import { clonePlainData } from "@/lib/clonePlainData";
import PresentationCoverDesigner from "./PresentationCoverDesigner";

type Props = {
  drafts: PresentationDraft[];
  templates: PresentationPresetDetail[];
  onChanged: () => Promise<void>;
  onRequestApprove: (draft: PresentationDraft) => void;
};

type EditTarget =
  | { kind: "catalog"; id: string }
  | { kind: "creating"; seedKey: string };

function generationStatus(draft: PresentationDraft): string {
  const meta = draft.generation_meta;
  if (meta && typeof meta === "object" && "status" in meta) {
    return String((meta as { status?: unknown }).status || "");
  }
  return "";
}

function coverConfigFromDraft(draft: PresentationDraft): Record<string, unknown> {
  const template = draft.template_draft || {};
  const config =
    template.config && typeof template.config === "object" && !Array.isArray(template.config)
      ? clonePlainData(template.config as Record<string, unknown>)
      : clonePlainData(DEFAULT_COVER_TEMPLATE_CONFIG);
  config.cover = true;
  if (!config.layout) config.layout = "executive_cover";
  if (!config.page) config.page = { size: "A4", orientation: "portrait" };
  return config;
}

async function waitForReferenceDraft(draftId: string): Promise<PresentationDraft> {
  const started = Date.now();
  while (Date.now() - started < 90_000) {
    const draft = await fetchPresentationDraft(draftId);
    const status = generationStatus(draft);
    if (status === "done") return draft;
    if (status === "failed") {
      const detail =
        Array.isArray(draft.errors) && draft.errors.length
          ? String(draft.errors[0])
          : "Reference generation failed";
      throw new Error(detail);
    }
    await new Promise((resolve) => window.setTimeout(resolve, 1500));
  }
  throw new Error("Timed out waiting for cover generation");
}

export default function PresentationCoverTab({
  templates,
  onChanged,
}: Props) {
  const t = useTranslations("admin.presentation");
  const tCover = useTranslations("admin.presentation.cover");
  const locale = useLocale() as PresentationLocale;
  const coverPresets = useMemo(
    () => templates.filter((row) => templateHasCoverConfig(row.config)),
    [templates],
  );

  const [editTarget, setEditTarget] = useState<EditTarget | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [createConfig, setCreateConfig] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const effectiveTarget: EditTarget | null =
    editTarget ?? (coverPresets[0] ? { kind: "catalog", id: coverPresets[0].id } : null);

  const activeCatalog =
    effectiveTarget?.kind === "catalog"
      ? coverPresets.find((row) => row.id === effectiveTarget.id) || null
      : null;

  useEffect(() => {
    if (effectiveTarget?.kind === "catalog" && activeCatalog) {
      setName(activeCatalog.name);
      setDescription(activeCatalog.description || "");
      setCreateConfig(null);
    }
  }, [effectiveTarget?.kind, activeCatalog?.id, activeCatalog?.name, activeCatalog?.description]);

  function beginCreate() {
    setEditTarget({ kind: "creating", seedKey: "blank" });
    setName("");
    setDescription("");
    setCreateConfig(null);
    setMessage(null);
  }

  function selectCatalog(id: string) {
    setEditTarget({ kind: "catalog", id });
    setMessage(null);
  }

  async function run(action: () => Promise<unknown>, success?: string) {
    setBusy(true);
    setMessage(null);
    try {
      await action();
      await onChanged();
      if (success) setMessage(success);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : t("saveError"));
    } finally {
      setBusy(false);
    }
  }

  async function toggleActive() {
    if (!activeCatalog) return;
    await run(() =>
      updateAdminPreset("templates", activeCatalog.id, {
        is_active: !activeCatalog.is_active,
      }),
    );
  }

  async function removeCatalog() {
    if (!activeCatalog || activeCatalog.is_default) {
      setMessage(t("cannotDeleteDefault"));
      return;
    }
    if (!window.confirm(t("deleteConfirm", { name: activeCatalog.name }))) return;
    await run(async () => {
      await deleteAdminPreset("templates", activeCatalog.id);
      setEditTarget(null);
    });
  }

  async function generateCoverFromReference(file: File) {
    setBusy(true);
    setMessage(tCover("generatingFromReference"));
    let draftId: string | null = null;
    try {
      const queued = await createPresentationDraftFromReference(file, {
        source_locale: locale,
      });
      draftId = queued.id;
      const ready = await waitForReferenceDraft(queued.id);
      const config = coverConfigFromDraft(ready);
      const nextName = String(
        ready.template_draft.name ||
          (locale === "ja" ? "参照表紙" : "Reference cover"),
      );
      const nextDescription = String(ready.template_draft.description || "");
      setName(nextName);
      setDescription(nextDescription);
      setCreateConfig(config);
      setEditTarget({ kind: "creating", seedKey: ready.id });
      setMessage(tCover("referenceReady"));
      await discardPresentationDraft(ready.id);
      await onChanged();
    } catch (error) {
      if (draftId) {
        try {
          await discardPresentationDraft(draftId);
          await onChanged();
        } catch {
          // ignore cleanup errors
        }
      }
      setMessage(error instanceof Error ? error.message : t("saveError"));
    } finally {
      setBusy(false);
    }
  }

  const inputClass =
    "w-full rounded border border-slate-300 px-3 py-2 dark:border-slate-600 dark:bg-slate-950";

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
        <h3 className="text-base font-semibold">{tCover("savedTitle")}</h3>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{tCover("savedHelp")}</p>
        <div className="mt-4 flex flex-wrap items-end justify-between gap-3">
          <label className="min-w-64 flex-1 text-sm">
            <span className="mb-1 block">{t("selectPreset")}</span>
            <select
              className={inputClass}
              value={effectiveTarget?.kind === "catalog" ? effectiveTarget.id : ""}
              disabled={coverPresets.length === 0}
              onChange={(event) => {
                if (event.target.value) selectCatalog(event.target.value);
              }}
            >
              {coverPresets.length === 0 ? (
                <option value="">{tCover("noSavedCovers")}</option>
              ) : (
                coverPresets.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name}
                    {row.is_default ? ` · ${t("defaultBadge")}` : ""}
                    {!row.is_active ? ` · ${t("inactiveBadge")}` : ""}
                  </option>
                ))
              )}
            </select>
          </label>
          <button type="button" className="header-btn" disabled={busy} onClick={beginCreate}>
            {t("newPreset")}
          </button>
          {activeCatalog && effectiveTarget?.kind === "catalog" ? (
            <>
              <button
                type="button"
                className="header-btn"
                disabled={busy}
                onClick={() => void toggleActive()}
              >
                {activeCatalog.is_active ? t("deactivate") : t("activate")}
              </button>
              {!activeCatalog.is_default ? (
                <button
                  type="button"
                  className="header-btn text-red-700"
                  disabled={busy}
                  onClick={() => void removeCatalog()}
                >
                  {t("delete")}
                </button>
              ) : null}
            </>
          ) : null}
        </div>
        {effectiveTarget?.kind === "creating" || effectiveTarget?.kind === "catalog" ? (
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <label className="text-sm">
              <span className="mb-1 block">{t("name")}</span>
              <input
                className={inputClass}
                value={name}
                disabled={busy}
                onChange={(event) => setName(event.target.value)}
              />
            </label>
            <label className="text-sm md:col-span-2">
              <span className="mb-1 block">{t("descriptionLabel")}</span>
              <input
                className={inputClass}
                value={description}
                disabled={busy}
                onChange={(event) => setDescription(event.target.value)}
              />
            </label>
          </div>
        ) : null}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
        <h3 className="text-base font-semibold">{tCover("generateFromReferenceTitle")}</h3>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
          {tCover("generateFromReferenceHelp")}
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <label className={`header-btn cursor-pointer ${busy ? "opacity-50" : ""}`}>
            {busy ? tCover("generatingFromReference") : t("generateFromReference")}
            <input
              type="file"
              className="hidden"
              accept="image/png,image/jpeg,application/pdf"
              disabled={busy}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void generateCoverFromReference(file);
                event.currentTarget.value = "";
              }}
            />
          </label>
        </div>
        <p className="mt-2 text-xs text-slate-500">{t("referenceHint")}</p>
      </section>

      {effectiveTarget?.kind === "creating" ||
      (effectiveTarget?.kind === "catalog" && activeCatalog) ? (
        <PresentationCoverDesigner
          mode="catalog"
          draft={null}
          catalogTemplate={effectiveTarget.kind === "catalog" ? activeCatalog : null}
          isCreating={effectiveTarget.kind === "creating"}
          createName={name}
          createDescription={description}
          createConfig={createConfig}
          createSeedKey={effectiveTarget.kind === "creating" ? effectiveTarget.seedKey : "blank"}
          catalogName={name}
          catalogDescription={description}
          templates={templates}
          onChanged={onChanged}
          onRequestApprove={() => undefined}
          onCatalogCreated={(id) => {
            setEditTarget({ kind: "catalog", id });
            setCreateConfig(null);
          }}
        />
      ) : (
        <section className="rounded-lg border border-slate-200 bg-white p-6 text-sm dark:border-slate-700 dark:bg-slate-900">
          <h3 className="font-semibold">{tCover("title")}</h3>
          <p className="mt-2 text-slate-600 dark:text-slate-300">{tCover("emptyHelp")}</p>
        </section>
      )}

      {message ? (
        <p className="text-sm text-slate-600 dark:text-slate-300" role="status">
          {message}
        </p>
      ) : null}
    </div>
  );
}
