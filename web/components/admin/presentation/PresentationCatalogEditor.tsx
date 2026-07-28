"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  createAdminPreset,
  deleteAdminPreset,
  deleteThemeLogo,
  setAdminPresetDefault,
  updateAdminPreset,
  uploadThemeLogo,
  type PresentationCatalogKind,
  type PresentationPresetDetail,
} from "@/lib/presentation";
import { clonePlainData } from "@/lib/clonePlainData";

export type PresentationEditorField = {
  path: string;
  label: string;
  type?: "text" | "number" | "color" | "checkbox" | "select";
  min?: number;
  max?: number;
  step?: number;
  options?: Array<{ value: string; label: string }>;
};

type Props = {
  kind: PresentationCatalogKind;
  presets: PresentationPresetDetail[];
  defaultConfig: Record<string, unknown>;
  fields: PresentationEditorField[];
  onChanged: () => Promise<void>;
  showLogo?: boolean;
};

function readPath(config: Record<string, unknown>, path: string): unknown {
  return path.split(".").reduce<unknown>((value, key) => {
    if (!value || typeof value !== "object" || Array.isArray(value)) return undefined;
    return (value as Record<string, unknown>)[key];
  }, config);
}

function writePath(
  config: Record<string, unknown>,
  path: string,
  value: string | number | boolean,
): Record<string, unknown> {
  const copy = clonePlainData(config);
  const keys = path.split(".");
  let cursor = copy;
  keys.slice(0, -1).forEach((key) => {
    const child = cursor[key];
    if (!child || typeof child !== "object" || Array.isArray(child)) cursor[key] = {};
    cursor = cursor[key] as Record<string, unknown>;
  });
  cursor[keys[keys.length - 1]] = value;
  return copy;
}

export default function PresentationCatalogEditor({
  kind,
  presets,
  defaultConfig,
  fields,
  onChanged,
  showLogo = false,
}: Props) {
  const t = useTranslations("admin.presentation");
  const [selectedId, setSelectedId] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [config, setConfig] = useState<Record<string, unknown>>(defaultConfig);
  const [slug, setSlug] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [advancedJson, setAdvancedJson] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selected = presets.find((row) => row.id === selectedId) || presets[0];

  useEffect(() => {
    if (!selected) {
      setSelectedId("");
      return;
    }
    setSelectedId(selected.id);
    setName(selected.name);
    setDescription(selected.description || "");
    setConfig(clonePlainData(selected.config || defaultConfig));
    setAdvancedJson(JSON.stringify(selected.config || defaultConfig, null, 2));
  }, [selected?.id, presets, defaultConfig]);

  function beginCreate() {
    setIsCreating(true);
    setSlug("");
    setName("");
    setDescription("");
    setConfig(clonePlainData(defaultConfig));
    setAdvancedJson(JSON.stringify(defaultConfig, null, 2));
    setError(null);
  }

  function applyAdvancedJson() {
    try {
      const parsed = JSON.parse(advancedJson) as Record<string, unknown>;
      setConfig(parsed);
      setError(null);
    } catch {
      setError(t("invalidConfigJson"));
    }
  }

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      await onChanged();
      setIsCreating(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveError"));
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    if (!name.trim() || (isCreating && !slug.trim())) {
      setError(t("createRequired"));
      return;
    }
    if (isCreating) {
      await run(async () => {
        const created = await createAdminPreset(kind, {
          id: slug.trim(),
          name: name.trim(),
          description: description.trim() || null,
          config,
          is_active: true,
        });
        setSelectedId(created.id);
      });
      return;
    }
    if (!selected) return;
    await run(() =>
      updateAdminPreset(kind, selected.id, {
        name: name.trim(),
        description: description.trim() || null,
        config,
      }),
    );
  }

  async function remove() {
    if (!selected || selected.is_default) {
      setError(t("cannotDeleteDefault"));
      return;
    }
    if (!window.confirm(t("deleteConfirm", { name: selected.name }))) return;
    await run(() => deleteAdminPreset(kind, selected.id));
  }

  const inputClass =
    "w-full rounded border border-slate-300 px-3 py-2 dark:border-slate-600 dark:bg-slate-950";

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <label className="min-w-64 flex-1 text-sm">
            <span className="mb-1 block">{t("selectPreset")}</span>
            <select
              className={inputClass}
              value={isCreating ? "" : selected?.id || ""}
              onChange={(event) => {
                setIsCreating(false);
                setSelectedId(event.target.value);
              }}
            >
              {presets.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}{row.is_default ? ` · ${t("defaultBadge")}` : ""}
                </option>
              ))}
            </select>
          </label>
          <button type="button" className="header-btn" onClick={beginCreate}>
            {t("newPreset")}
          </button>
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
        <div className="grid gap-3 md:grid-cols-2">
          {isCreating ? (
            <label className="text-sm">
              <span className="mb-1 block">{t("slugId")}</span>
              <input className={inputClass} value={slug} onChange={(e) => setSlug(e.target.value)} />
            </label>
          ) : null}
          <label className="text-sm">
            <span className="mb-1 block">{t("name")}</span>
            <input className={inputClass} value={name} onChange={(e) => setName(e.target.value)} />
          </label>
          <label className="text-sm md:col-span-2">
            <span className="mb-1 block">{t("descriptionLabel")}</span>
            <input
              className={inputClass}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </label>
          {fields.map((field) => {
            const value = readPath(config, field.path);
            if (field.type === "checkbox") {
              return (
                <label key={field.path} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={Boolean(value)}
                    onChange={(e) => setConfig(writePath(config, field.path, e.target.checked))}
                  />
                  {field.label}
                </label>
              );
            }
            if (field.type === "select") {
              return (
                <label key={field.path} className="text-sm">
                  <span className="mb-1 block">{field.label}</span>
                  <select
                    className={inputClass}
                    value={String(value ?? "")}
                    onChange={(e) => setConfig(writePath(config, field.path, e.target.value))}
                  >
                    {field.options?.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </label>
              );
            }
            return (
              <label key={field.path} className="text-sm">
                <span className="mb-1 block">{field.label}</span>
                <div className={field.type === "color" ? "flex gap-2" : undefined}>
                  {field.type === "color" ? (
                    <input
                      type="color"
                      className="h-10 w-12 rounded border border-slate-300"
                      value={`#${String(value || "000000").replace("#", "")}`}
                      onChange={(e) =>
                        setConfig(writePath(config, field.path, e.target.value.slice(1).toUpperCase()))
                      }
                    />
                  ) : null}
                  <input
                    className={inputClass}
                    type={field.type === "number" ? "number" : "text"}
                    min={field.min}
                    max={field.max}
                    step={field.step}
                    value={String(value ?? "")}
                    onChange={(e) =>
                      setConfig(
                        writePath(
                          config,
                          field.path,
                          field.type === "number" ? Number(e.target.value) : e.target.value,
                        ),
                      )
                    }
                  />
                </div>
              </label>
            );
          })}
        </div>

        {showLogo && selected && !isCreating ? (
          <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-slate-200 pt-4 dark:border-slate-700">
            <label className="header-btn cursor-pointer">
              {t("logoUpload")}
              <input
                type="file"
                accept="image/png,image/jpeg,image/svg+xml,image/webp"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) void run(() => uploadThemeLogo(selected.id, file));
                }}
              />
            </label>
            {selected.has_logo ? (
              <button
                type="button"
                className="header-btn"
                onClick={() => void run(() => deleteThemeLogo(selected.id))}
              >
                {t("logoReset")}
              </button>
            ) : null}
            <span className="text-xs text-slate-500">{t("logoHint")}</span>
          </div>
        ) : null}

        <details className="mt-4" open={advancedOpen} onToggle={(e) => setAdvancedOpen(e.currentTarget.open)}>
          <summary className="cursor-pointer text-sm font-medium">{t("advancedJson")}</summary>
          <textarea
            className="mt-2 h-48 w-full rounded border border-slate-300 px-3 py-2 font-mono text-xs dark:border-slate-600 dark:bg-slate-950"
            value={advancedJson}
            onChange={(e) => setAdvancedJson(e.target.value)}
          />
          <button type="button" className="header-btn mt-2 text-xs" onClick={applyAdvancedJson}>
            {t("applyJson")}
          </button>
        </details>

        {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
        <div className="mt-4 flex flex-wrap gap-2">
          <button type="button" className="header-btn" disabled={busy} onClick={() => void save()}>
            {busy ? t("saving") : t("saveEdit")}
          </button>
          {!isCreating && selected ? (
            <>
              {!selected.is_default ? (
                <button
                  type="button"
                  className="header-btn"
                  disabled={busy}
                  onClick={() => void run(() => setAdminPresetDefault(kind, selected.id))}
                >
                  {t("setDefault")}
                </button>
              ) : null}
              <button
                type="button"
                className="header-btn"
                disabled={busy}
                onClick={() =>
                  void run(() =>
                    updateAdminPreset(kind, selected.id, { is_active: !selected.is_active }),
                  )
                }
              >
                {selected.is_active ? t("deactivate") : t("activate")}
              </button>
              {!selected.is_default ? (
                <button
                  type="button"
                  className="header-btn text-red-700"
                  disabled={busy}
                  onClick={() => void remove()}
                >
                  {t("delete")}
                </button>
              ) : null}
            </>
          ) : null}
        </div>
      </section>
    </div>
  );
}
