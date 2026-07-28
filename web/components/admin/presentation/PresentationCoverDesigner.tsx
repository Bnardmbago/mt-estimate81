"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import {
  applyPresentationDraftSuggestions,
  checkPresentationDraftConsistency,
  createAdminPreset,
  deletePresentationDraftAsset,
  deletePresentationTemplateAsset,
  updateAdminPreset,
  updatePresentationDraft,
  uploadPresentationDraftAsset,
  uploadPresentationTemplateAsset,
  type PresentationConsistencySuggestion,
  type PresentationDraft,
  type PresentationLocale,
  type PresentationPresetDetail,
} from "@/lib/presentation";
import { DEFAULT_COVER_TEMPLATE_CONFIG } from "@/lib/cover-template-defaults";
import { clonePlainData } from "@/lib/clonePlainData";
import {
  normalizeGeometry,
  type CoverGeometry,
} from "@/lib/cover-geometry";
import {
  accentHexColor,
  coerceAccentShapes,
  createAccentShape,
  createEdgeStripe,
  duplicateAccentShape,
  legacyAccentToShape,
  type AccentEdge,
  type AccentPageDimensions,
  type AccentShape,
  type AccentShapeType,
} from "@/lib/cover-accent-shapes";
import { coverPageDimensions } from "@/lib/cover-preview-size";
import PresentationConsistencyPanel from "./PresentationConsistencyPanel";
import PresentationCoverAssetControls from "./PresentationCoverAssetControls";
import PresentationCoverFieldList from "./PresentationCoverFieldList";
import PresentationAccentShapesPanel from "./PresentationAccentShapesPanel";
import PresentationAccentShapeStyleControls, {
  defaultAccentGeometry,
  defaultAccentStyle,
} from "./PresentationAccentShapeStyleControls";
import PresentationCoverPreview, {
  type CoverAsset,
  type CoverDesign,
  type CoverField,
  type CoverPage,
} from "./PresentationCoverPreview";

type Props = {
  mode: "catalog" | "draft";
  draft: PresentationDraft | null;
  catalogTemplate: PresentationPresetDetail | null;
  isCreating?: boolean;
  createName?: string;
  createDescription?: string;
  createConfig?: Record<string, unknown> | null;
  createSeedKey?: string;
  catalogName?: string;
  catalogDescription?: string;
  templates: PresentationPresetDetail[];
  onChanged: () => Promise<void>;
  onRequestApprove: (draft: PresentationDraft) => void;
  onCatalogCreated?: (id: string) => void;
};

const DEFAULT_DESIGN: CoverDesign = {
  alignment: "left",
  padding_mm: 24,
  accent: { enabled: true, width_mm: 48 },
  typography: { title_pt: 30, metadata_pt: 10 },
  colors: {
    background: "FFFFFF",
    title: "1E3A5F",
    text: "334155",
    accent: "2563EB",
  },
  assets: [],
};

export default function PresentationCoverDesigner({
  mode,
  draft,
  catalogTemplate,
  isCreating = false,
  createName = "",
  createDescription = "",
  createConfig = null,
  createSeedKey = "blank",
  catalogName = "",
  catalogDescription = "",
  templates,
  onChanged,
  onRequestApprove,
  onCatalogCreated,
}: Props) {
  const t = useTranslations("admin.presentation.cover");
  const tRoot = useTranslations("admin.presentation");
  const locale = useLocale() as PresentationLocale;
  const [templatePayload, setTemplatePayload] = useState<Record<string, unknown>>({});
  const [coverMode, setCoverMode] = useState<"default" | "enabled" | "disabled">("enabled");
  const [previewUrls, setPreviewUrls] = useState<Record<string, string>>({});
  const [selectedLayerId, setSelectedLayerId] = useState<string | null>(null);
  const [snapEnabled, setSnapEnabled] = useState(false);
  const previewUrlsRef = useRef<Record<string, string>>({});
  const [suggestions, setSuggestions] = useState<PresentationConsistencySuggestion[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const sourceKey = useMemo(() => {
    if (mode === "draft") return `draft:${draft?.id || ""}`;
    if (isCreating) return `creating:${createSeedKey}`;
    return `catalog:${catalogTemplate?.id || ""}`;
  }, [mode, draft?.id, isCreating, createSeedKey, catalogTemplate?.id]);

  useEffect(() => {
    if (mode === "draft" && draft) {
      const payload = clonePlainData(draft.template_draft || {});
      const selectedConfig = configOf(payload);
      const design = designOf(selectedConfig.cover_design);
      selectedConfig.cover_design = {
        ...design,
        assets: normalizeCoverAssets(design.assets || []),
      };
      setTemplatePayload({ ...payload, config: selectedConfig });
      setCoverMode(
        Object.prototype.hasOwnProperty.call(selectedConfig, "cover")
          ? selectedConfig.cover
            ? "enabled"
            : "disabled"
          : "default",
      );
    } else if (isCreating) {
      const seeded = createConfig && typeof createConfig === "object"
        ? clonePlainData(createConfig)
        : clonePlainData(DEFAULT_COVER_TEMPLATE_CONFIG);
      if (seeded && typeof seeded === "object") {
        (seeded as Record<string, unknown>).cover = true;
      }
      setTemplatePayload({
        name: createName || "",
        description: createDescription || "",
        config: seeded,
      });
      setCoverMode("enabled");
    } else if (catalogTemplate) {
      const nextConfig = clonePlainData(
        catalogTemplate.config || DEFAULT_COVER_TEMPLATE_CONFIG,
      ) as Record<string, unknown>;
      const design = designOf(nextConfig.cover_design);
      nextConfig.cover_design = {
        ...design,
        assets: normalizeCoverAssets(design.assets || []),
      };
      setTemplatePayload({
        name: catalogTemplate.name,
        description: catalogTemplate.description || "",
        config: nextConfig,
      });
      setCoverMode(catalogTemplate.config?.cover ? "enabled" : "disabled");
    } else {
      setTemplatePayload({});
    }
    setSuggestions(null);
    setMessage(null);
    setSelectedLayerId(null);
    // Reset editor state only when the edit target identity changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- sourceKey encodes the target
  }, [sourceKey]);

  useEffect(() => () => {
    Object.values(previewUrlsRef.current).forEach((url) => URL.revokeObjectURL(url));
  }, []);

  const canEdit =
    (mode === "draft" && Boolean(draft)) ||
    (mode === "catalog" && (isCreating || Boolean(catalogTemplate)));

  if (!canEdit) {
    return null;
  }

  const config = configOf(templatePayload);
  const page = pageOf(config.page);
  const design = designOf(config.cover_design);
  const fields = fieldsOf(config.cover_fields);
  const targetTemplate =
    mode === "draft" && draft
      ? templates.find((template) => template.id === draft.target_template_id)
      : catalogTemplate;
  const templateDefaultEnabled = Boolean(targetTemplate?.config.cover ?? false);
  const enabled =
    mode === "catalog"
      ? true
      : coverMode === "enabled" || (coverMode === "default" && templateDefaultEnabled);
  const pageMm = pageDimensionsMm(page);
  const themeAccent = resolveThemeAccent(mode === "draft" ? draft : null, design);
  const shapes = shapesOf(design, pageMm);
  const selectedShapeId = selectedLayerId?.startsWith("shape:")
    ? selectedLayerId.slice("shape:".length)
    : null;
  const selectedShape = shapes.find((shape) => shape.id === selectedShapeId) ?? null;
  const assetOwnerId =
    mode === "draft" && draft
      ? draft.id
      : isCreating
        ? ""
        : catalogTemplate?.id || "";
  const assetOwnerKind = mode === "draft" ? "draft" : "template";

  function updateConfig(patch: Record<string, unknown>) {
    setTemplatePayload((current) => ({
      ...current,
      config: { ...configOf(current), ...patch },
    }));
    setSuggestions(null);
  }

  function updateDesign(patch: Partial<CoverDesign>) {
    updateConfig({ cover_design: deepMergeDesign(design, patch) });
  }

  function changeCoverMode(next: "default" | "enabled" | "disabled") {
    setCoverMode(next);
    const nextConfig = { ...config };
    if (next === "default") delete nextConfig.cover;
    else nextConfig.cover = next === "enabled";
    setTemplatePayload((current) => ({ ...current, config: nextConfig }));
    setSuggestions(null);
  }

  async function run<T>(action: () => Promise<T>, success?: string): Promise<T | null> {
    setBusy(true);
    setMessage(null);
    try {
      const result = await action();
      if (success) setMessage(success);
      return result;
    } catch (error) {
      setMessage(error instanceof Error ? error.message : t("saveError"));
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function persist() {
    if (mode === "draft" && draft) {
      const updated = await run(
        () => updatePresentationDraft(draft.id, { template_draft: templatePayload }),
        t("saved"),
      );
      if (updated) {
        setTemplatePayload(clonePlainData(updated.template_draft));
        await onChanged();
      }
      return updated;
    }

    const nextConfig = {
      ...config,
      cover: true,
    };
    const nextName = (catalogName || String(templatePayload.name || "")).trim();
    const nextDescription =
      (catalogDescription || String(templatePayload.description || "")).trim() || null;

    if (isCreating) {
      if (!nextName) {
        setMessage(tRoot("createRequired"));
        return null;
      }
      const existingIds = new Set(templates.map((row) => row.id));
      const slug = uniqueCoverPresetId(nextName, existingIds);
      const created = await run(
        () =>
          createAdminPreset("templates", {
            id: slug,
            name: nextName,
            description: nextDescription || createDescription.trim() || null,
            config: nextConfig,
            is_active: true,
          }),
        t("saved"),
      );
      if (created) {
        await onChanged();
        onCatalogCreated?.(created.id);
      }
      return created;
    }

    if (!catalogTemplate) return null;
    const updated = await run(
      () =>
        updateAdminPreset("templates", catalogTemplate.id, {
          name: nextName || catalogTemplate.name,
          description: nextDescription,
          config: nextConfig,
        }),
      t("saved"),
    );
    if (updated) {
      setTemplatePayload({
        name: updated.name,
        description: updated.description || "",
        config: clonePlainData(updated.config),
      });
      await onChanged();
    }
    return updated;
  }

  async function upload(role: CoverAsset["role"], file: File) {
    if (mode === "catalog" && isCreating) {
      setMessage(t("saveBeforeUpload"));
      return;
    }
    const previous = (design.assets || []).find((item) => item.role === role);
    const uploaded = await run(() =>
      mode === "draft" && draft
        ? uploadPresentationDraftAsset(draft.id, file)
        : uploadPresentationTemplateAsset(catalogTemplate!.id, file),
    );
    if (!uploaded) return;
    const asset: CoverAsset = {
      id: uploaded.id,
      role,
      storage_path: uploaded.storage_path,
      filename: uploaded.filename,
      x: previous?.x ?? (role === "logo" ? 85 : 50),
      y: previous?.y ?? (role === "logo" ? 15 : role === "decorative" ? 85 : 50),
      zoom: previous?.zoom ?? 1,
      opacity: previous?.opacity ?? 1,
      ...(role === "background"
        ? { fit: previous?.fit || ("cover" as const) }
        : {
            rotation: previous?.rotation ?? 0,
            geometry:
              previous?.geometry ||
              defaultAssetGeometry(role, previous?.x, previous?.y),
          }),
    };
    const previewUrl = URL.createObjectURL(file);
    if (previous?.id && previewUrlsRef.current[previous.id]?.startsWith("blob:")) {
      URL.revokeObjectURL(previewUrlsRef.current[previous.id]);
    }
    previewUrlsRef.current = { ...previewUrlsRef.current, [uploaded.id]: previewUrl };
    setPreviewUrls(previewUrlsRef.current);
    const nextAssets = [
      ...(design.assets || []).filter((item) => item.role !== role),
      asset,
    ];
    updateDesign({ assets: nextAssets });

    // Persist immediately so storage references survive reload (plan: approved assets persist).
    const saved = await persistWithAssets(nextAssets);
    if (saved && previous?.id && previous.id !== uploaded.id) {
      await deleteStoredAsset(previous.id).catch(() => undefined);
    }
  }

  async function removeAsset(role: CoverAsset["role"]) {
    const previous = (design.assets || []).find((item) => item.role === role);
    const nextAssets = (design.assets || []).filter((asset) => asset.role !== role);
    updateDesign({ assets: nextAssets });
    if (selectedLayerId === `asset:${role}`) setSelectedLayerId(null);
    const saved = await persistWithAssets(nextAssets);
    if (saved && previous?.id) {
      if (previewUrlsRef.current[previous.id]?.startsWith("blob:")) {
        URL.revokeObjectURL(previewUrlsRef.current[previous.id]);
      }
      const nextPreview = { ...previewUrlsRef.current };
      delete nextPreview[previous.id];
      previewUrlsRef.current = nextPreview;
      setPreviewUrls(nextPreview);
      await deleteStoredAsset(previous.id).catch(() => undefined);
    }
  }

  async function deleteStoredAsset(assetId: string) {
    if (mode === "draft" && draft) {
      await deletePresentationDraftAsset(draft.id, assetId);
      return;
    }
    if (catalogTemplate?.id) {
      await deletePresentationTemplateAsset(catalogTemplate.id, assetId);
    }
  }

  async function persistWithAssets(assets: CoverAsset[]) {
    const nextDesign = deepMergeDesign(design, { assets });
    const nextConfig = {
      ...config,
      cover: true,
      cover_design: nextDesign,
    };
    if (mode === "draft" && draft) {
      const payload = {
        ...templatePayload,
        config: nextConfig,
      };
      const updated = await run(
        () => updatePresentationDraft(draft.id, { template_draft: payload }),
        t("saved"),
      );
      if (updated) {
        setTemplatePayload(clonePlainData(updated.template_draft));
        await onChanged();
      }
      return updated;
    }
    if (!catalogTemplate) return null;
    const updated = await run(
      () =>
        updateAdminPreset("templates", catalogTemplate.id, {
          name: catalogName || catalogTemplate.name,
          description: (catalogDescription || catalogTemplate.description || "").trim() || null,
          config: nextConfig,
        }),
      t("saved"),
    );
    if (updated) {
      setTemplatePayload({
        name: updated.name,
        description: updated.description || "",
        config: clonePlainData(updated.config),
      });
      await onChanged();
    }
    return updated;
  }

  function changeAsset(role: CoverAsset["role"], patch: Partial<CoverAsset>) {
    updateDesign({
      assets: (design.assets || []).map((asset) => {
        if (asset.role !== role) return asset;
        const next = { ...asset, ...patch };
        if (role !== "background") {
          next.geometry = syncAssetGeometry(next, patch);
        }
        return next;
      }),
    });
  }

  function changeFieldGeometry(key: string, geometry: CoverGeometry) {
    updateConfig({
      cover_fields: fields.map((field) =>
        field.key === key ? { ...field, geometry } : field,
      ),
    });
  }

  function changeAssetGeometry(role: CoverAsset["role"], geometry: CoverGeometry) {
    changeAsset(role, {
      geometry,
      position: "custom",
      x: geometry.x_pct + geometry.width_pct / 2,
      y: geometry.y_pct + (geometry.height_pct ?? 10) / 2,
    });
  }

  function updateShapes(next: AccentShape[]) {
    updateDesign({ accent_shapes: next });
  }

  function updateShape(id: string, patch: Partial<AccentShape>) {
    updateShapes(shapes.map((shape) => (shape.id === id ? { ...shape, ...patch } : shape)));
  }

  function addShape(type: AccentShapeType) {
    const shape = createAccentShape(type, themeAccent);
    updateShapes([...shapes, shape]);
    setSelectedLayerId(`shape:${shape.id}`);
  }

  function addEdge(edge: AccentEdge) {
    const shape = createEdgeStripe(edge, pageMm);
    updateShapes([...shapes, shape]);
    setSelectedLayerId(`shape:${shape.id}`);
  }

  function duplicateShape(id: string) {
    const source = shapes.find((shape) => shape.id === id);
    if (!source) return;
    const copy = duplicateAccentShape(source);
    const index = shapes.findIndex((shape) => shape.id === id);
    const next = [...shapes];
    next.splice(index + 1, 0, copy);
    updateShapes(next);
    setSelectedLayerId(`shape:${copy.id}`);
  }

  function deleteShape(id: string) {
    updateShapes(shapes.filter((shape) => shape.id !== id));
    if (selectedLayerId === `shape:${id}`) setSelectedLayerId(null);
  }

  function reorderShape(id: string, direction: "up" | "down") {
    const index = shapes.findIndex((shape) => shape.id === id);
    const target = direction === "up" ? index - 1 : index + 1;
    if (index < 0 || target < 0 || target >= shapes.length) return;
    const next = [...shapes];
    [next[index], next[target]] = [next[target], next[index]];
    updateShapes(next);
  }

  function changeShapeGeometry(id: string, geometry: AccentShape["geometry"]) {
    const shape = shapes.find((item) => item.id === id);
    let next = geometry;
    if (shape?.type === "circle") {
      const diameter = Math.min(geometry.width_pct, geometry.height_pct);
      next = { ...geometry, width_pct: diameter, height_pct: diameter };
    }
    updateShape(id, { geometry: next });
  }

  function changeLayerOrder(
    action: "forward" | "backward" | "front" | "back",
    geometry: CoverGeometry,
  ) {
    const allZ = [
      ...fields.map((field) => field.geometry?.z_index ?? 0),
      ...(design.assets || []).map((asset) => asset.geometry?.z_index ?? 0),
      ...shapes.map((shape) => shape.geometry.z_index),
    ];
    const maximum = Math.max(0, ...allZ);
    const zIndex =
      action === "front"
        ? Math.min(999, maximum + 1)
        : action === "back"
          ? 0
          : action === "forward"
            ? Math.min(999, geometry.z_index + 1)
            : Math.max(0, geometry.z_index - 1);
    const next = normalizeGeometry({ ...geometry, z_index: zIndex });
    if (selectedLayerId?.startsWith("field:")) {
      changeFieldGeometry(fieldKeyFromLayerId(selectedLayerId), next);
    } else if (selectedLayerId?.startsWith("asset:")) {
      changeAssetGeometry(selectedLayerId.split(":")[1] as CoverAsset["role"], next);
    } else if (selectedShapeId) {
      changeShapeGeometry(selectedShapeId, {
        x_pct: next.x_pct,
        y_pct: next.y_pct,
        width_pct: next.width_pct,
        height_pct: next.height_pct ?? geometry.height_pct ?? 1,
        rotation_deg: next.rotation_deg ?? geometry.rotation_deg ?? 0,
        z_index: next.z_index,
      });
    }
  }

  async function checkConsistency() {
    if (mode !== "draft" || !draft) return;
    const saved = await persist();
    if (!saved) return;
    const result = await run(() => checkPresentationDraftConsistency(draft.id));
    if (result) setSuggestions(result);
  }

  async function applySuggestions(ids?: string[]) {
    if (mode !== "draft" || !draft) return;
    const result = await run(
      () => applyPresentationDraftSuggestions(draft.id, ids),
      t("suggestionsApplied"),
    );
    if (!result) return;
    setTemplatePayload(clonePlainData(result.template_draft));
    await onChanged();
    const refreshed = await run(() => checkPresentationDraftConsistency(draft.id));
    if (refreshed) setSuggestions(refreshed);
  }

  async function reviewApproval() {
    if (mode !== "draft" || !draft) return;
    const updated = await persist();
    if (updated && typeof updated === "object" && "id" in updated) {
      onRequestApprove(updated as PresentationDraft);
    }
  }

  return (
    <div className="space-y-4">
      {mode === "draft" ? (
        <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
          <div className="grid gap-3 md:grid-cols-[1fr_14rem]">
            <div className="text-sm">
              <span className="mb-1 block">{t("draft")}</span>
              <p className="rounded border border-slate-200 px-3 py-2 dark:border-slate-700">
                {String(draft?.template_draft.name || draft?.theme_draft.name || t("untitled"))}
              </p>
            </div>
            <label className="text-sm">
              <span className="mb-1 block">{t("coverState")}</span>
              <select
                className="w-full rounded border border-slate-300 px-3 py-2 dark:border-slate-600 dark:bg-slate-950"
                value={coverMode}
                onChange={(event) =>
                  changeCoverMode(event.target.value as typeof coverMode)
                }
              >
                <option value="default">{t("templateDefault")}</option>
                <option value="enabled">{t("enabled")}</option>
                <option value="disabled">{t("disabled")}</option>
              </select>
            </label>
          </div>
        </section>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.72fr)]">
        <div className="space-y-4">
          <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
            <h3 className="text-sm font-semibold">{t("layout")}</h3>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <Select
                label={t("alignment")}
                value={design.alignment || "left"}
                options={["left", "center", "right"]}
                labelFor={(value) => t(`alignments.${value}`)}
                onChange={(alignment) =>
                  updateDesign({ alignment: alignment as CoverDesign["alignment"] })
                }
              />
              <NumberUnit
                label={t("padding")}
                value={design.padding_mm ?? 24}
                unit="mm"
                min={0}
                max={80}
                onChange={(padding_mm) => updateDesign({ padding_mm })}
              />
              <NumberUnit
                label={t("titleFont")}
                value={design.typography?.title_pt ?? 30}
                unit="pt"
                min={8}
                max={72}
                onChange={(title_pt) =>
                  updateDesign({ typography: { ...design.typography, title_pt } })
                }
              />
              <NumberUnit
                label={t("metadataFont")}
                value={design.typography?.metadata_pt ?? 10}
                unit="pt"
                min={6}
                max={30}
                onChange={(metadata_pt) =>
                  updateDesign({ typography: { ...design.typography, metadata_pt } })
                }
              />
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {(["background", "title", "text", "accent"] as const).map((colorName) => (
                <ColorControl
                  key={colorName}
                  label={t(`colors.${colorName}`)}
                  value={design.colors?.[colorName] || defaultColor(colorName)}
                  onChange={(value) =>
                    updateDesign({ colors: { ...design.colors, [colorName]: value } })
                  }
                />
              ))}
            </div>
          </section>

          <PresentationCoverAssetControls
            assets={design.assets || []}
            busy={busy}
            onUpload={upload}
            onChange={changeAsset}
            onRemove={(role) => {
              void removeAsset(role);
            }}
          />
          <PresentationCoverFieldList
            fields={fields}
            locale={locale}
            selectedKey={selectedFieldKey(selectedLayerId, fields)}
            onSelect={(key) => setSelectedLayerId(fieldLayerId(key))}
            onChange={(cover_fields) => {
              updateConfig({ cover_fields });
              const selectedKey = selectedFieldKey(selectedLayerId, fields);
              if (
                selectedKey !== null &&
                !cover_fields.some((field) => field.key === selectedKey)
              ) {
                setSelectedLayerId(null);
              }
            }}
          />
          <PresentationAccentShapesPanel
            shapes={shapes}
            selectedId={selectedShapeId}
            onSelect={(id) => setSelectedLayerId(`shape:${id}`)}
            onAddShape={addShape}
            onAddEdge={addEdge}
            onRename={(id, shapeName) => updateShape(id, { name: shapeName })}
            onToggleVisible={(id) => {
              const shape = shapes.find((item) => item.id === id);
              if (shape) updateShape(id, { visible: !shape.visible });
            }}
            onToggleLock={(id) => {
              const shape = shapes.find((item) => item.id === id);
              if (shape) updateShape(id, { locked: !shape.locked });
            }}
            onDuplicate={duplicateShape}
            onDelete={deleteShape}
            onReorder={reorderShape}
          />
          {selectedShape ? (
            <PresentationAccentShapeStyleControls
              key={selectedShape.id}
              shape={selectedShape}
              themeAccent={themeAccent}
              onChange={(patch) => updateShape(selectedShape.id, patch)}
              onResetStyle={() =>
                updateShape(
                  selectedShape.id,
                  defaultAccentStyle(selectedShape.type, themeAccent),
                )
              }
              onResetGeometry={() =>
                updateShape(selectedShape.id, {
                  geometry: {
                    ...defaultAccentGeometry(selectedShape.type),
                    z_index: selectedShape.geometry.z_index,
                  },
                })
              }
            />
          ) : null}
        </div>
        <div className="space-y-4 xl:sticky xl:top-4 xl:self-start">
          {assetOwnerId || Object.keys(previewUrls).length > 0 || !design.assets?.length ? (
            <PresentationCoverPreview
              assetOwnerId={assetOwnerId || "pending"}
              assetOwnerKind={assetOwnerKind}
              enabled={enabled}
              page={page}
              design={design}
              fields={fields}
              shapes={shapes}
              themeAccent={themeAccent}
              locale={locale}
              previewUrls={previewUrls}
              selectedLayerId={selectedLayerId}
              snapEnabled={snapEnabled}
              onSnapEnabledChange={setSnapEnabled}
              onSelectLayer={setSelectedLayerId}
              onFieldGeometryChange={changeFieldGeometry}
              onAssetGeometryChange={changeAssetGeometry}
              onShapeGeometryChange={changeShapeGeometry}
              onDeleteAsset={(role) => {
                updateDesign({
                  assets: (design.assets || []).filter((asset) => asset.role !== role),
                });
                setSelectedLayerId(null);
              }}
              onDeleteShape={deleteShape}
              onLayerOrder={changeLayerOrder}
              onEnableCover={() => changeCoverMode("enabled")}
            />
          ) : null}
          <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
            <p className="text-xs text-slate-500">
              {t("pageInherited", {
                size: page.size,
                orientation: t(page.orientation),
              })}
            </p>
            {message ? (
              <p className="mt-2 text-sm text-slate-700 dark:text-slate-200">{message}</p>
            ) : null}
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                className="header-btn"
                disabled={busy}
                onClick={() => void persist()}
              >
                {busy
                  ? t("saving")
                  : mode === "draft"
                    ? t("saveDraft")
                    : tRoot("saveEdit")}
              </button>
              {mode === "draft" ? (
                <>
                  <button
                    type="button"
                    className="header-btn"
                    disabled={busy}
                    onClick={() => void checkConsistency()}
                  >
                    {t("checkConsistency")}
                  </button>
                  <button
                    type="button"
                    className="header-btn header-btn-active"
                    disabled={busy}
                    onClick={() => void reviewApproval()}
                  >
                    {t("reviewApprove")}
                  </button>
                </>
              ) : null}
            </div>
          </section>
          {mode === "draft" && suggestions ? (
            <PresentationConsistencyPanel
              key={suggestions.map((item) => item.id).join("|")}
              suggestions={suggestions}
              busy={busy}
              onApply={applySuggestions}
              onDismiss={() => setSuggestions(null)}
              onReset={checkConsistency}
            />
          ) : null}
        </div>
      </div>
    </div>
  );
}

function configOf(payload: Record<string, unknown>): Record<string, unknown> {
  const config = payload.config;
  return config && typeof config === "object" && !Array.isArray(config)
    ? (config as Record<string, unknown>)
    : {};
}

function pageOf(value: unknown): CoverPage {
  const page =
    value && typeof value === "object" && !Array.isArray(value)
      ? (value as Record<string, unknown>)
      : {};
  return {
    size: String(page.size || "A4"),
    orientation: page.orientation === "landscape" ? "landscape" : "portrait",
  };
}

function designOf(value: unknown): CoverDesign {
  const design =
    value && typeof value === "object" && !Array.isArray(value)
      ? (value as CoverDesign)
      : {};
  return deepMergeDesign(DEFAULT_DESIGN, design);
}

function fieldsOf(value: unknown): CoverField[] {
  return Array.isArray(value)
    ? value.filter((field): field is CoverField => Boolean(field && typeof field === "object"))
    : [];
}

function deepMergeDesign(base: CoverDesign, patch: Partial<CoverDesign>): CoverDesign {
  return {
    ...base,
    ...patch,
    accent: { ...base.accent, ...patch.accent },
    typography: { ...base.typography, ...patch.typography },
    colors: { ...base.colors, ...patch.colors },
    assets: patch.assets ?? base.assets ?? [],
  };
}

function normalizeCoverAssets(assets: CoverAsset[]): CoverAsset[] {
  return assets.map((asset) => {
    if (asset.role === "background" || asset.geometry) return asset;
    return {
      ...asset,
      geometry: defaultAssetGeometry(asset.role, asset.x, asset.y),
    };
  });
}

function defaultAssetGeometry(
  role: CoverAsset["role"],
  x?: number,
  y?: number,
): CoverGeometry {
  const width = role === "logo" ? 20 : 30;
  const height = role === "logo" ? 10 : 20;
  const centerX = x ?? (role === "logo" ? 85 : 70);
  const centerY = y ?? (role === "logo" ? 15 : 80);
  return normalizeGeometry({
    x_pct: Math.max(0, centerX - width / 2),
    y_pct: Math.max(0, centerY - height / 2),
    width_pct: width,
    height_pct: height,
    z_index: role === "logo" ? 10 : 5,
  })!;
}

function syncAssetGeometry(
  asset: CoverAsset,
  patch: Partial<CoverAsset>,
): CoverGeometry | undefined {
  if (patch.geometry) return patch.geometry;
  const current =
    asset.geometry ||
    defaultAssetGeometry(asset.role, asset.x, asset.y);
  if (patch.x === undefined && patch.y === undefined) return current;
  const width = current.width_pct;
  const height = current.height_pct ?? 10;
  const centerX = patch.x ?? asset.x ?? current.x_pct + width / 2;
  const centerY = patch.y ?? asset.y ?? current.y_pct + height / 2;
  return normalizeGeometry({
    ...current,
    x_pct: Math.max(0, centerX - width / 2),
    y_pct: Math.max(0, centerY - height / 2),
    width_pct: width,
    height_pct: height,
  })!;
}

function Select({
  label,
  value,
  options,
  labelFor,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  labelFor: (value: string) => string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="text-sm">
      <span className="mb-1 block">{label}</span>
      <select
        className="w-full rounded border border-slate-300 px-3 py-2 dark:border-slate-600 dark:bg-slate-950"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {labelFor(option)}
          </option>
        ))}
      </select>
    </label>
  );
}

function NumberUnit({
  label,
  value,
  unit,
  min,
  max,
  onChange,
}: {
  label: string;
  value: number;
  unit: string;
  min: number;
  max: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="text-sm">
      <span className="mb-1 block">{label}</span>
      <span className="flex">
        <input
          className="min-w-0 flex-1 rounded-l border border-slate-300 px-3 py-2 dark:border-slate-600 dark:bg-slate-950"
          type="number"
          value={value}
          min={min}
          max={max}
          onChange={(event) => onChange(Number(event.target.value))}
        />
        <span className="flex items-center rounded-r border border-l-0 border-slate-300 bg-slate-100 px-3 text-xs dark:border-slate-600 dark:bg-slate-800">
          {unit}
        </span>
      </span>
    </label>
  );
}

function ColorControl({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const hex = value.replace("#", "").toUpperCase();
  const picker = /^[0-9A-F]{6}$/.test(hex) ? `#${hex}` : "#000000";
  return (
    <label className="text-sm">
      <span className="mb-1 block">{label}</span>
      <span className="flex gap-2">
        <input
          type="color"
          className="h-10 w-12 rounded border border-slate-300"
          value={picker}
          onChange={(event) => onChange(event.target.value.slice(1).toUpperCase())}
        />
        <input
          className="min-w-0 flex-1 rounded border border-slate-300 px-3 py-2 font-mono dark:border-slate-600 dark:bg-slate-950"
          value={hex}
          maxLength={6}
          onChange={(event) => onChange(event.target.value.replace("#", "").toUpperCase())}
        />
      </span>
    </label>
  );
}

function defaultColor(name: "background" | "title" | "text" | "accent") {
  return { background: "FFFFFF", title: "1E3A5F", text: "334155", accent: "2563EB" }[name];
}

function selectedFieldKey(selectedLayerId: string | null, fields: CoverField[]): string | null {
  if (!selectedLayerId?.startsWith("field:")) return null;
  const key = fieldKeyFromLayerId(selectedLayerId);
  return fields.some((field) => field.key === key) ? key : null;
}

function fieldLayerId(key: string) {
  return `field:${encodeURIComponent(key)}`;
}

function fieldKeyFromLayerId(layerId: string) {
  return decodeURIComponent(layerId.slice("field:".length));
}

function pageDimensionsMm(page: CoverPage): AccentPageDimensions {
  const [width_mm, height_mm] = coverPageDimensions(page.size, page.orientation);
  return { width_mm, height_mm };
}

function shapesOf(design: CoverDesign, page: AccentPageDimensions): AccentShape[] {
  if (Array.isArray(design.accent_shapes)) return coerceAccentShapes(design.accent_shapes);
  const legacy = legacyAccentToShape(design.accent, page);
  return legacy ? [legacy] : [];
}

function resolveThemeAccent(
  draft: PresentationDraft | null,
  design: CoverDesign,
): string {
  const themeConfig = draft?.theme_draft?.config;
  const themeColors =
    themeConfig && typeof themeConfig === "object"
      ? (themeConfig as { colors?: { accent?: unknown } }).colors
      : undefined;
  return (
    accentHexColor(themeColors?.accent) ||
    accentHexColor(design.colors?.accent) ||
    "#2563eb"
  );
}

/** Build an API-valid preset id from a display name; avoid collisions with existing ids. */
function uniqueCoverPresetId(name: string, existingIds: Set<string>): string {
  const base =
    name
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 48) || "cover-preset";
  const rooted = /^[a-z0-9]/.test(base) ? base : `cover-${base}`;
  if (!existingIds.has(rooted)) return rooted;
  for (let index = 2; index < 1000; index += 1) {
    const candidate = `${rooted.slice(0, 44)}-${index}`;
    if (!existingIds.has(candidate)) return candidate;
  }
  return `cover-${Date.now().toString(36)}`;
}
