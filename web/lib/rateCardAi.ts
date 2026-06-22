export type RateCardAiSection =
  | "roles"
  | "phases"
  | "setup_cost_items"
  | "monthly_rc_items";

export type RateCardAiSuggestResponse = {
  section: RateCardAiSection;
  items: Array<Record<string, unknown>>;
  generation_notes: string;
  replace_all: boolean;
  estimate: {
    estimate_id: string;
    project_name: string;
    client_name: string;
    status: string;
    updated_at: string;
  } | null;
};

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

export type RateCardSettingsLike = {
  roles: RoleRate[];
  phases: PhasePercentage[];
  setup_cost_items: LineItem[];
  monthly_rc_items: LineItem[];
};

const HOURS_PER_DAY = 8;

function normalizeName(value: string): string {
  return value.trim().toLowerCase();
}

function normalizeRole(item: Record<string, unknown>): RoleRate {
  const hourly = Number(item.hourly_rate ?? item.hourly_rate_jpy) || 0;
  const daily =
    item.daily_rate !== undefined && item.daily_rate !== null
      ? Number(item.daily_rate)
      : item.daily_rate_jpy === undefined || item.daily_rate_jpy === null
        ? hourly * HOURS_PER_DAY
        : Number(item.daily_rate_jpy);
  return {
    name: String(item.name ?? "").trim(),
    hourly_rate: hourly,
    daily_rate: daily,
  };
}

function normalizePhase(item: Record<string, unknown>): PhasePercentage {
  return {
    name: String(item.name ?? "").trim(),
    percentage: Number(item.percentage) || 0,
  };
}

function normalizeLineItem(item: Record<string, unknown>): LineItem {
  return {
    name: String(item.name ?? "").trim(),
    amount: Number(item.amount ?? item.amount_jpy) || 0,
  };
}

export function appendSectionItems(
  settings: RateCardSettingsLike,
  response: RateCardAiSuggestResponse,
): RateCardSettingsLike {
  const existingNames = new Set<string>();

  if (response.section === "roles") {
    for (const role of settings.roles) {
      existingNames.add(normalizeName(role.name));
    }
    const additions = response.items
      .map(normalizeRole)
      .filter((item) => item.name && !existingNames.has(normalizeName(item.name)));
    return { ...settings, roles: [...settings.roles, ...additions] };
  }

  if (response.section === "phases") {
    if (response.replace_all) {
      return {
        ...settings,
        phases: response.items.map(normalizePhase).filter((item) => item.name),
      };
    }
    for (const phase of settings.phases) {
      existingNames.add(normalizeName(phase.name));
    }
    const additions = response.items
      .map(normalizePhase)
      .filter((item) => item.name && !existingNames.has(normalizeName(item.name)));
    return { ...settings, phases: [...settings.phases, ...additions] };
  }

  if (response.section === "setup_cost_items") {
    for (const item of settings.setup_cost_items) {
      existingNames.add(normalizeName(item.name));
    }
    const additions = response.items
      .map(normalizeLineItem)
      .filter((item) => item.name && !existingNames.has(normalizeName(item.name)));
    return { ...settings, setup_cost_items: [...settings.setup_cost_items, ...additions] };
  }

  for (const item of settings.monthly_rc_items) {
    existingNames.add(normalizeName(item.name));
  }
  const additions = response.items
    .map(normalizeLineItem)
    .filter((item) => item.name && !existingNames.has(normalizeName(item.name)));
  return { ...settings, monthly_rc_items: [...settings.monthly_rc_items, ...additions] };
}

export function previewItemsForDisplay(
  response: RateCardAiSuggestResponse,
): Array<Record<string, unknown>> {
  if (response.section === "roles") {
    return response.items.map(normalizeRole);
  }
  if (response.section === "phases") {
    return response.items.map(normalizePhase);
  }
  return response.items.map(normalizeLineItem);
}
