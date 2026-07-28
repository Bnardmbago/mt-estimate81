"use client";

import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
  type KeyboardEvent as ReactKeyboardEvent,
  type PointerEvent as ReactPointerEvent,
} from "react";
import { useTranslations } from "next-intl";
import {
  keyboardMove,
  moveGeometry,
  normalizeGeometry,
  pointToPercent,
  resizeGeometry,
  rotateGeometry,
  snapGeometry,
  type CoverGeometry,
  type PercentPoint,
  type ResizeHandle,
  type SnapGuide,
} from "@/lib/cover-geometry";
import { type AccentShape } from "@/lib/cover-accent-shapes";
import { coverBackgroundImageStyle } from "@/lib/cover-background-style";
import { coverPageDimensions, coverPreviewWidthCss } from "@/lib/cover-preview-size";
import PresentationAccentShapeSvg from "./PresentationAccentShapeSvg";

export type CoverPage = {
  size: string;
  orientation: "portrait" | "landscape";
};

export type CoverAsset = {
  id?: string;
  role: "logo" | "background" | "decorative";
  storage_path?: string;
  filename?: string;
  x?: number;
  y?: number;
  zoom?: number;
  opacity?: number;
  rotation?: number;
  fit?: "cover" | "contain" | "fill";
  position?: string;
  geometry?: CoverGeometry;
};

export type CoverTextStyle = {
  font_family?: string;
  font_size_pt?: number;
  font_weight?: number;
  italic?: boolean;
  color?: string;
  text_align?: "left" | "center" | "right";
  line_height?: number;
  letter_spacing_em?: number;
  opacity?: number;
  background_color?: string;
  padding_mm?: number;
};

export type CoverField = {
  key: string;
  emphasis?: string | null;
  content?: {
    _i18n?: Partial<Record<"en" | "ja", { label?: string; default_text?: string }>>;
  };
  required?: boolean;
  auto_fill?: string;
  geometry?: CoverGeometry;
  style?: CoverTextStyle;
};

export type CoverDesign = {
  alignment?: "left" | "center" | "right";
  padding_mm?: number;
  accent?: { enabled?: boolean; width_mm?: number; opacity?: number };
  accent_shapes?: unknown;
  typography?: { title_pt?: number; metadata_pt?: number };
  colors?: { background?: string; title?: string; text?: string; accent?: string };
  assets?: CoverAsset[];
};

function color(value: string | undefined, fallback: string) {
  const normalized = String(value || "").replace("#", "");
  return /^[0-9a-f]{6}$/i.test(normalized) ? `#${normalized}` : fallback;
}

function localizedField(field: CoverField, locale: "en" | "ja") {
  const i18n = field.content?._i18n;
  return i18n?.[locale] || i18n?.[locale === "en" ? "ja" : "en"] || {};
}

type Props = {
  /** Owner id for asset GET URLs (draft id or template id). */
  assetOwnerId: string;
  assetOwnerKind?: "draft" | "template";
  enabled: boolean;
  page: CoverPage;
  design: CoverDesign;
  fields: CoverField[];
  shapes: AccentShape[];
  themeAccent: string;
  locale: "en" | "ja";
  previewUrls: Record<string, string>;
  selectedLayerId: string | null;
  snapEnabled: boolean;
  readOnly?: boolean;
  onSnapEnabledChange: (enabled: boolean) => void;
  onSelectLayer: (id: string | null) => void;
  onFieldGeometryChange: (key: string, geometry: CoverGeometry) => void;
  onAssetGeometryChange: (role: CoverAsset["role"], geometry: CoverGeometry) => void;
  onShapeGeometryChange: (id: string, geometry: AccentShape["geometry"]) => void;
  onDeleteAsset: (role: CoverAsset["role"]) => void;
  onDeleteShape: (id: string) => void;
  onLayerOrder: (
    action: "forward" | "backward" | "front" | "back",
    geometry: CoverGeometry,
  ) => void;
  onEnableCover: () => void;
};

type Layer = {
  id: string;
  kind: "field" | "asset" | "shape";
  fieldKey?: string;
  role?: CoverAsset["role"];
  shapeId?: string;
  locked?: boolean;
  geometry?: CoverGeometry;
};

type Interaction = {
  pointerId: number;
  layer: Layer;
  geometry: CoverGeometry;
  start: PercentPoint;
  handle?: ResizeHandle;
  rotate?: boolean;
  moved: boolean;
  latest?: CoverGeometry;
};

const RESIZE_HANDLES: ResizeHandle[] = [
  "north-west",
  "north",
  "north-east",
  "east",
  "south-east",
  "south",
  "south-west",
  "west",
];

export default function PresentationCoverPreview({
  assetOwnerId,
  assetOwnerKind = "draft",
  enabled,
  page,
  design,
  fields,
  shapes,
  themeAccent,
  locale,
  previewUrls,
  selectedLayerId,
  snapEnabled,
  readOnly = false,
  onSnapEnabledChange,
  onSelectLayer,
  onFieldGeometryChange,
  onAssetGeometryChange,
  onShapeGeometryChange,
  onDeleteAsset,
  onDeleteShape,
  onLayerOrder,
  onEnableCover,
}: Props) {
  const t = useTranslations("admin.presentation.cover");
  const dimensions = coverPageDimensions(page.size, page.orientation);
  const assets = design.assets || [];
  const background = assets.find((asset) => asset.role === "background");
  const foreground = assets.filter((asset) => asset.role !== "background");
  const padding = design.padding_mm ?? 24;
  const pageRef = useRef<HTMLDivElement>(null);
  const layerElements = useRef<Record<string, HTMLElement | null>>({});
  const interaction = useRef<Interaction | null>(null);
  const [measuredGeometry, setMeasuredGeometry] = useState<Record<string, CoverGeometry>>({});
  const [liveGeometry, setLiveGeometry] = useState<{ layerId: string; geometry: CoverGeometry } | null>(null);
  const [guides, setGuides] = useState<SnapGuide[]>([]);
  const visibleShapes = shapes.filter((shape) => shape.visible);
  const layers: Layer[] = [
    ...fields.map((field) => ({
      id: fieldLayerId(field.key),
      kind: "field" as const,
      fieldKey: field.key,
      geometry: field.geometry,
    })),
    ...foreground.map((asset) => ({
      id: `asset:${asset.role}`,
      kind: "asset" as const,
      role: asset.role,
      geometry: asset.geometry,
    })),
    ...visibleShapes.map((shape) => ({
      id: shapeLayerId(shape.id),
      kind: "shape" as const,
      shapeId: shape.id,
      locked: shape.locked,
      geometry: shape.geometry,
    })),
  ];
  const selectedLayer = layers.find((layer) => layer.id === selectedLayerId);
  const selectedGeometry = liveGeometry?.layerId === selectedLayerId
    ? liveGeometry.geometry
    : selectedLayer?.geometry ||
      (selectedLayerId ? measuredGeometry[selectedLayerId] : undefined);
  const hasExplicitTitle = fields.some((field) => field.emphasis === "title");
  const measurementSignature = JSON.stringify([
    page,
    fields.map(({ key, geometry, content, style }) => ({ key, geometry, content, style })),
    foreground.map(({ id, role, geometry, storage_path }) => ({ id, role, geometry, storage_path })),
  ]);

  useLayoutEffect(() => {
    setLiveGeometry(null);
    setGuides([]);
  }, [selectedLayerId]);

  useLayoutEffect(() => {
    const page = pageRef.current;
    if (!page) return;
    setMeasuredGeometry((current) => {
      let changed = false;
      const next = { ...current };
      layers.forEach((layer) => {
        if (layer.geometry) return;
        const element = layerElements.current[layer.id];
        if (!element) return;
        const geometry = geometryFromElement(element, page, layer.kind === "field" ? 4 : 3);
        if (!sameGeometry(current[layer.id], geometry)) {
          next[layer.id] = geometry;
          changed = true;
        }
      });
      return changed ? next : current;
    });
  }, [measurementSignature]);

  function updateLayerGeometry(layer: Layer, geometry: CoverGeometry, commit: boolean) {
    const normalized = normalizeGeometry(geometry);
    setLiveGeometry({ layerId: layer.id, geometry: normalized });
    if (!commit) return;
    if (layer.kind === "field" && layer.fieldKey !== undefined) {
      onFieldGeometryChange(layer.fieldKey, normalized);
    } else if (layer.kind === "shape" && layer.shapeId !== undefined) {
      onShapeGeometryChange(layer.shapeId, asAccentGeometry(normalized));
    } else if (layer.role) {
      onAssetGeometryChange(layer.role, normalized);
    }
  }

  function beginInteraction(
    event: ReactPointerEvent<HTMLElement>,
    layer: Layer,
    handle?: ResizeHandle,
    rotate = false,
  ) {
    if (readOnly || event.button !== 0) return;
    const pageElement = pageRef.current;
    const layerElement = layerElements.current[layer.id];
    if (!pageElement || !layerElement) return;
    // Locked shapes can be selected but never start pointer edits.
    if (layer.locked) {
      event.preventDefault();
      event.stopPropagation();
      onSelectLayer(layer.id);
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    // Capture on the page so move/up handlers keep receiving events even if
    // the hit-target re-renders during the drag.
    pageElement.setPointerCapture(event.pointerId);
    onSelectLayer(layer.id);
    const geometry = layer.geometry ||
      measuredGeometry[layer.id] ||
      geometryFromElement(layerElement, pageElement, layer.kind === "field" ? 4 : 3);
    const bounds = pageElement.getBoundingClientRect();
    interaction.current = {
      pointerId: event.pointerId,
      layer,
      geometry,
      start: pointToPercent({ x: event.clientX, y: event.clientY }, bounds),
      handle,
      rotate,
      moved: false,
      latest: geometry,
    };
    setLiveGeometry({ layerId: layer.id, geometry });
  }

  function handlePointerMove(event: ReactPointerEvent<HTMLDivElement>) {
    const active = interaction.current;
    const pageElement = pageRef.current;
    if (!active || active.pointerId !== event.pointerId || !pageElement) return;
    const point = pointToPercent(
      { x: event.clientX, y: event.clientY },
      pageElement.getBoundingClientRect(),
    );
    const delta = {
      x_pct: point.x_pct - active.start.x_pct,
      y_pct: point.y_pct - active.start.y_pct,
    };
    let next: CoverGeometry;
    if (active.rotate) {
      next = rotateGeometry(active.geometry, { x: event.clientX, y: event.clientY }, pageElement.getBoundingClientRect());
    } else if (active.handle) {
      const proportionalByDefault = active.layer.kind === "asset";
      next = resizeGeometry(active.geometry, active.handle, delta, {
        lockAspectRatio: proportionalByDefault ? !event.shiftKey : event.shiftKey,
        fromCenter: event.altKey,
      });
    } else {
      next = moveGeometry(active.geometry, delta);
    }
    if (snapEnabled && !active.handle && !active.rotate) {
      const snapped = snapGeometry(next, {
        peer_guides: peerGuides(layers, active.layer.id, measuredGeometry),
      });
      next = snapped.geometry;
      setGuides(snapped.guides);
    } else {
      setGuides([]);
    }
    active.moved = true;
    active.latest = next;
    // Preview only during drag — committing every move re-renders the design
    // tree and can drop pointer capture / stall accent-shape dragging.
    updateLayerGeometry(active.layer, next, false);
  }

  function endInteraction(event: ReactPointerEvent<HTMLDivElement>) {
    if (interaction.current?.pointerId !== event.pointerId) return;
    const active = interaction.current;
    interaction.current = null;
    if (active?.moved && active.latest) {
      updateLayerGeometry(active.layer, active.latest, true);
    }
    setLiveGeometry(null);
    setGuides([]);
  }

  function handleKeyDown(event: ReactKeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape") {
      onSelectLayer(null);
      return;
    }
    if (!selectedLayer || !selectedGeometry) return;
    if (selectedLayer.kind === "shape" && selectedLayer.locked) return;
    if (event.key === "Delete" || event.key === "Backspace") {
      event.preventDefault();
      if (selectedLayer.kind === "asset" && selectedLayer.role) {
        onDeleteAsset(selectedLayer.role);
        onSelectLayer(null);
      } else if (selectedLayer.kind === "shape" && selectedLayer.shapeId) {
        onDeleteShape(selectedLayer.shapeId);
        onSelectLayer(null);
      }
      return;
    }
    if (!event.key.startsWith("Arrow")) return;
    event.preventDefault();
    updateLayerGeometry(
      selectedLayer,
      keyboardMove(selectedGeometry, event.key as "ArrowUp" | "ArrowRight" | "ArrowDown" | "ArrowLeft", event.shiftKey),
      true,
    );
    setLiveGeometry(null);
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-slate-100 p-4 dark:border-slate-700 dark:bg-slate-950">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-semibold">{readOnly ? t("setPreview") : t("livePreview")}</h3>
          {!enabled ? (
            <>
              <span className="rounded-full bg-amber-100 px-2 py-1 text-[11px] font-medium text-amber-800 dark:bg-amber-950 dark:text-amber-200">
                {t("disabledBadge")}
              </span>
              {!readOnly ? (
                <button type="button" className="header-btn text-xs" onClick={onEnableCover}>
                  {t("enableCover")}
                </button>
              ) : null}
            </>
          ) : null}
        </div>
        <div className="flex items-center gap-3">
          {!readOnly ? (
            <label className="flex items-center gap-1.5 text-xs">
              <input type="checkbox" checked={snapEnabled} onChange={(event) => onSnapEnabledChange(event.target.checked)} />
              {t("snap")}
            </label>
          ) : null}
          <span className="text-xs text-slate-500">
            {page.size} · {t(page.orientation)}
          </span>
        </div>
      </div>
      {!readOnly && selectedLayer && selectedGeometry ? (
        <div className="mb-3 flex flex-wrap items-center gap-2 rounded border border-blue-200 bg-blue-50 p-2 text-xs dark:border-blue-800 dark:bg-blue-950">
          <span className="font-mono">
            X {formatPercent(selectedGeometry.x_pct)} · Y {formatPercent(selectedGeometry.y_pct)} · W {formatPercent(selectedGeometry.width_pct)} · H {formatPercent(selectedGeometry.height_pct ?? 1)}
            {selectedLayer.kind === "shape"
              ? ` · R ${Number((selectedGeometry.rotation_deg ?? 0).toFixed(1))}°`
              : ""}
          </span>
          <span className="ml-auto flex flex-wrap gap-1">
            <button type="button" className="header-btn text-xs" onClick={() => onLayerOrder("forward", selectedGeometry)}>{t("bringForward")}</button>
            <button type="button" className="header-btn text-xs" onClick={() => onLayerOrder("backward", selectedGeometry)}>{t("sendBackward")}</button>
            <button type="button" className="header-btn text-xs" onClick={() => onLayerOrder("front", selectedGeometry)}>{t("bringToFront")}</button>
            <button type="button" className="header-btn text-xs" onClick={() => onLayerOrder("back", selectedGeometry)}>{t("sendToBack")}</button>
          </span>
        </div>
      ) : null}
      <div className="presentation-cover-preview-frame">
        <div
          ref={pageRef}
          tabIndex={readOnly ? -1 : 0}
          aria-label={t("canvasLabel")}
          className="presentation-cover-preview-page"
          style={{
            width: coverPreviewWidthCss(dimensions),
            aspectRatio: `${dimensions[0]} / ${dimensions[1]}`,
            backgroundColor: color(design.colors?.background, "#ffffff"),
            color: color(design.colors?.text, "#334155"),
            textAlign: design.alignment || "left",
          }}
          onPointerDown={readOnly ? undefined : (event) => {
            if (event.target === event.currentTarget) onSelectLayer(null);
          }}
          onPointerMove={readOnly ? undefined : handlePointerMove}
          onPointerUp={readOnly ? undefined : endInteraction}
          onPointerCancel={readOnly ? undefined : endInteraction}
          onKeyDown={readOnly ? undefined : handleKeyDown}
        >
          {snapEnabled ? <div className="presentation-cover-preview-grid" /> : null}
          {background ? (
            <AssetImage
              asset={background}
              assetOwnerId={assetOwnerId}
              assetOwnerKind={assetOwnerKind}
              previewUrls={previewUrls}
              background
            />
          ) : null}
          {visibleShapes.length > 0 ? (
            <svg
              className="presentation-cover-preview-accent-art"
              viewBox={`0 0 ${dimensions[0]} ${dimensions[1]}`}
              preserveAspectRatio="none"
              aria-hidden="true"
            >
              {orderShapes(visibleShapes).map((shape) => (
                <PresentationAccentShapeSvg
                  key={shape.id}
                  shape={liveShapeGeometry(shape, selectedLayerId, liveGeometry)}
                  themeAccent={themeAccent}
                  page={{ width_mm: dimensions[0], height_mm: dimensions[1] }}
                />
              ))}
            </svg>
          ) : null}
          <div
            className="presentation-cover-preview-content"
            style={{ padding: `${Math.max(4, padding / 2)}%` }}
          >
            {fields.map((field, index) => {
              if (field.geometry) return null;
              const layer = layers[index];
              return (
                <div
                  key={field.key}
                  ref={(node) => { layerElements.current[layer.id] = node; }}
                  className={`presentation-cover-preview-auto-field ${selectedLayerId === layer.id ? "is-selected" : ""} ${index > 0 ? "mt-2" : ""}`}
                  style={fieldTextStyle(field, isTitleField(field, index, hasExplicitTitle), design)}
                  role="button"
                  tabIndex={0}
                  aria-pressed={selectedLayerId === layer.id}
                  onPointerDown={(event) => beginInteraction(event, layer)}
                  onKeyDown={(event) => selectLayerWithKeyboard(event, layer.id, onSelectLayer)}
                >
                  <FieldContent field={field} isTitle={isTitleField(field, index, hasExplicitTitle)} locale={locale} sampleTitle={t("sampleTitle")} />
                </div>
              );
            })}
          </div>
          {/* Shape hit targets after content so low z_index shapes remain draggable. */}
          {visibleShapes.map((shape) => {
            const layer = layers.find((candidate) => candidate.id === shapeLayerId(shape.id))!;
            const geometry =
              liveGeometry?.layerId === layer.id ? liveGeometry.geometry : shape.geometry;
            return (
              <div
                key={shape.id}
                ref={(node) => { layerElements.current[layer.id] = node; }}
                className={`presentation-cover-preview-layer presentation-cover-preview-shape-layer ${shape.locked ? "is-locked" : ""}`}
                style={{
                  ...geometryStyle(geometry),
                  transform: geometry.rotation_deg ? `rotate(${geometry.rotation_deg}deg)` : undefined,
                  transformOrigin: "center",
                }}
                role="button"
                tabIndex={0}
                aria-pressed={selectedLayerId === layer.id}
                aria-label={shape.name}
                onPointerDown={(event) => beginInteraction(event, layer)}
                onKeyDown={(event) => selectLayerWithKeyboard(event, layer.id, onSelectLayer)}
              />
            );
          })}
          {fields.map((field, index) => {
            if (!field.geometry) return null;
            const layer = layers[index];
            return (
              <div
                key={field.key}
                ref={(node) => { layerElements.current[layer.id] = node; }}
                className="presentation-cover-preview-layer presentation-cover-preview-text-layer"
                style={{ ...geometryStyle(field.geometry), ...fieldTextStyle(field, isTitleField(field, index, hasExplicitTitle), design) }}
                role="button"
                tabIndex={0}
                aria-pressed={selectedLayerId === layer.id}
                onPointerDown={(event) => beginInteraction(event, layer)}
                onKeyDown={(event) => selectLayerWithKeyboard(event, layer.id, onSelectLayer)}
              >
                <FieldContent field={field} isTitle={isTitleField(field, index, hasExplicitTitle)} locale={locale} sampleTitle={t("sampleTitle")} />
              </div>
            );
          })}
          {foreground.map((asset) => {
            const layer = layers.find((candidate) => candidate.id === `asset:${asset.role}`)!;
            return (
              <div
                key={`${asset.role}-${asset.id || asset.storage_path}`}
                ref={(node) => { layerElements.current[layer.id] = node; }}
                className={`presentation-cover-preview-layer presentation-cover-preview-asset-layer ${asset.geometry ? "" : "is-legacy"}`}
                style={asset.geometry ? geometryStyle(asset.geometry) : legacyAssetStyle(asset)}
                role="button"
                tabIndex={0}
                aria-pressed={selectedLayerId === layer.id}
                onPointerDown={(event) => beginInteraction(event, layer)}
                onKeyDown={(event) => selectLayerWithKeyboard(event, layer.id, onSelectLayer)}
              >
                <AssetImage
                  asset={asset}
                  assetOwnerId={assetOwnerId}
                  assetOwnerKind={assetOwnerKind}
                  previewUrls={previewUrls}
                />
              </div>
            );
          })}
          {guides.map((guide, index) => (
            <div
              key={`${guide.axis}-${guide.value_pct}-${index}`}
              className={`presentation-cover-preview-guide presentation-cover-preview-guide-${guide.axis}`}
              style={guide.axis === "x" ? { left: `${guide.value_pct}%` } : { top: `${guide.value_pct}%` }}
            />
          ))}
          {selectedLayer && selectedGeometry ? (
            <div
              className="presentation-cover-preview-selection"
              style={{
                ...geometryStyle(selectedGeometry),
                ...(selectedLayer.kind === "shape" && selectedGeometry.rotation_deg
                  ? {
                      transform: `rotate(${selectedGeometry.rotation_deg}deg)`,
                      transformOrigin: "center",
                    }
                  : {}),
              }}
            >
              {selectedLayer.locked ? null : (
                <>
                  {RESIZE_HANDLES.map((handle) => (
                    <button
                      key={handle}
                      type="button"
                      aria-label={t("resizeHandle", { handle })}
                      className={`presentation-cover-resize-handle handle-${handle}`}
                      onPointerDown={(event) => beginInteraction(event, selectedLayer, handle)}
                    />
                  ))}
                  {selectedLayer.kind === "shape" ? (
                    <button
                      type="button"
                      aria-label={t("accent.rotateHandle")}
                      className="presentation-cover-rotate-handle"
                      onPointerDown={(event) => beginInteraction(event, selectedLayer, undefined, true)}
                    />
                  ) : null}
                </>
              )}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function AssetImage({
  asset,
  assetOwnerId,
  assetOwnerKind = "draft",
  previewUrls,
  background = false,
}: {
  asset: CoverAsset;
  assetOwnerId: string;
  assetOwnerKind?: "draft" | "template";
  previewUrls: Record<string, string>;
  background?: boolean;
}) {
  const [remoteUrl, setRemoteUrl] = useState<string | null>(null);
  const assetPath =
    asset.id && assetOwnerId
      ? assetOwnerKind === "template"
        ? `/api/admin/presentation/templates/${encodeURIComponent(assetOwnerId)}/assets/${encodeURIComponent(asset.id)}`
        : `/api/admin/presentation/drafts/${encodeURIComponent(assetOwnerId)}/assets/${encodeURIComponent(asset.id)}`
      : null;
  const source = asset.id
    ? previewUrls[asset.id] || remoteUrl || undefined
    : undefined;

  useEffect(() => {
    if (!asset.id || previewUrls[asset.id] || !assetPath) {
      return;
    }
    let cancelled = false;
    let objectUrl: string | null = null;
    void fetch(assetPath, { credentials: "include" })
      .then(async (response) => {
        if (!response.ok) throw new Error("asset fetch failed");
        const blob = await response.blob();
        objectUrl = URL.createObjectURL(blob);
        if (!cancelled) setRemoteUrl(objectUrl);
      })
      .catch(() => {
        if (!cancelled) setRemoteUrl(assetPath);
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [asset.id, assetPath, previewUrls]);

  if (!source) return null;
  const x = asset.x ?? 50;
  const y = asset.y ?? 50;
  const zoom = asset.zoom ?? 1;
  const opacity = asset.opacity ?? 1;

  if (background) {
    return (
      <img
        src={source}
        alt=""
        className="presentation-cover-preview-background"
        style={coverBackgroundImageStyle({
          x,
          y,
          zoom,
          fit: asset.fit || "cover",
          opacity,
        })}
      />
    );
  }
  return (
    <img
      src={source}
      alt={asset.filename || ""}
      draggable={false}
      className={`presentation-cover-preview-asset presentation-cover-preview-${asset.role}`}
      style={{
        opacity,
        transform: `scale(${zoom}) rotate(${asset.rotation ?? 0}deg)`,
      }}
    />
  );
}

function FieldContent({ field, isTitle, locale, sampleTitle }: { field: CoverField; isTitle: boolean; locale: "en" | "ja"; sampleTitle: string }) {
  const value = localizedField(field, locale);
  if (isTitle) return <>{value.default_text || sampleTitle}</>;
  return (
    <>
      <span className="font-semibold">{value.label || field.key}</span>
      {value.default_text ? ` · ${value.default_text}` : ""}
    </>
  );
}

function fieldTextStyle(field: CoverField, isTitle: boolean, design: CoverDesign): CSSProperties {
  const style = field.style || {};
  const defaultSize = isTitle ? design.typography?.title_pt ?? 30 : design.typography?.metadata_pt ?? 10;
  const fallbackColor = isTitle ? design.colors?.title : design.colors?.text;
  return {
    fontFamily: style.font_family
      ? `${style.font_family}, "Noto Sans JP", "Hiragino Kaku Gothic ProN", "Yu Gothic", sans-serif`
      : `"Noto Sans JP", "Hiragino Kaku Gothic ProN", "Yu Gothic", sans-serif`,
    fontSize: `${Math.max(6, style.font_size_pt ?? defaultSize) * 0.55}px`,
    fontWeight: style.font_weight ?? (isTitle ? 700 : 400),
    fontStyle: style.italic ? "italic" : "normal",
    color: color(style.color, color(fallbackColor, isTitle ? "#1e3a5f" : "#334155")),
    textAlign: style.text_align || design.alignment || "left",
    lineHeight: style.line_height ?? 1.2,
    letterSpacing: `${style.letter_spacing_em ?? 0}em`,
    opacity: style.opacity ?? 1,
    backgroundColor: style.background_color ? color(style.background_color, "transparent") : undefined,
    padding: style.padding_mm ? `${style.padding_mm * 0.7}px` : undefined,
  };
}

function geometryStyle(geometry: CoverGeometry): CSSProperties {
  return {
    left: `${geometry.x_pct}%`,
    top: `${geometry.y_pct}%`,
    width: `${geometry.width_pct}%`,
    ...(geometry.height_pct === undefined ? {} : { height: `${geometry.height_pct}%` }),
    zIndex: geometry.z_index,
  };
}

function legacyAssetStyle(asset: CoverAsset): CSSProperties {
  return {
    left: `${asset.x ?? 50}%`,
    top: `${asset.y ?? 50}%`,
    transform: "translate(-50%, -50%)",
    zIndex: 3,
  };
}

function geometryFromElement(element: HTMLElement, page: HTMLElement, zIndex: number): CoverGeometry {
  const elementRect = element.getBoundingClientRect();
  const pageRect = page.getBoundingClientRect();
  return normalizeGeometry({
    x_pct: ((elementRect.left - pageRect.left) / pageRect.width) * 100,
    y_pct: ((elementRect.top - pageRect.top) / pageRect.height) * 100,
    width_pct: (elementRect.width / pageRect.width) * 100,
    height_pct: (elementRect.height / pageRect.height) * 100,
    z_index: zIndex,
  });
}

function sameGeometry(left: CoverGeometry | undefined, right: CoverGeometry) {
  return Boolean(
    left &&
    Math.abs(left.x_pct - right.x_pct) < 0.001 &&
    Math.abs(left.y_pct - right.y_pct) < 0.001 &&
    Math.abs(left.width_pct - right.width_pct) < 0.001 &&
    Math.abs((left.height_pct ?? 1) - (right.height_pct ?? 1)) < 0.001 &&
    left.z_index === right.z_index,
  );
}

function peerGuides(
  layers: Layer[],
  selectedId: string,
  measuredGeometry: Record<string, CoverGeometry>,
) {
  return layers.flatMap((layer) => {
    const geometry = layer.geometry || measuredGeometry[layer.id];
    if (layer.id === selectedId || !geometry) return [];
    const height = geometry.height_pct ?? 1;
    return [
      { axis: "x" as const, value_pct: geometry.x_pct },
      { axis: "x" as const, value_pct: geometry.x_pct + geometry.width_pct / 2 },
      { axis: "x" as const, value_pct: geometry.x_pct + geometry.width_pct },
      { axis: "y" as const, value_pct: geometry.y_pct },
      { axis: "y" as const, value_pct: geometry.y_pct + height / 2 },
      { axis: "y" as const, value_pct: geometry.y_pct + height },
    ];
  });
}

function fieldLayerId(key: string) {
  return `field:${encodeURIComponent(key)}`;
}

function shapeLayerId(id: string) {
  return `shape:${id}`;
}

function asAccentGeometry(geometry: CoverGeometry): AccentShape["geometry"] {
  return {
    x_pct: geometry.x_pct,
    y_pct: geometry.y_pct,
    width_pct: geometry.width_pct,
    height_pct: geometry.height_pct ?? 1,
    rotation_deg: geometry.rotation_deg ?? 0,
    z_index: geometry.z_index,
  };
}

function orderShapes(shapes: AccentShape[]): AccentShape[] {
  return shapes
    .map((shape, index) => ({ shape, index }))
    .sort((a, b) => a.shape.geometry.z_index - b.shape.geometry.z_index || a.index - b.index)
    .map((item) => item.shape);
}

function liveShapeGeometry(
  shape: AccentShape,
  selectedLayerId: string | null,
  liveGeometry: { layerId: string; geometry: CoverGeometry } | null,
): AccentShape {
  if (!liveGeometry || liveGeometry.layerId !== shapeLayerId(shape.id)) return shape;
  return { ...shape, geometry: asAccentGeometry(liveGeometry.geometry) };
}

function isTitleField(field: CoverField, index: number, hasExplicitTitle: boolean) {
  return field.emphasis === "title" || (!hasExplicitTitle && index === 0);
}

function selectLayerWithKeyboard(
  event: ReactKeyboardEvent<HTMLElement>,
  layerId: string,
  onSelectLayer: (id: string | null) => void,
) {
  if (event.key !== "Enter" && event.key !== " ") return;
  event.preventDefault();
  event.stopPropagation();
  onSelectLayer(layerId);
}

function formatPercent(value: number) {
  return `${Number(value.toFixed(2))}%`;
}
