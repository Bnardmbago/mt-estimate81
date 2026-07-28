"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  ACCENT_SHAPE_WARNING_THRESHOLD,
  type AccentEdge,
  type AccentShape,
  type AccentShapeType,
} from "@/lib/cover-accent-shapes";

type Props = {
  shapes: AccentShape[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onAddShape: (type: AccentShapeType) => void;
  onAddEdge: (edge: AccentEdge) => void;
  onRename: (id: string, name: string) => void;
  onToggleVisible: (id: string) => void;
  onToggleLock: (id: string) => void;
  onDuplicate: (id: string) => void;
  onDelete: (id: string) => void;
  onReorder: (id: string, direction: "up" | "down") => void;
};

const SHAPE_TYPES: AccentShapeType[] = [
  "rectangle",
  "line",
  "circle",
  "ellipse",
  "triangle",
  "polygon",
];
const EDGES: AccentEdge[] = ["left", "right", "top", "bottom"];

export default function PresentationAccentShapesPanel({
  shapes,
  selectedId,
  onSelect,
  onAddShape,
  onAddEdge,
  onRename,
  onToggleVisible,
  onToggleLock,
  onDuplicate,
  onDelete,
  onReorder,
}: Props) {
  const t = useTranslations("admin.presentation.cover");
  const [shapeType, setShapeType] = useState<AccentShapeType>("rectangle");
  const [edge, setEdge] = useState<AccentEdge>("left");
  const overLimit = shapes.length > ACCENT_SHAPE_WARNING_THRESHOLD;

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">{t("accent.title")}</h3>
        <span className="text-xs text-slate-500">{shapes.length}</span>
      </div>

      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        <div className="flex gap-2">
          <select
            aria-label={t("accent.shapeType")}
            className="min-w-0 flex-1 rounded border border-slate-300 px-2 py-2 text-sm dark:border-slate-600 dark:bg-slate-950"
            value={shapeType}
            onChange={(event) => setShapeType(event.target.value as AccentShapeType)}
          >
            {SHAPE_TYPES.map((type) => (
              <option key={type} value={type}>{t(`accent.shapeTypes.${type}`)}</option>
            ))}
          </select>
          <button type="button" className="header-btn text-xs" onClick={() => onAddShape(shapeType)}>
            {t("accent.addShape")}
          </button>
        </div>
        <div className="flex gap-2">
          <select
            aria-label={t("accent.edge")}
            className="min-w-0 flex-1 rounded border border-slate-300 px-2 py-2 text-sm dark:border-slate-600 dark:bg-slate-950"
            value={edge}
            onChange={(event) => setEdge(event.target.value as AccentEdge)}
          >
            {EDGES.map((value) => (
              <option key={value} value={value}>{t(`accent.edges.${value}`)}</option>
            ))}
          </select>
          <button type="button" className="header-btn text-xs" onClick={() => onAddEdge(edge)}>
            {t("accent.addEdge")}
          </button>
        </div>
      </div>

      {overLimit ? (
        <p role="status" className="mt-3 rounded border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
          {t("accent.countWarning", { max: ACCENT_SHAPE_WARNING_THRESHOLD })}
        </p>
      ) : null}

      {shapes.length === 0 ? (
        <p className="mt-3 text-sm text-slate-500">{t("accent.empty")}</p>
      ) : (
        <ul className="mt-3 space-y-1">
          {shapes.map((shape, index) => {
            const active = shape.id === selectedId;
            return (
              <li
                key={shape.id}
                className={`rounded border px-2 py-1.5 ${active ? "border-blue-400 bg-blue-50 dark:border-blue-600 dark:bg-blue-950" : "border-slate-200 dark:border-slate-700"}`}
              >
                <div className="flex items-center gap-2">
                  <div className="flex min-w-0 flex-1 items-center gap-1">
                    <button
                      type="button"
                      className="shrink-0 rounded px-1 text-[11px] text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                      aria-pressed={active}
                      title={t(`accent.shapeTypes.${shape.type}`)}
                      onClick={() => onSelect(shape.id)}
                    >
                      {t(`accent.shapeTypes.${shape.type}`)}
                    </button>
                    <input
                      className="min-w-0 flex-1 rounded border border-transparent bg-transparent px-1 py-0.5 text-sm hover:border-slate-300 focus:border-slate-400 focus:outline-none dark:hover:border-slate-600"
                      value={shape.name}
                      aria-label={t("accent.layerName")}
                      onFocus={() => onSelect(shape.id)}
                      onChange={(event) => onRename(shape.id, event.target.value)}
                    />
                  </div>
                  <IconButton
                    label={shape.visible ? t("accent.hide") : t("accent.show")}
                    active={!shape.visible}
                    onClick={() => onToggleVisible(shape.id)}
                  >
                    {shape.visible ? "◉" : "◌"}
                  </IconButton>
                  <IconButton
                    label={shape.locked ? t("accent.unlock") : t("accent.lock")}
                    active={shape.locked}
                    onClick={() => onToggleLock(shape.id)}
                  >
                    {shape.locked ? "🔒" : "🔓"}
                  </IconButton>
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-1">
                  <MiniButton label={t("accent.moveUp")} disabled={index === 0} onClick={() => onReorder(shape.id, "up")}>↑</MiniButton>
                  <MiniButton label={t("accent.moveDown")} disabled={index === shapes.length - 1} onClick={() => onReorder(shape.id, "down")}>↓</MiniButton>
                  <MiniButton label={t("accent.duplicate")} onClick={() => onDuplicate(shape.id)}>⧉</MiniButton>
                  <MiniButton
                    label={t("accent.delete")}
                    onClick={() => {
                      if (window.confirm(t("accent.deleteConfirm"))) onDelete(shape.id);
                    }}
                  >
                    ✕
                  </MiniButton>
                  {!shape.visible ? <Badge>{t("accent.hidden")}</Badge> : null}
                  {shape.locked ? <Badge>{t("accent.lockedBadge")}</Badge> : null}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

function IconButton({
  label,
  active,
  onClick,
  children,
}: {
  label: string;
  active?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      aria-pressed={active}
      className={`rounded px-1.5 py-0.5 text-sm ${active ? "text-blue-600" : "text-slate-500"} hover:bg-slate-100 dark:hover:bg-slate-800`}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

function MiniButton({
  label,
  disabled,
  onClick,
  children,
}: {
  label: string;
  disabled?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      disabled={disabled}
      className="rounded border border-slate-200 px-1.5 py-0.5 text-xs text-slate-600 hover:bg-slate-100 disabled:opacity-40 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
      onClick={onClick}
    >
      {children}
    </button>
  );
}

function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full bg-slate-200 px-2 py-0.5 text-[10px] font-medium text-slate-600 dark:bg-slate-700 dark:text-slate-300">
      {children}
    </span>
  );
}
