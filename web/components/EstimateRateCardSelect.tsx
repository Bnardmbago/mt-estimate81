"use client";

import Link from "next/link";
import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import GeneratedRateCardReviewModal, {
  type GeneratedRateCardPreview,
  type GeneratedRateCardSettings,
} from "@/components/GeneratedRateCardReviewModal";
import AiGenerationProgress from "@/components/AiGenerationProgress";
import { apiJson } from "@/lib/api";

type RateCardOption = {
  id: string;
  name: string;
  is_active: boolean;
  development_approach: string;
};

export type RateCardSelectionMode = "existing" | "generate";

export type EstimateRateCardSelectHandle = {
  ensureRateCardForExtract: () => Promise<string | null>;
  getMode: () => RateCardSelectionMode;
  hasRateCard: () => boolean;
  canProceedWithExtract: () => boolean;
};

type EstimateRateCardSelectProps = {
  estimateId: string;
  projectName: string;
  selectedRateCardId: string | null;
  selectedRateCardName: string | null;
  readOnly?: boolean;
  onChange?: (rateCardId: string | null) => void;
  onSelectionStateChange?: (state: {
    mode: RateCardSelectionMode;
    hasCard: boolean;
  }) => void;
};

const selectClassName =
  "w-full min-w-[240px] rounded border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:bg-gray-50 disabled:text-gray-600";

function normalizePreviewSettings(raw: GeneratedRateCardSettings): GeneratedRateCardSettings {
  return {
    ...raw,
    roles: (raw.roles ?? []).map((role) => ({
      ...role,
      daily_rate_jpy: role.daily_rate_jpy ?? role.hourly_rate_jpy * 8,
    })),
    setup_cost_items: raw.setup_cost_items ?? [],
    monthly_rc_items: raw.monthly_rc_items ?? [],
  };
}

const EstimateRateCardSelect = forwardRef<
  EstimateRateCardSelectHandle,
  EstimateRateCardSelectProps
>(function EstimateRateCardSelect(
  {
    estimateId,
    projectName,
    selectedRateCardId,
    selectedRateCardName,
    readOnly = false,
    onChange,
    onSelectionStateChange,
  },
  ref,
) {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("review");
  const tPanel = useTranslations("review.rateCardPanel");
  const tRateCards = useTranslations("rateCards");
  const [options, setOptions] = useState<RateCardOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [value, setValue] = useState(selectedRateCardId ?? "");
  const [mode, setMode] = useState<RateCardSelectionMode>("existing");
  const [reviewOpen, setReviewOpen] = useState(false);
  const [preview, setPreview] = useState<GeneratedRateCardPreview | null>(null);
  const [saveForExtract, setSaveForExtract] = useState(false);
  const pendingExtractResolve = useRef<((id: string | null) => void) | null>(null);

  const loadOptions = useCallback(async () => {
    setLoadError(null);
    try {
      const list = await apiJson<RateCardOption[]>("/rate-cards/cards/options");
      setOptions(list);
      if (list.length === 0 && !selectedRateCardId) {
        setMode("generate");
      }
      return list;
    } catch {
      setLoadError(tPanel("loadOptionsError"));
      return [];
    } finally {
      setLoading(false);
    }
  }, [selectedRateCardId, tPanel]);

  useEffect(() => {
    setValue(selectedRateCardId ?? "");
  }, [selectedRateCardId]);

  useEffect(() => {
    void loadOptions();
  }, [loadOptions]);

  useEffect(() => {
    onSelectionStateChange?.({
      mode,
      hasCard: Boolean(selectedRateCardId || value),
    });
  }, [mode, onSelectionStateChange, selectedRateCardId, value]);

  function resolvePendingExtract(cardId: string | null) {
    pendingExtractResolve.current?.(cardId);
    pendingExtractResolve.current = null;
    setSaveForExtract(false);
    setGenerating(false);
  }

  async function handleSelectExisting(nextValue: string) {
    if (!nextValue) {
      setValue("");
      onChange?.(null);
      return;
    }

    setValue(nextValue);
    setSaving(true);
    setActionError(null);

    try {
      await apiJson(`/estimates/${estimateId}`, {
        method: "PATCH",
        body: JSON.stringify({ rate_card_id: nextValue }),
      });
      onChange?.(nextValue);
      router.refresh();
    } catch (saveError) {
      setValue(selectedRateCardId ?? "");
      setActionError(saveError instanceof Error ? saveError.message : t("rateCardSaveError"));
    } finally {
      setSaving(false);
    }
  }

  async function openGeneratePreview(forExtract: boolean): Promise<string | null> {
    setGenerating(true);
    setActionError(null);

    try {
      const result = await apiJson<GeneratedRateCardPreview>(
        `/estimates/${estimateId}/rate-card/generate`,
        { method: "POST" },
      );
      setPreview({
        ...result,
        name: result.name || projectName,
        settings: normalizePreviewSettings(result.settings),
      });
      setSaveForExtract(forExtract);
      setReviewOpen(true);

      if (!forExtract) {
        return null;
      }

      return new Promise<string | null>((resolve) => {
        pendingExtractResolve.current = resolve;
      });
    } catch (generateError) {
      setActionError(
        generateError instanceof Error ? generateError.message : tPanel("generateError"),
      );
      if (forExtract) {
        setGenerating(false);
      }
      return null;
    } finally {
      if (!forExtract) {
        setGenerating(false);
      }
    }
  }

  const ensureRateCardForExtract = useCallback(async (): Promise<string | null> => {
    const assignedId = selectedRateCardId ?? (value || null);
    if (assignedId) {
      if (!selectedRateCardId && value) {
        setSaving(true);
        setActionError(null);
        try {
          await apiJson(`/estimates/${estimateId}`, {
            method: "PATCH",
            body: JSON.stringify({ rate_card_id: value }),
          });
          onChange?.(value);
          router.refresh();
        } catch (saveError) {
          setActionError(
            saveError instanceof Error ? saveError.message : t("rateCardSaveError"),
          );
          return null;
        } finally {
          setSaving(false);
        }
      }
      return assignedId;
    }

    if (mode === "existing") {
      return null;
    }

    return openGeneratePreview(true);
  }, [estimateId, mode, onChange, router, selectedRateCardId, t, value]);

  async function handleSaveGenerated() {
    if (!preview || !preview.name.trim()) {
      return;
    }

    setSaving(true);
    setActionError(null);

    try {
      const updated = await apiJson<{ rate_card_id: string | null }>(
        `/estimates/${estimateId}/rate-card`,
        {
          method: "POST",
          body: JSON.stringify({
            name: preview.name.trim(),
            settings: preview.settings,
            activate: true,
          }),
        },
      );

      setReviewOpen(false);
      setPreview(null);

      if (updated.rate_card_id) {
        setValue(updated.rate_card_id);
        setMode("existing");
        onChange?.(updated.rate_card_id);
        await loadOptions();
        router.refresh();
        resolvePendingExtract(updated.rate_card_id);
        return;
      }

      resolvePendingExtract(null);
    } catch (saveError) {
      setActionError(saveError instanceof Error ? saveError.message : tPanel("saveGeneratedError"));
      if (saveForExtract) {
        resolvePendingExtract(null);
      }
    } finally {
      setSaving(false);
    }
  }

  function handleCloseModal() {
    if (saving) {
      return;
    }
    setReviewOpen(false);
    setPreview(null);
    resolvePendingExtract(null);
  }

  useImperativeHandle(
    ref,
    () => ({
      ensureRateCardForExtract,
      getMode: () => mode,
      hasRateCard: () => Boolean(selectedRateCardId || value),
      canProceedWithExtract: () =>
        Boolean(selectedRateCardId || value) || mode === "generate",
    }),
    [ensureRateCardForExtract, mode, selectedRateCardId, value],
  );

  if (readOnly) {
    return (
      <div className="mb-4">
        <span className="mb-1 block text-sm font-medium text-gray-700">{t("rateCardLabel")}</span>
        <p className="text-sm text-gray-800">{selectedRateCardName ?? "—"}</p>
      </div>
    );
  }

  return (
    <div className="mb-4 space-y-4 rounded-lg border border-gray-200 bg-gray-50 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-gray-900">{tPanel("title")}</h3>
          <p className="mt-1 text-sm text-gray-600">{tPanel("description")}</p>
        </div>
        <Link
          href={`/${locale}/rate-cards`}
          className="rounded border border-blue-200 bg-white px-3 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-50"
        >
          {tPanel("manageRateCards")}
        </Link>
      </div>

      <fieldset className="space-y-2">
        <legend className="sr-only">{tPanel("title")}</legend>
        <label className="flex cursor-pointer items-start gap-2 text-sm">
          <input
            type="radio"
            name="rate-card-mode"
            checked={mode === "existing"}
            onChange={() => setMode("existing")}
            disabled={saving || generating}
            className="mt-0.5"
          />
          <span>
            <span className="font-medium text-gray-900">{tPanel("modeSelectExisting")}</span>
            <span className="mt-0.5 block text-gray-600">{tPanel("existingHint")}</span>
          </span>
        </label>
        <label className="flex cursor-pointer items-start gap-2 text-sm">
          <input
            type="radio"
            name="rate-card-mode"
            checked={mode === "generate"}
            onChange={() => setMode("generate")}
            disabled={saving || generating}
            className="mt-0.5"
          />
          <span>
            <span className="font-medium text-gray-900">{tPanel("modeCreateNew")}</span>
            <span className="mt-0.5 block text-gray-600">{tPanel("generateOnExtractHint")}</span>
          </span>
        </label>
      </fieldset>

      {mode === "existing" && (
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-gray-700">{tPanel("existingLabel")}</span>
          {loading ? (
            <p className="text-sm text-gray-500">{t("rateCardLoading")}</p>
          ) : options.length === 0 ? (
            <p className="text-sm text-amber-700">{tPanel("noExistingCards")}</p>
          ) : (
            <select
              value={value}
              onChange={(event) => void handleSelectExisting(event.target.value)}
              disabled={saving || generating}
              className={selectClassName}
            >
              <option value="">{tPanel("selectPlaceholder")}</option>
              {options.map((option) => {
                const approachLabel = ["traditional", "ai_assisted", "hybrid", "low_code"].includes(
                  option.development_approach,
                )
                  ? tRateCards(`developmentApproachOptions.${option.development_approach}.label`)
                  : option.development_approach;
                return (
                  <option key={option.id} value={option.id}>
                    {option.name} — {approachLabel}
                    {option.is_active ? " *" : ""}
                  </option>
                );
              })}
            </select>
          )}
        </label>
      )}

      {mode === "generate" && !selectedRateCardId && (
        <p className="rounded-md border border-indigo-100 bg-indigo-50 px-3 py-2 text-sm text-indigo-900">
          {tPanel("generateReadyHint", { project: projectName })}
        </p>
      )}

      {(selectedRateCardId || value) && selectedRateCardName && (
        <p className="text-sm text-gray-700">
          {tPanel("selectedCard", { name: selectedRateCardName })}
        </p>
      )}

      {(saving || generating) && (
        <div className="mt-2">
          <AiGenerationProgress
            active
            compact
            title={generating ? tPanel("generating") : t("rateCardSaving")}
            message={generating ? undefined : t("rateCardSaving")}
          />
        </div>
      )}
      {loadError && (
        <p className="text-sm text-amber-700" role="status">
          {loadError}
        </p>
      )}
      {actionError && (
        <p className="text-sm text-red-600" role="alert">
          {actionError}
        </p>
      )}

      <GeneratedRateCardReviewModal
        open={reviewOpen}
        preview={preview}
        saving={saving}
        saveLabel={saveForExtract ? tPanel("reviewSaveAndExtract") : tPanel("reviewSave")}
        onClose={handleCloseModal}
        onChange={setPreview}
        onSave={() => void handleSaveGenerated()}
      />
    </div>
  );
});

export default EstimateRateCardSelect;
