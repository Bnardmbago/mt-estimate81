"use client";

import Link from "next/link";
import { notFound } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { apiFetch, apiJson } from "@/lib/api";
import { isKnownPhaseKey, KNOWN_PHASE_KEYS, moneySymbol, useDisplayLabels } from "@/lib/displayI18n";
import RateCardList from "@/components/rate-cards/RateCardList";
import RateCardSectionAiModal from "@/components/rate-cards/RateCardSectionAiModal";
import {
  appendSectionItems,
  type RateCardAiSection,
  type RateCardAiSuggestResponse,
} from "@/lib/rateCardAi";

const HOURS_PER_DAY = 8;

const DEVELOPMENT_APPROACH_OPTIONS = [
  "traditional",
  "ai_assisted",
  "hybrid",
  "low_code",
] as const;

type DevelopmentApproach = (typeof DEVELOPMENT_APPROACH_OPTIONS)[number];

function normalizePhaseKey(name: string): (typeof KNOWN_PHASE_KEYS)[number] | null {
  const normalized = name.trim().toLowerCase();
  return (KNOWN_PHASE_KEYS as readonly string[]).includes(normalized)
    ? (normalized as (typeof KNOWN_PHASE_KEYS)[number])
    : null;
}

const REGION_OPTIONS = ["japan", "philippines", "usa"] as const;
const CURRENCY_OPTIONS = ["JPY", "USD", "PHP"] as const;

type Region = (typeof REGION_OPTIONS)[number];
type Currency = (typeof CURRENCY_OPTIONS)[number];

type RoleRate = {
  name: string;
  hourly_rate: number;
  daily_rate: number;
  hourly_rate_jpy?: number;
  daily_rate_jpy?: number;
};

type PhasePercentage = {
  name: string;
  percentage: number;
};

type LineItem = {
  name: string;
  amount: number;
  amount_jpy?: number;
};

type RateCardSettings = {
  roles: RoleRate[];
  phases: PhasePercentage[];
  development_approach: DevelopmentApproach;
  contingency_rate: number;
  overhead_rate: number;
  monthly_rc_items: LineItem[];
  setup_cost_items: LineItem[];
  productivity: { hours_per_feature_default: number };
  tax_rate: number;
  region: Region;
  currency: Currency;
};

type ActiveRateCard = {
  id: string;
  name: string;
  version_number: number;
  version_id: string;
  version_label: string | null;
  settings: RateCardSettings;
  estimate_count: number;
  is_locked: boolean;
  duplicated_from_name: string | null;
};

type RateCardEstimateUsage = {
  estimate_id: string;
  project_name: string;
  client_name: string;
  status: string;
  updated_at: string;
};

type ApiErrorDetail = {
  error?: string;
  code?: string;
  details?: { estimate_count?: number };
};

async function readApiError(response: Response, fallback: string): Promise<ApiErrorDetail> {
  const payload = await response.json().catch(() => ({}));
  if (typeof payload.error === "string") {
    return {
      error: payload.error,
      code: payload.code,
      details: payload.details,
    };
  }
  const detail =
    typeof payload.detail === "object" && payload.detail !== null
      ? (payload.detail as ApiErrorDetail)
      : (payload as ApiErrorDetail);
  if (typeof detail.error === "string") {
    return detail;
  }
  return { error: fallback };
}

type RateCardSummary = {
  id: string;
  name: string;
  is_active: boolean;
  development_approach: string;
  version_count: number;
  latest_version_number: number;
  created_at: string;
  estimate_count: number;
  is_locked: boolean;
};

type RateCardEditorProps = {
  initialCardId?: string;
  showAllCardsList?: boolean;
};

const inputClassName =
  "w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

function defaultDailyRate(hourlyRate: number): number {
  return hourlyRate * HOURS_PER_DAY;
}

function normalizeRole(role: RoleRate): RoleRate {
  const hourly = Number(role.hourly_rate ?? role.hourly_rate_jpy) || 0;
  const daily =
    role.daily_rate !== undefined && role.daily_rate !== null
      ? Number(role.daily_rate)
      : role.daily_rate_jpy !== undefined && role.daily_rate_jpy !== null
        ? Number(role.daily_rate_jpy)
        : defaultDailyRate(hourly);
  return {
    ...role,
    hourly_rate: hourly,
    daily_rate: daily,
  };
}

function detectManualDailyRateIndexes(roles: RoleRate[]): Set<number> {
  return new Set(
    roles
      .map((role, index) =>
        role.daily_rate !== defaultDailyRate(role.hourly_rate) ? index : -1,
      )
      .filter((index) => index >= 0),
  );
}

function normalizeLineItem(item: LineItem): LineItem {
  return {
    ...item,
    amount: Number(item.amount ?? item.amount_jpy) || 0,
  };
}

function normalizeSettings(raw: RateCardSettings): RateCardSettings {
  const legacySetup = (raw as RateCardSettings & { setup_costs?: Record<string, number> })
    .setup_costs;
  let setupCostItems = raw.setup_cost_items ?? [];

  if (setupCostItems.length === 0 && legacySetup) {
    setupCostItems = [
      { name: "Infrastructure", amount: legacySetup.infrastructure_jpy ?? 0 },
      { name: "Tooling", amount: legacySetup.tooling_jpy ?? 0 },
      { name: "Third party", amount: legacySetup.third_party_jpy ?? 0 },
    ];
  }

  return {
    ...raw,
    region: REGION_OPTIONS.includes(raw.region as Region) ? raw.region : "philippines",
    currency: CURRENCY_OPTIONS.includes(raw.currency as Currency) ? raw.currency : "JPY",
    development_approach: DEVELOPMENT_APPROACH_OPTIONS.includes(
      raw.development_approach as DevelopmentApproach,
    )
      ? (raw.development_approach as DevelopmentApproach)
      : "traditional",
    roles: (raw.roles ?? []).map(normalizeRole),
    setup_cost_items: setupCostItems.map(normalizeLineItem),
    monthly_rc_items: (raw.monthly_rc_items ?? []).map(normalizeLineItem),
  };
}

export default function RateCardEditor({
  initialCardId,
  showAllCardsList = true,
}: RateCardEditorProps) {
  const t = useTranslations("rateCards");
  const locale = useLocale();
  const { formatJpy, formatMoney, translateRole, translateSetupItem } = useDisplayLabels();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleteCardConfirm, setDeleteCardConfirm] = useState(false);
  const [deletingCard, setDeletingCard] = useState(false);
  const [duplicateModalOpen, setDuplicateModalOpen] = useState(false);
  const [duplicateName, setDuplicateName] = useState("");
  const [duplicating, setDuplicating] = useState(false);
  const [creatingCard, setCreatingCard] = useState(false);
  const [creatingCardName, setCreatingCardName] = useState("");
  const [creatingCardApproach, setCreatingCardApproach] =
    useState<DevelopmentApproach>("traditional");
  const [creating, setCreating] = useState(false);
  const [switchingCard, setSwitchingCard] = useState(false);
  const [loadingUsage, setLoadingUsage] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [rateCardId, setRateCardId] = useState("");
  const [cards, setCards] = useState<RateCardSummary[]>([]);
  const [cardName, setCardName] = useState("");
  const [versionId, setVersionId] = useState("");
  const [isLocked, setIsLocked] = useState(false);
  const [estimateCount, setEstimateCount] = useState(0);
  const [usageEstimates, setUsageEstimates] = useState<RateCardEstimateUsage[]>([]);
  const [settings, setSettings] = useState<RateCardSettings | null>(null);
  const [dirty, setDirty] = useState(false);
  const [manualDailyRates, setManualDailyRates] = useState<Set<number>>(new Set());
  const [aiModalSection, setAiModalSection] = useState<RateCardAiSection | null>(null);
  const [fxLastUpdated, setFxLastUpdated] = useState<string | null>(null);
  const [applyingRegional, setApplyingRegional] = useState(false);

  const loadUsage = useCallback(async (cardId: string) => {
    setLoadingUsage(true);
    try {
      const list = await apiJson<RateCardEstimateUsage[]>(
        `/rate-cards/cards/${cardId}/estimates`,
      );
      setUsageEstimates(list);
    } catch {
      setUsageEstimates([]);
    } finally {
      setLoadingUsage(false);
    }
  }, []);

  const applyActiveCard = useCallback((data: ActiveRateCard) => {
    const normalized = normalizeSettings(data.settings);
    setRateCardId(data.id);
    setCardName(data.name);
    setVersionId(data.version_id);
    setIsLocked(data.is_locked);
    setEstimateCount(data.estimate_count);
    setSettings(normalized);
    setManualDailyRates(detectManualDailyRateIndexes(normalized.roles));
    setDeleteCardConfirm(false);
    setDuplicateModalOpen(false);
    setDirty(false);
    setSaved(false);
  }, []);

  const loadCards = useCallback(async () => {
    const list = await apiJson<RateCardSummary[]>("/rate-cards/cards");
    setCards(list);
    return list;
  }, []);

  useEffect(() => {
    async function load() {
      try {
        const cardList = await loadCards();

        if (initialCardId) {
          const response = await apiFetch(`/rate-cards/cards/${initialCardId}`);
          if (response.status === 403 || response.status === 404) {
            notFound();
            return;
          }
          if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(
              typeof error.error === "string" ? error.error : response.statusText,
            );
          }
          const data = (await response.json()) as ActiveRateCard;
          applyActiveCard(data);
          await loadUsage(data.id);
          return;
        }

        if (cardList.length === 0) {
          return;
        }

        const data = await apiJson<ActiveRateCard>("/rate-cards/active");
        applyActiveCard(data);
        await loadUsage(data.id);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : t("loadError"));
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [applyActiveCard, initialCardId, loadCards, loadUsage, t]);

  useEffect(() => {
    void apiJson<{ rates: Record<string, string | number | null> }>("/rate-cards/fx-rates")
      .then((data) => {
        const fetchedAt = data.rates.fetched_at;
        setFxLastUpdated(typeof fetchedAt === "string" ? fetchedAt : null);
      })
      .catch(() => {
        setFxLastUpdated(null);
      });
  }, []);

  async function switchCard(selectedCardId: string) {
    if (selectedCardId === rateCardId) {
      return;
    }

    setError(null);
    setSwitchingCard(true);

    try {
      const data = await apiJson<ActiveRateCard>(`/rate-cards/cards/${selectedCardId}/activate`, {
        method: "POST",
      });
      applyActiveCard(data);
      await loadCards();
      await loadUsage(data.id);
    } catch (switchError) {
      setError(switchError instanceof Error ? switchError.message : t("switchCardError"));
    } finally {
      setSwitchingCard(false);
    }
  }

  function openCreateCard() {
    setCreatingCardName(t("newCardDefaultName"));
    setCreatingCardApproach("traditional");
    setCreatingCard(true);
    setError(null);
  }

  async function handleCreateCard() {
    const name = creatingCardName.trim();
    if (!name) {
      return;
    }

    setCreating(true);
    setError(null);

    try {
      const data = await apiJson<ActiveRateCard>("/rate-cards/cards", {
        method: "POST",
        body: JSON.stringify({
          name,
          activate: true,
          development_approach: creatingCardApproach,
        }),
      });
      applyActiveCard(data);
      setCreatingCard(false);
      setCreatingCardName("");
      setCreatingCardApproach("traditional");
      await loadCards();
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : t("createCardError"));
    } finally {
      setCreating(false);
    }
  }

  function markDirty() {
    setDirty(true);
    setSaved(false);
  }

  function updateRegion(region: Region) {
    if (!settings) return;
    setSettings({ ...settings, region });
    markDirty();
  }

  function updateCurrency(currency: Currency) {
    if (!settings) return;
    setSettings({ ...settings, currency });
    markDirty();
  }

  function updateRole(index: number, field: "name" | "hourly_rate", value: string) {
    if (!settings) return;
    const roles = [...settings.roles];
    const role = { ...roles[index] };
    if (field === "name") {
      role.name = value;
    } else {
      const hourly = value === "" ? 0 : Number(value);
      role.hourly_rate = hourly;
      if (!manualDailyRates.has(index)) {
        role.daily_rate = defaultDailyRate(hourly);
      }
    }
    roles[index] = role;
    setSettings({ ...settings, roles });
    markDirty();
  }

  function updateRoleDailyRate(index: number, value: string) {
    if (!settings) return;
    const roles = [...settings.roles];
    const role = {
      ...roles[index],
      daily_rate: value === "" ? 0 : Number(value),
    };
    roles[index] = role;
    setSettings({ ...settings, roles });
    setManualDailyRates((current) => {
      const next = new Set(current);
      next.add(index);
      return next;
    });
    markDirty();
  }

  function resetRoleDailyRate(index: number) {
    if (!settings) return;
    const roles = [...settings.roles];
    const role = { ...roles[index] };
    role.daily_rate = defaultDailyRate(role.hourly_rate);
    roles[index] = role;
    setSettings({ ...settings, roles });
    setManualDailyRates((current) => {
      const next = new Set(current);
      next.delete(index);
      return next;
    });
    markDirty();
  }

  function isDailyRateCustom(index: number, role: RoleRate): boolean {
    return (
      manualDailyRates.has(index) ||
      role.daily_rate !== defaultDailyRate(role.hourly_rate)
    );
  }

  function remapManualDailyRates(removedIndex: number, current: Set<number>): Set<number> {
    const next = new Set<number>();
    for (const index of current) {
      if (index < removedIndex) {
        next.add(index);
      } else if (index > removedIndex) {
        next.add(index - 1);
      }
    }
    return next;
  }

  function addRole() {
    if (!settings) return;
    setSettings({
      ...settings,
      roles: [
        ...settings.roles,
        { name: "", hourly_rate: 0, daily_rate: 0 },
      ],
    });
    markDirty();
  }

  function removeRole(index: number) {
    if (!settings || settings.roles.length <= 1) return;
    setSettings({
      ...settings,
      roles: settings.roles.filter((_, roleIndex) => roleIndex !== index),
    });
    setManualDailyRates((current) => remapManualDailyRates(index, current));
    markDirty();
  }

  function addPhase() {
    if (!settings) return;
    setSettings({
      ...settings,
      phases: [...settings.phases, { name: "", percentage: 0 }],
    });
    markDirty();
  }

  function removePhase(index: number) {
    if (!settings || settings.phases.length <= 1) return;
    setSettings({
      ...settings,
      phases: settings.phases.filter((_, phaseIndex) => phaseIndex !== index),
    });
    markDirty();
  }

  function updatePhase(index: number, field: keyof PhasePercentage, value: string) {
    if (!settings) return;
    const phases = [...settings.phases];
    const phase = { ...phases[index] };
    if (field === "name") {
      phase.name = value;
    } else {
      phase.percentage = Number(value) / 100;
    }
    phases[index] = phase;
    setSettings({ ...settings, phases });
    markDirty();
  }

  function updateDevelopmentApproach(value: string) {
    if (!settings) return;
    if (!DEVELOPMENT_APPROACH_OPTIONS.includes(value as DevelopmentApproach)) {
      return;
    }
    setSettings({ ...settings, development_approach: value as DevelopmentApproach });
    markDirty();
  }

  function updateRate(field: "contingency_rate" | "overhead_rate" | "tax_rate", value: string) {
    if (!settings) return;
    setSettings({ ...settings, [field]: Number(value) / 100 });
    markDirty();
  }

  function updateLineItem(
    collection: "setup_cost_items" | "monthly_rc_items",
    index: number,
    field: keyof LineItem,
    value: string,
  ) {
    if (!settings) return;
    const items = [...settings[collection]];
    const item = { ...items[index] };
    if (field === "name") {
      item.name = value;
    } else {
      item.amount = Number(value);
    }
    items[index] = item;
    setSettings({ ...settings, [collection]: items });
    markDirty();
  }

  function addLineItem(collection: "setup_cost_items" | "monthly_rc_items") {
    if (!settings) return;
    setSettings({
      ...settings,
      [collection]: [...settings[collection], { name: "", amount: 0 }],
    });
    markDirty();
  }

  function removeLineItem(collection: "setup_cost_items" | "monthly_rc_items", index: number) {
    if (!settings) return;
    setSettings({
      ...settings,
      [collection]: settings[collection].filter((_, itemIndex) => itemIndex !== index),
    });
    markDirty();
  }

  function buildSettingsPayload(): RateCardSettings {
    if (!settings) {
      throw new Error("Missing settings");
    }

    return {
      ...settings,
      roles: settings.roles
        .filter((role) => role.name.trim())
        .map((role) => ({
          ...role,
          daily_rate: role.daily_rate ?? defaultDailyRate(role.hourly_rate),
        })),
      phases: settings.phases.filter((phase) => phase.name.trim()),
      setup_cost_items: settings.setup_cost_items.filter((item) => item.name.trim()),
      monthly_rc_items: settings.monthly_rc_items.filter((item) => item.name.trim()),
    };
  }

  async function handleApplyRegionalRates() {
    if (!settings || fieldsDisabled) return;

    const hasEditedRates = settings.roles.some((role) => role.hourly_rate > 0);
    if (hasEditedRates && !window.confirm(t("applyRegionalRatesConfirm"))) {
      return;
    }

    setApplyingRegional(true);
    setError(null);
    try {
      const response = await apiJson<{ settings: RateCardSettings }>(
        "/rate-cards/apply-regional-standard",
        {
          method: "POST",
          body: JSON.stringify({
            settings: buildSettingsPayload(),
            region: settings.region,
          }),
        },
      );
      const normalized = normalizeSettings(response.settings);
      setSettings(normalized);
      setManualDailyRates(detectManualDailyRateIndexes(normalized.roles));
      markDirty();
    } catch (applyError) {
      setError(
        applyError instanceof Error ? applyError.message : t("applyRegionalRatesError"),
      );
    } finally {
      setApplyingRegional(false);
    }
  }

  function openDuplicateModal() {
    setDuplicateName(t("duplicateDefaultName", { name: cardName }));
    setDuplicateModalOpen(true);
    setError(null);
  }

  async function handleDuplicateCard() {
    const name = duplicateName.trim();
    if (!name) {
      return;
    }

    setDuplicating(true);
    setError(null);

    try {
      const data = await apiJson<ActiveRateCard>(`/rate-cards/cards/${rateCardId}/duplicate`, {
        method: "POST",
        body: JSON.stringify({ name }),
      });
      applyActiveCard(data);
      setDuplicateModalOpen(false);
      setDuplicateName("");
      await loadCards();
      await loadUsage(data.id);
    } catch (duplicateError) {
      setError(duplicateError instanceof Error ? duplicateError.message : t("duplicateError"));
    } finally {
      setDuplicating(false);
    }
  }

  async function handleSaveCard() {
    if (!settings) return;
    setSaving(true);
    setError(null);

    try {
      const response = await apiFetch(`/rate-cards/cards/${rateCardId}`, {
        method: "PUT",
        body: JSON.stringify({
          name: cardName.trim(),
          settings: buildSettingsPayload(),
        }),
      });

      if (!response.ok) {
        const detail = await readApiError(response, t("saveError"));
        if (detail.code === "RATE_CARD_LOCKED") {
          throw new Error(t("lockedSaveError"));
        }
        throw new Error(detail.error ?? t("saveError"));
      }

      const data = (await response.json()) as ActiveRateCard;
      applyActiveCard(data);
      setSaved(true);
      await loadCards();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : t("saveError"));
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteCard() {
    setDeletingCard(true);
    setError(null);

    try {
      const response = await apiFetch(`/rate-cards/cards/${rateCardId}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        const detail = await readApiError(response, t("deleteCardError"));
        if (detail.code === "RATE_CARD_IN_USE") {
          throw new Error(t("deleteCardInUse"));
        }
        throw new Error(detail.error ?? t("deleteCardError"));
      }

      setDeleteCardConfirm(false);
      const cardList = await loadCards();
      if (cardList.length === 0) {
        setSettings(null);
        setRateCardId("");
        return;
      }

      const active = await apiJson<ActiveRateCard>("/rate-cards/active");
      applyActiveCard(active);
      await loadUsage(active.id);
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : t("deleteCardError"));
    } finally {
      setDeletingCard(false);
    }
  }

  const setupTotal = useMemo(
    () => settings?.setup_cost_items.reduce((sum, item) => sum + item.amount, 0) ?? 0,
    [settings],
  );
  const monthlyRcSubtotal = useMemo(
    () => settings?.monthly_rc_items.reduce((sum, item) => sum + item.amount, 0) ?? 0,
    [settings],
  );
  function handleApplyAiSuggestion(response: RateCardAiSuggestResponse) {
    if (!settings) {
      return;
    }
    const merged = appendSectionItems(settings, response);
    const normalized = normalizeSettings({
      ...settings,
      roles: merged.roles,
      phases: merged.phases,
      setup_cost_items: merged.setup_cost_items,
      monthly_rc_items: merged.monthly_rc_items,
    });
    setSettings(normalized);
    setManualDailyRates(detectManualDailyRateIndexes(normalized.roles));
    markDirty();
  }

  function renderSectionActions(section: RateCardAiSection, onAdd: () => void) {
    if (isLocked) {
      return null;
    }

    return (
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => setAiModalSection(section)}
          className="text-sm font-medium text-indigo-600 hover:text-indigo-800"
        >
          {t("ai.suggest")}
        </button>
        <button type="button" onClick={onAdd} className="text-sm text-blue-600 hover:text-blue-800">
          {t("addItem")}
        </button>
      </div>
    );
  }

  function renderDevelopmentApproachField(options?: { createMode?: boolean; disabled?: boolean }) {
    const createMode = options?.createMode ?? false;
    const approach = createMode ? creatingCardApproach : settings?.development_approach ?? "traditional";
    const disabled =
      options?.disabled ??
      (createMode
        ? creating
        : isLocked || saving || switchingCard || deletingCard || creating || duplicating);

    return (
      <label className="block text-sm">
        <span className="mb-1 block font-medium text-gray-700">
          {t("developmentApproach")}
          <span className="ml-1 text-red-600" aria-hidden="true">
            *
          </span>
        </span>
        <select
          value={approach}
          onChange={(event) =>
            createMode
              ? setCreatingCardApproach(event.target.value as DevelopmentApproach)
              : updateDevelopmentApproach(event.target.value)
          }
          disabled={disabled}
          required
          className={`${inputClassName} max-w-md disabled:bg-gray-50 disabled:text-gray-600`}
        >
          {DEVELOPMENT_APPROACH_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {t(`developmentApproachOptions.${option}.label`)}
            </option>
          ))}
        </select>
        <p className="mt-1 max-w-2xl text-xs text-gray-500">
          {t(`developmentApproachOptions.${approach}.description`)}
        </p>
        {!createMode && (
          <p className="mt-1 max-w-2xl text-xs text-gray-400">{t("developmentApproachHint")}</p>
        )}
      </label>
    );
  }

  if (loading && !settings) {
    return (
      <>
        <p className="text-sm text-gray-500">{t("loading")}</p>
        {showAllCardsList && (
          <RateCardList cards={cards} loading={loading} currentCardId={rateCardId || undefined} />
        )}
      </>
    );
  }

  if (!settings) {
    return (
      <div className="space-y-4">
        {error && (
          <p className="text-sm text-red-600" role="alert">
            {error}
          </p>
        )}
        <p className="text-sm text-gray-600">{t("noCards")}</p>
        {creatingCard ? (
          <div className="flex flex-wrap items-end gap-2">
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-gray-700">{t("cardName")}</span>
              <input
                type="text"
                value={creatingCardName}
                onChange={(event) => setCreatingCardName(event.target.value)}
                className={`${inputClassName} max-w-md`}
              />
            </label>
            {renderDevelopmentApproachField({ createMode: true })}
            <button
              type="button"
              onClick={() => void handleCreateCard()}
              disabled={creating || !creatingCardName.trim()}
              className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {creating ? t("creatingCard") : t("createCardConfirm")}
            </button>
            <button
              type="button"
              onClick={() => setCreatingCard(false)}
              disabled={creating}
              className="rounded border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50 disabled:opacity-50"
            >
              {t("createCardCancel")}
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={openCreateCard}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            {t("createCard")}
          </button>
        )}
        {showAllCardsList && (
          <RateCardList cards={cards} loading={false} currentCardId={rateCardId || undefined} />
        )}
      </div>
    );
  }

  const phaseSum = settings.phases.reduce((sum, phase) => sum + phase.percentage, 0);
  const canSaveSettings = Math.abs(phaseSum - 1) <= 0.001;
  const currencySymbol = moneySymbol(settings.currency);
  const fxUpdatedLabel = fxLastUpdated
    ? t("fxLastUpdated", {
        date: new Date(fxLastUpdated).toLocaleString(
          locale === "ja" ? "ja-JP" : "en-US",
          { dateStyle: "medium", timeStyle: "short" },
        ),
      })
    : t("fxLastUpdatedUnknown");
  const canSaveCard =
    canSaveSettings && dirty && !saving && !deletingCard && !switchingCard && !creating && !isLocked;
  const canDeleteCard = cards.length > 1 && !deletingCard && !creating && !switchingCard && !saving;
  const fieldsDisabled = isLocked || saving || switchingCard || deletingCard || creating || duplicating;

  function formatUsageDate(value: string): string {
    return new Date(value).toLocaleDateString(locale, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  return (
    <div className="space-y-8">
      {error && (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      <section className="rounded-lg border border-gray-200 bg-gray-50 p-4">
        {!showAllCardsList && (
          <div className="mb-4 space-y-3">
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-gray-700">{t("cardName")}</span>
              <input
                type="text"
                value={cardName}
                onChange={(event) => {
                  setCardName(event.target.value);
                  markDirty();
                }}
                disabled={fieldsDisabled}
                className={`${inputClassName} max-w-md disabled:bg-gray-50 disabled:text-gray-600`}
              />
            </label>
            {renderDevelopmentApproachField()}
            {dirty && (
              <p className="text-sm text-amber-600">{t("unsavedChanges")}</p>
            )}
            {!canSaveSettings && (
              <p className="text-sm text-amber-600">
                {t("phaseSumWarning", { percent: Math.round(phaseSum * 100) })}
              </p>
            )}
          </div>
        )}
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:flex-wrap">
            {showAllCardsList && cards.length > 0 && (
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-gray-700">{t("selectCard")}</span>
                <select
                  value={rateCardId}
                  onChange={(event) => void switchCard(event.target.value)}
                  disabled={switchingCard || creating || deletingCard || saving}
                  className={`${inputClassName} min-w-[12rem]`}
                >
                  {cards.map((card) => (
                    <option key={card.id} value={card.id}>
                      {card.name}
                      {card.is_active ? ` (${t("activeCard")})` : ""}
                      {card.estimate_count > 0
                        ? ` (${t("estimateCountBadge", { count: card.estimate_count })})`
                        : ""}
                    </option>
                  ))}
                </select>
              </label>
            )}

            {creatingCard ? (
              <div className="flex flex-wrap items-end gap-2">
                <label className="block text-sm">
                  <span className="mb-1 block font-medium text-gray-700">{t("newCardName")}</span>
                  <input
                    type="text"
                    value={creatingCardName}
                    onChange={(event) => setCreatingCardName(event.target.value)}
                    className={`${inputClassName} min-w-[12rem]`}
                  />
                </label>
                {renderDevelopmentApproachField({ createMode: true })}
                <button
                  type="button"
                  onClick={() => void handleCreateCard()}
                  disabled={creating || !creatingCardName.trim()}
                  className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {creating ? t("creatingCard") : t("createCardConfirm")}
                </button>
                <button
                  type="button"
                  onClick={() => setCreatingCard(false)}
                  disabled={creating}
                  className="rounded border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50 disabled:opacity-50"
                >
                  {t("createCardCancel")}
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={openCreateCard}
                disabled={switchingCard || deletingCard || saving}
                className="rounded border border-blue-600 px-4 py-2 text-sm font-medium text-blue-600 hover:bg-blue-50 disabled:opacity-50"
              >
                {t("createCard")}
              </button>
            )}

            {deleteCardConfirm ? (
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm text-gray-600">
                  {t("deleteCardConfirm", { name: cardName })}
                </span>
                <button
                  type="button"
                  onClick={() => void handleDeleteCard()}
                  disabled={!canDeleteCard}
                  className="rounded bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
                >
                  {deletingCard ? t("deletingCard") : t("deleteCardConfirmYes")}
                </button>
                <button
                  type="button"
                  onClick={() => setDeleteCardConfirm(false)}
                  disabled={deletingCard}
                  className="rounded border border-gray-300 px-3 py-2 text-sm hover:bg-gray-50 disabled:opacity-50"
                >
                  {t("deleteCardConfirmNo")}
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setDeleteCardConfirm(true)}
                disabled={!canDeleteCard}
                className="rounded border border-red-300 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
              >
                {t("deleteCard")}
              </button>
            )}
          </div>

          <div className="flex flex-col items-start gap-1 sm:items-end">
            {saved && !dirty && !isLocked && (
              <span className="text-sm text-green-600">{t("saved")}</span>
            )}
            {isLocked ? (
              <button
                type="button"
                onClick={openDuplicateModal}
                disabled={duplicating || switchingCard}
                className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {t("duplicateCard")}
              </button>
            ) : (
              <button
                type="button"
                onClick={() => void handleSaveCard()}
                disabled={!canSaveCard}
                className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? t("saving") : t("saveCard")}
              </button>
            )}
            {cards.length <= 1 && (
              <p className="text-xs text-gray-400">{t("deleteLastCardHint")}</p>
            )}
          </div>
        </div>
      </section>

      {isLocked && (
        <div
          className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
          role="status"
        >
          {t("lockedBanner", { count: estimateCount })}
        </div>
      )}

      <section className="rounded-lg border border-gray-200 bg-white p-4">
        <h3 className="mb-3 text-sm font-semibold text-gray-800">{t("usageTitle")}</h3>
        {loadingUsage ? (
          <p className="text-sm text-gray-500">{t("usageLoading")}</p>
        ) : usageEstimates.length === 0 ? (
          <p className="text-sm text-gray-500">{t("usageEmpty")}</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-gray-700">
                    {t("usageProject")}
                  </th>
                  <th className="px-3 py-2 text-left font-medium text-gray-700">
                    {t("usageClient")}
                  </th>
                  <th className="px-3 py-2 text-left font-medium text-gray-700">
                    {t("usageStatus")}
                  </th>
                  <th className="px-3 py-2 text-left font-medium text-gray-700">
                    {t("usageUpdated")}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {usageEstimates.map((estimate) => (
                  <tr key={estimate.estimate_id}>
                    <td className="px-3 py-2">
                      <Link
                        href={`/${locale}/estimates/${estimate.estimate_id}`}
                        className="text-blue-600 hover:text-blue-800 hover:underline"
                      >
                        {estimate.project_name}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-gray-700">{estimate.client_name}</td>
                    <td className="px-3 py-2 text-gray-700">{estimate.status}</td>
                    <td className="px-3 py-2 text-gray-700">
                      {formatUsageDate(estimate.updated_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {duplicateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div
            className="w-full max-w-md rounded-lg bg-white p-6 shadow-lg"
            role="dialog"
            aria-labelledby="duplicate-modal-title"
          >
            <h3 id="duplicate-modal-title" className="text-lg font-semibold text-gray-900">
              {t("duplicateModalTitle")}
            </h3>
            <p className="mt-2 text-sm text-gray-600">{t("duplicateModalDescription")}</p>
            <div className="mt-4 space-y-3">
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-gray-700">
                  {t("duplicateOriginalName")}
                </span>
                <input
                  type="text"
                  value={cardName}
                  readOnly
                  className={`${inputClassName} bg-gray-50 text-gray-600`}
                />
              </label>
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-gray-700">
                  {t("duplicateNewName")}
                </span>
                <input
                  type="text"
                  value={duplicateName}
                  onChange={(event) => setDuplicateName(event.target.value)}
                  className={inputClassName}
                  autoFocus
                />
              </label>
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setDuplicateModalOpen(false)}
                disabled={duplicating}
                className="rounded border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50 disabled:opacity-50"
              >
                {t("duplicateCancel")}
              </button>
              <button
                type="button"
                onClick={() => void handleDuplicateCard()}
                disabled={duplicating || !duplicateName.trim()}
                className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {duplicating ? t("duplicating") : t("duplicateConfirm")}
              </button>
            </div>
          </div>
        </div>
      )}

      {showAllCardsList && (
        <div className="space-y-3">
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-gray-700">{t("cardName")}</span>
            <input
              type="text"
              value={cardName}
              onChange={(event) => {
                setCardName(event.target.value);
                markDirty();
              }}
              disabled={fieldsDisabled}
              className={`${inputClassName} max-w-md disabled:bg-gray-50 disabled:text-gray-600`}
            />
          </label>
          {renderDevelopmentApproachField()}
          {dirty && (
            <p className="text-sm text-amber-600">{t("unsavedChanges")}</p>
          )}
          {!canSaveSettings && (
            <p className="text-sm text-amber-600">
              {t("phaseSumWarning", { percent: Math.round(phaseSum * 100) })}
            </p>
          )}
        </div>
      )}

      <section className="rounded-lg border border-gray-200 bg-gray-50 p-4">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-gray-700">{t("regionLabel")}</span>
            <select
              value={settings.region}
              onChange={(event) => updateRegion(event.target.value as Region)}
              disabled={fieldsDisabled}
              className={`${inputClassName} disabled:bg-gray-100 disabled:text-gray-600`}
            >
              <option value="japan">{t("regionJapan")}</option>
              <option value="philippines">{t("regionPhilippines")}</option>
              <option value="usa">{t("regionUsa")}</option>
            </select>
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-gray-700">{t("currencyLabel")}</span>
            <select
              value={settings.currency}
              onChange={(event) => updateCurrency(event.target.value as Currency)}
              disabled={fieldsDisabled}
              className={`${inputClassName} disabled:bg-gray-100 disabled:text-gray-600`}
            >
              <option value="JPY">{t("currencyJPY")}</option>
              <option value="USD">{t("currencyUSD")}</option>
              <option value="PHP">{t("currencyPHP")}</option>
            </select>
          </label>
          <div className="flex flex-col justify-end gap-2">
            <button
              type="button"
              onClick={() => void handleApplyRegionalRates()}
              disabled={fieldsDisabled || applyingRegional}
              className="rounded border border-blue-600 px-4 py-2 text-sm font-medium text-blue-600 hover:bg-blue-50 disabled:opacity-50"
            >
              {applyingRegional ? t("applyingRegionalRates") : t("applyRegionalRates")}
            </button>
            <p className="text-xs text-gray-500">{fxUpdatedLabel}</p>
          </div>
        </div>
      </section>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="font-medium">{t("roles")}</h3>
          {renderSectionActions("roles", addRole)}
        </div>
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left font-medium text-gray-700">{t("roleName")}</th>
                <th className="px-3 py-2 text-left font-medium text-gray-700">
                  {t("hourlyRate", { symbol: currencySymbol })}
                </th>
                <th className="px-3 py-2 text-left font-medium text-gray-700">
                  {t("dailyRate", { symbol: currencySymbol })}
                </th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {settings.roles.map((role, index) => (
                <tr key={`${role.name}-${index}`}>
                  <td className="px-3 py-2">
                    <input
                      type="text"
                      value={role.name}
                      onChange={(event) => updateRole(index, "name", event.target.value)}
                      disabled={fieldsDisabled}
                      placeholder={translateRole(role.name)}
                      className={`${inputClassName} disabled:bg-gray-50 disabled:text-gray-600`}
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="number"
                      value={role.hourly_rate}
                      onChange={(event) =>
                        updateRole(index, "hourly_rate", event.target.value)
                      }
                      disabled={fieldsDisabled}
                      className={`${inputClassName} disabled:bg-gray-50 disabled:text-gray-600`}
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="number"
                      min="0"
                      value={role.daily_rate}
                      onChange={(event) => updateRoleDailyRate(index, event.target.value)}
                      disabled={fieldsDisabled}
                      className={`${inputClassName} disabled:bg-gray-50 disabled:text-gray-600`}
                    />
                    <div className="mt-1 flex items-center justify-between gap-2 text-xs text-gray-400">
                      <span>{t("dailyRateFormula")}</span>
                      {!isLocked && isDailyRateCustom(index, role) && (
                        <button
                          type="button"
                          onClick={() => resetRoleDailyRate(index)}
                          className="text-blue-600 hover:text-blue-800"
                        >
                          {t("resetDailyRate")}
                        </button>
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-right">
                    {!isLocked && (
                      <button
                        type="button"
                        onClick={() => removeRole(index)}
                        disabled={settings.roles.length <= 1}
                        className="text-xs text-red-600 hover:text-red-800 disabled:opacity-40"
                      >
                        {t("removeItem")}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="font-medium">{t("phases")}</h3>
          {renderSectionActions("phases", addPhase)}
        </div>
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left font-medium text-gray-700">{t("phaseName")}</th>
                <th className="px-3 py-2 text-left font-medium text-gray-700">{t("percentage")}</th>
                <th className="px-3 py-2 text-left font-medium text-gray-700">{t("phaseMeaning")}</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {settings.phases.map((phase, index) => {
                const phaseKey = normalizePhaseKey(phase.name);

                return (
                  <tr key={`${phase.name}-${index}`}>
                    <td className="px-3 py-2">
                      <select
                        value={phase.name}
                        onChange={(event) => updatePhase(index, "name", event.target.value)}
                        disabled={fieldsDisabled}
                        className={`${inputClassName} disabled:bg-gray-50 disabled:text-gray-600`}
                      >
                        {!isKnownPhaseKey(phase.name) && phase.name ? (
                          <option value={phase.name}>{phase.name}</option>
                        ) : null}
                        {KNOWN_PHASE_KEYS.map((phaseKey) => (
                          <option key={phaseKey} value={phaseKey}>
                            {t(`phaseLabels.${phaseKey}`)}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-3 py-2">
                      <input
                        type="number"
                        min="0"
                        max="100"
                        step="1"
                        value={Math.round(phase.percentage * 100)}
                        onChange={(event) => updatePhase(index, "percentage", event.target.value)}
                        disabled={fieldsDisabled}
                        className={`${inputClassName} w-24 disabled:bg-gray-50 disabled:text-gray-600`}
                      />
                    </td>
                    <td className="px-3 py-2 text-gray-600">
                      {phaseKey ? t(`phaseMeanings.${phaseKey}`) : "—"}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {!isLocked && (
                        <button
                          type="button"
                          onClick={() => removePhase(index)}
                          disabled={settings.phases.length <= 1}
                          className="text-xs text-red-600 hover:text-red-800 disabled:opacity-40"
                        >
                          {t("removeItem")}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-gray-700">{t("contingency")}</span>
          <input
            type="number"
            min="0"
            max="100"
            value={Math.round(settings.contingency_rate * 100)}
            onChange={(event) => updateRate("contingency_rate", event.target.value)}
            disabled={fieldsDisabled}
            className={`${inputClassName} disabled:bg-gray-50 disabled:text-gray-600`}
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-gray-700">{t("overhead")}</span>
          <input
            type="number"
            min="0"
            max="100"
            value={Math.round(settings.overhead_rate * 100)}
            onChange={(event) => updateRate("overhead_rate", event.target.value)}
            disabled={fieldsDisabled}
            className={`${inputClassName} disabled:bg-gray-50 disabled:text-gray-600`}
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-gray-700">{t("tax")}</span>
          <input
            type="number"
            min="0"
            max="100"
            value={Math.round(settings.tax_rate * 100)}
            onChange={(event) => updateRate("tax_rate", event.target.value)}
            disabled={fieldsDisabled}
            className={`${inputClassName} disabled:bg-gray-50 disabled:text-gray-600`}
          />
        </label>
      </section>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="font-medium">{t("setupCosts")}</h3>
          {renderSectionActions("setup_cost_items", () => addLineItem("setup_cost_items"))}
        </div>
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left font-medium text-gray-700">{t("itemName")}</th>
                <th className="px-3 py-2 text-left font-medium text-gray-700">
                  {t("amount", { symbol: currencySymbol })}
                </th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {settings.setup_cost_items.map((item, index) => (
                <tr key={`setup-${index}`}>
                  <td className="px-3 py-2">
                    <input
                      type="text"
                      value={item.name}
                      onChange={(event) =>
                        updateLineItem("setup_cost_items", index, "name", event.target.value)
                      }
                      disabled={fieldsDisabled}
                      placeholder={translateSetupItem(item.name)}
                      className={`${inputClassName} disabled:bg-gray-50 disabled:text-gray-600`}
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="number"
                      min="0"
                      value={item.amount}
                      onChange={(event) =>
                        updateLineItem("setup_cost_items", index, "amount", event.target.value)
                      }
                      disabled={fieldsDisabled}
                      className={`${inputClassName} disabled:bg-gray-50 disabled:text-gray-600`}
                    />
                  </td>
                  <td className="px-3 py-2 text-right">
                    {!isLocked && (
                      <button
                        type="button"
                        onClick={() => removeLineItem("setup_cost_items", index)}
                        className="text-xs text-red-600 hover:text-red-800"
                      >
                        {t("removeItem")}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              <tr className="bg-gray-50 font-semibold">
                <td className="px-3 py-2">{t("setupTotal")}</td>
                <td className="px-3 py-2">{formatMoney(setupTotal, settings.currency)}</td>
                <td />
              </tr>
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs text-gray-500">{t("setupCostsHint")}</p>
      </section>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="font-medium">{t("monthlyRcItems")}</h3>
          {renderSectionActions("monthly_rc_items", () => addLineItem("monthly_rc_items"))}
        </div>
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left font-medium text-gray-700">{t("itemName")}</th>
                <th className="px-3 py-2 text-left font-medium text-gray-700">
                  {t("amount", { symbol: currencySymbol })}
                </th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {settings.monthly_rc_items.map((item, index) => (
                <tr key={`rc-${index}`}>
                  <td className="px-3 py-2">
                    <input
                      type="text"
                      value={item.name}
                      onChange={(event) =>
                        updateLineItem("monthly_rc_items", index, "name", event.target.value)
                      }
                      disabled={fieldsDisabled}
                      className={`${inputClassName} disabled:bg-gray-50 disabled:text-gray-600`}
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="number"
                      min="0"
                      value={item.amount}
                      onChange={(event) =>
                        updateLineItem("monthly_rc_items", index, "amount", event.target.value)
                      }
                      disabled={fieldsDisabled}
                      className={`${inputClassName} disabled:bg-gray-50 disabled:text-gray-600`}
                    />
                  </td>
                  <td className="px-3 py-2 text-right">
                    {!isLocked && (
                      <button
                        type="button"
                        onClick={() => removeLineItem("monthly_rc_items", index)}
                        className="text-xs text-red-600 hover:text-red-800"
                      >
                        {t("removeItem")}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              <tr className="bg-gray-50 font-semibold">
                <td className="px-3 py-2">{t("monthlyRcSubtotal")}</td>
                <td className="px-3 py-2">{formatMoney(monthlyRcSubtotal, settings.currency)}</td>
                <td />
              </tr>
              <tr className="bg-indigo-50 font-semibold text-indigo-900">
                <td className="px-3 py-2">{t("annualRcSubtotal")}</td>
                <td className="px-3 py-2">{formatMoney(monthlyRcSubtotal * 12, settings.currency)}</td>
                <td />
              </tr>
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs text-gray-500">{t("monthlyRcHint")}</p>
      </section>

      {showAllCardsList && (
        <RateCardList cards={cards} loading={loading} currentCardId={rateCardId || undefined} />
      )}

      <RateCardSectionAiModal
        open={aiModalSection !== null}
        section={aiModalSection}
        rateCardId={rateCardId}
        usageEstimates={usageEstimates}
        onClose={() => setAiModalSection(null)}
        onApply={handleApplyAiSuggestion}
      />
    </div>
  );
}
