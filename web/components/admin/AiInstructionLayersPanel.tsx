"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { apiJson } from "@/lib/api";

type InstructionLocation =
  | "ai_spec_assistant"
  | "extraction"
  | "extraction_client_constraints"
  | "rate_card_generation"
  | "rate_card_section";

type InstructionLocale = "en" | "ja";

type InstructionParameters = {
  max_tokens?: number;
  temperature?: number;
  timeout_seconds?: number;
  max_document_chars?: number;
};

type InstructionLayerData = {
  system_prompt: string | null;
  default_prompt: string | null;
  user_prompt: string | null;
  negative_prompt: string | null;
  parameters: InstructionParameters | null;
  updated_at: string | null;
};

type InstructionLayerResponse = {
  location: InstructionLocation;
  locale: InstructionLocale;
  layer: InstructionLayerData;
  effective_prompt: InstructionLayerData;
  prompt_defaults: InstructionLayerData;
  preview: {
    system: string;
    user_prefix: string;
    parameters: Record<string, number>;
  };
  parameter_defaults: Record<string, number>;
  parameter_bounds: Record<string, [number, number]>;
};

const LOCATIONS: InstructionLocation[] = [
  "ai_spec_assistant",
  "extraction",
  "extraction_client_constraints",
  "rate_card_generation",
  "rate_card_section",
];

const LOCALES: InstructionLocale[] = ["en", "ja"];

const inputClassName =
  "w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

const textareaClassName = `${inputClassName} min-h-[6rem] font-mono text-xs`;

const numberInputClassName =
  "w-full max-w-xs rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

function tabButtonClass(isActive: boolean) {
  return isActive ? "header-btn header-btn-active" : "header-btn";
}

function parametersToForm(parameters: InstructionParameters | null): Record<string, string> {
  return {
    max_tokens: parameters?.max_tokens?.toString() ?? "",
    temperature: parameters?.temperature?.toString() ?? "",
    timeout_seconds: parameters?.timeout_seconds?.toString() ?? "",
    max_document_chars: parameters?.max_document_chars?.toString() ?? "",
  };
}

function promptFieldsFromLayer(layer: InstructionLayerData) {
  return {
    systemPrompt: layer.system_prompt ?? "",
    defaultPrompt: layer.default_prompt ?? "",
    userPrompt: layer.user_prompt ?? "",
    negativePrompt: layer.negative_prompt ?? "",
  };
}

export default function AiInstructionLayersPanel() {
  const t = useTranslations("admin.aiInstructionLayers");
  const [location, setLocation] = useState<InstructionLocation>("ai_spec_assistant");
  const [locale, setLocale] = useState<InstructionLocale>("en");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [data, setData] = useState<InstructionLayerResponse | null>(null);
  const [systemPrompt, setSystemPrompt] = useState("");
  const [defaultPrompt, setDefaultPrompt] = useState("");
  const [userPrompt, setUserPrompt] = useState("");
  const [negativePrompt, setNegativePrompt] = useState("");
  const [parameterFields, setParameterFields] = useState<Record<string, string>>({
    max_tokens: "",
    temperature: "",
    timeout_seconds: "",
    max_document_chars: "",
  });

  const loadLayer = useCallback(async () => {
    setLoading(true);
    setError(null);
    setSaved(false);
    try {
      const response = await apiJson<InstructionLayerResponse>(
        `/admin/ai-instruction-layers/${location}/${locale}`,
      );
      setData(response);
      const fields = promptFieldsFromLayer(response.effective_prompt);
      setSystemPrompt(fields.systemPrompt);
      setDefaultPrompt(fields.defaultPrompt);
      setUserPrompt(fields.userPrompt);
      setNegativePrompt(fields.negativePrompt);
      setParameterFields(parametersToForm(response.layer.parameters));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : t("loadError"));
    } finally {
      setLoading(false);
    }
  }, [location, locale, t]);

  useEffect(() => {
    void loadLayer();
  }, [loadLayer]);

  function buildParametersPayload(): InstructionParameters | null {
    const payload: InstructionParameters = {};
    const entries: Array<[keyof InstructionParameters, string]> = [
      ["max_tokens", parameterFields.max_tokens],
      ["temperature", parameterFields.temperature],
      ["timeout_seconds", parameterFields.timeout_seconds],
      ["max_document_chars", parameterFields.max_document_chars],
    ];

    for (const [key, value] of entries) {
      const trimmed = value.trim();
      if (!trimmed) {
        continue;
      }
      const parsed = Number(trimmed);
      if (!Number.isFinite(parsed)) {
        throw new Error(t("invalidParameters"));
      }
      payload[key] = parsed;
    }

    return Object.keys(payload).length > 0 ? payload : null;
  }

  async function handleSave(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setSaved(false);

    try {
      const parameters = buildParametersPayload();
      const response = await apiJson<InstructionLayerResponse>(
        `/admin/ai-instruction-layers/${location}/${locale}`,
        {
          method: "PATCH",
          body: JSON.stringify({
            system_prompt: systemPrompt,
            default_prompt: defaultPrompt,
            user_prompt: userPrompt,
            negative_prompt: negativePrompt,
            parameters,
          }),
        },
      );
      setData(response);
      const fields = promptFieldsFromLayer(response.effective_prompt);
      setSystemPrompt(fields.systemPrompt);
      setDefaultPrompt(fields.defaultPrompt);
      setUserPrompt(fields.userPrompt);
      setNegativePrompt(fields.negativePrompt);
      setParameterFields(parametersToForm(response.layer.parameters));
      setSaved(true);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : t("saveError"));
    } finally {
      setSaving(false);
    }
  }

  async function handleReset() {
    if (!window.confirm(t("resetConfirm"))) {
      return;
    }

    setResetting(true);
    setError(null);
    setSaved(false);

    try {
      const response = await apiJson<InstructionLayerResponse>(
        `/admin/ai-instruction-layers/${location}/${locale}`,
        { method: "DELETE" },
      );
      setData(response);
      const fields = promptFieldsFromLayer(response.effective_prompt);
      setSystemPrompt(fields.systemPrompt);
      setDefaultPrompt(fields.defaultPrompt);
      setUserPrompt(fields.userPrompt);
      setNegativePrompt(fields.negativePrompt);
      setParameterFields(parametersToForm(null));
      setSaved(true);
    } catch (resetError) {
      setError(resetError instanceof Error ? resetError.message : t("resetError"));
    } finally {
      setResetting(false);
    }
  }

  if (loading) {
    return <p className="text-sm text-gray-500">{t("loading")}</p>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">{t("title")}</h2>
        <p className="mt-1 text-sm text-gray-600">{t("description")}</p>
        <p className="mt-2 rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-900">
          {t("safetyNote")}
        </p>
      </div>

      <div className="space-y-3">
        <div>
          <p className="mb-2 text-sm font-medium text-gray-700">{t("locationLabel")}</p>
          <nav className="flex flex-wrap gap-2" aria-label={t("locationLabel")}>
            {LOCATIONS.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setLocation(item)}
                className={tabButtonClass(location === item)}
              >
                {t(`locations.${item}`)}
              </button>
            ))}
          </nav>
        </div>

        <div>
          <p className="mb-2 text-sm font-medium text-gray-700">{t("localeLabel")}</p>
          <div className="flex gap-2">
            {LOCALES.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setLocale(item)}
                className={tabButtonClass(locale === item)}
              >
                {item.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </div>

      <form onSubmit={handleSave} className="space-y-5">
        <div>
          <label htmlFor="system-prompt" className="mb-1 block text-sm font-medium">
            {t("systemPrompt")}
          </label>
          <p className="mb-2 text-xs text-gray-500">{t("systemPromptHint")}</p>
          <textarea
            id="system-prompt"
            value={systemPrompt}
            onChange={(event) => setSystemPrompt(event.target.value)}
            className={textareaClassName}
            placeholder={t("optionalPlaceholder")}
          />
        </div>

        <div>
          <label htmlFor="default-prompt" className="mb-1 block text-sm font-medium">
            {t("defaultPrompt")}
          </label>
          <p className="mb-2 text-xs text-gray-500">{t("defaultPromptHint")}</p>
          <textarea
            id="default-prompt"
            value={defaultPrompt}
            onChange={(event) => setDefaultPrompt(event.target.value)}
            className={textareaClassName}
            placeholder={t("optionalPlaceholder")}
          />
        </div>

        <div>
          <label htmlFor="user-prompt" className="mb-1 block text-sm font-medium">
            {t("userPrompt")}
          </label>
          <p className="mb-2 text-xs text-gray-500">{t(`userPromptHints.${location}`)}</p>
          <textarea
            id="user-prompt"
            value={userPrompt}
            onChange={(event) => setUserPrompt(event.target.value)}
            className={textareaClassName}
            placeholder={t("optionalPlaceholder")}
          />
        </div>

        <div>
          <label htmlFor="negative-prompt" className="mb-1 block text-sm font-medium">
            {t("negativePrompt")}
          </label>
          <p className="mb-2 text-xs text-gray-500">{t("negativePromptHint")}</p>
          <textarea
            id="negative-prompt"
            value={negativePrompt}
            onChange={(event) => setNegativePrompt(event.target.value)}
            className={textareaClassName}
            placeholder={t("optionalPlaceholder")}
          />
        </div>

        <fieldset className="space-y-3 rounded-lg border border-gray-200 p-4">
          <legend className="px-1 text-sm font-medium">{t("parametersTitle")}</legend>
          <p className="text-xs text-gray-500">{t("parametersHint")}</p>
          {(["max_tokens", "temperature", "timeout_seconds", "max_document_chars"] as const).map(
            (key) => {
              const bounds = data?.parameter_bounds[key];
              const defaultValue = data?.parameter_defaults[key];
              return (
                <div key={key}>
                  <label htmlFor={`param-${key}`} className="mb-1 block text-sm font-medium">
                    {t(`parameters.${key}`)}
                  </label>
                  <input
                    id={`param-${key}`}
                    type="number"
                    step={key === "temperature" ? "0.1" : "1"}
                    value={parameterFields[key]}
                    onChange={(event) =>
                      setParameterFields((current) => ({
                        ...current,
                        [key]: event.target.value,
                      }))
                    }
                    className={numberInputClassName}
                    placeholder={
                      defaultValue !== undefined ? String(defaultValue) : t("optionalPlaceholder")
                    }
                  />
                  {bounds ? (
                    <p className="mt-1 text-xs text-gray-500">
                      {t("parameterBounds", { min: bounds[0], max: bounds[1] })}
                    </p>
                  ) : null}
                </div>
              );
            },
          )}
        </fieldset>

        {data ? (
          <section className="rounded-lg border border-gray-200 bg-gray-50 p-4">
            <h3 className="text-sm font-semibold text-gray-900">{t("previewTitle")}</h3>
            <p className="mt-1 text-xs text-gray-500">{t("previewHint")}</p>
            <div className="mt-3 space-y-3">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                  {t("previewSystem")}
                </p>
                <pre className="mt-1 max-h-64 overflow-auto whitespace-pre-wrap rounded border border-gray-200 bg-white p-3 text-xs text-gray-800">
                  {data.preview.system}
                </pre>
              </div>
              {data.preview.user_prefix ? (
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                    {t("previewUserPrefix")}
                  </p>
                  <pre className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap rounded border border-gray-200 bg-white p-3 text-xs text-gray-800">
                    {data.preview.user_prefix}
                  </pre>
                </div>
              ) : null}
            </div>
          </section>
        ) : null}

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="submit"
            disabled={saving || resetting}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? t("saving") : t("save")}
          </button>
          <button
            type="button"
            onClick={() => void handleReset()}
            disabled={saving || resetting}
            className="rounded border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {resetting ? t("resetting") : t("reset")}
          </button>
          {saved ? <span className="text-sm text-green-600">{t("saved")}</span> : null}
        </div>

        {error ? (
          <p className="text-sm text-red-600" role="alert">
            {error}
          </p>
        ) : null}
      </form>
    </div>
  );
}
