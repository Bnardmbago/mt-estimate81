"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { apiJson } from "@/lib/api";

type RoleRate = {
  name: string;
  hourly_rate_jpy: number;
  daily_rate_jpy?: number;
};

type PhasePercentage = {
  name: string;
  percentage: number;
};

type MonthlyRcItem = {
  name: string;
  amount_jpy: number;
};

type RateCardSettings = {
  roles: RoleRate[];
  phases: PhasePercentage[];
  contingency_rate: number;
  overhead_rate: number;
  monthly_rc_items: MonthlyRcItem[];
  default_maintenance_monthly_jpy: number;
  setup_costs: {
    infrastructure_jpy: number;
    tooling_jpy: number;
    third_party_jpy: number;
  };
  productivity: { hours_per_feature_default: number };
  tax_rate: number;
};

type ActiveRateCard = {
  id: string;
  name: string;
  version_number: number;
  version_id: string;
  settings: RateCardSettings;
};

const inputClassName =
  "w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

export default function RateCardEditor() {
  const t = useTranslations("admin.rateCards");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [cardName, setCardName] = useState("");
  const [versionNumber, setVersionNumber] = useState(0);
  const [settings, setSettings] = useState<RateCardSettings | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await apiJson<ActiveRateCard>("/admin/rate-cards/active");
        setCardName(data.name);
        setVersionNumber(data.version_number);
        setSettings({
          ...data.settings,
          default_maintenance_monthly_jpy: data.settings.default_maintenance_monthly_jpy ?? 0,
        });
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : t("loadError"));
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [t]);

  function updateRole(index: number, field: keyof RoleRate, value: string) {
    if (!settings) return;
    const roles = [...settings.roles];
    const role = { ...roles[index] };
    if (field === "name") {
      role.name = value;
    } else {
      role[field] = Number(value);
    }
    roles[index] = role;
    setSettings({ ...settings, roles });
    setSaved(false);
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
    setSaved(false);
  }

  function updateRate(field: "contingency_rate" | "overhead_rate" | "tax_rate", value: string) {
    if (!settings) return;
    setSettings({ ...settings, [field]: Number(value) / 100 });
    setSaved(false);
  }

  function updateSetupCost(
    field: "infrastructure_jpy" | "tooling_jpy" | "third_party_jpy",
    value: string,
  ) {
    if (!settings) return;
    setSettings({
      ...settings,
      setup_costs: { ...settings.setup_costs, [field]: Number(value) },
    });
    setSaved(false);
  }

  function updateMonthlyItem(index: number, field: keyof MonthlyRcItem, value: string) {
    if (!settings) return;
    const items = [...settings.monthly_rc_items];
    const item = { ...items[index] };
    if (field === "name") {
      item.name = value;
    } else {
      item.amount_jpy = Number(value);
    }
    items[index] = item;
    setSettings({ ...settings, monthly_rc_items: items });
    setSaved(false);
  }

  async function handleSave() {
    if (!settings) return;
    setSaving(true);
    setError(null);

    try {
      const data = await apiJson<ActiveRateCard>("/admin/rate-cards", {
        method: "PUT",
        body: JSON.stringify({ settings }),
      });
      setVersionNumber(data.version_number);
      setSettings(data.settings);
      setSaved(true);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : t("saveError"));
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <p className="text-sm text-gray-500">{t("loading")}</p>;
  }

  if (!settings) {
    return (
      <p className="text-sm text-red-600" role="alert">
        {error || t("loadError")}
      </p>
    );
  }

  const phaseSum = settings.phases.reduce((sum, phase) => sum + phase.percentage, 0);
  const monthlyRcSubtotal = settings.monthly_rc_items.reduce(
    (sum, item) => sum + item.amount_jpy,
    0,
  );
  const monthlyRcTotal = monthlyRcSubtotal;

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold">{cardName}</h2>
          <p className="text-sm text-gray-500">{t("version", { number: versionNumber })}</p>
        </div>
        <div className="flex items-center gap-3">
          {saved && <span className="text-sm text-green-600">{t("saved")}</span>}
          <button
            type="button"
            onClick={() => void handleSave()}
            disabled={saving || Math.abs(phaseSum - 1) > 0.001}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? t("saving") : t("save")}
          </button>
        </div>
      </div>

      {error && (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      {Math.abs(phaseSum - 1) > 0.001 && (
        <p className="text-sm text-amber-600" role="alert">
          {t("phaseSumWarning", { percent: (phaseSum * 100).toFixed(1) })}
        </p>
      )}

      <section>
        <h3 className="mb-3 font-medium">{t("roles")}</h3>
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left font-medium text-gray-700">{t("roleName")}</th>
                <th className="px-3 py-2 text-left font-medium text-gray-700">{t("hourlyRate")}</th>
                <th className="px-3 py-2 text-left font-medium text-gray-700">{t("dailyRate")}</th>
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
                      className={inputClassName}
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="number"
                      value={role.hourly_rate_jpy}
                      onChange={(event) =>
                        updateRole(index, "hourly_rate_jpy", event.target.value)
                      }
                      className={inputClassName}
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="number"
                      value={role.daily_rate_jpy ?? role.hourly_rate_jpy * 8}
                      onChange={(event) =>
                        updateRole(index, "daily_rate_jpy", event.target.value)
                      }
                      className={inputClassName}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h3 className="mb-3 font-medium">{t("phases")}</h3>
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left font-medium text-gray-700">{t("phaseName")}</th>
                <th className="px-3 py-2 text-left font-medium text-gray-700">{t("percentage")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {settings.phases.map((phase, index) => (
                <tr key={`${phase.name}-${index}`}>
                  <td className="px-3 py-2">
                    <input
                      type="text"
                      value={phase.name}
                      onChange={(event) => updatePhase(index, "name", event.target.value)}
                      className={inputClassName}
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="number"
                      min="0"
                      max="100"
                      step="1"
                      value={Math.round(phase.percentage * 100)}
                      onChange={(event) => updatePhase(index, "percentage", event.target.value)}
                      className={`${inputClassName} w-24`}
                    />
                  </td>
                </tr>
              ))}
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
            className={inputClassName}
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
            className={inputClassName}
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
            className={inputClassName}
          />
        </label>
      </section>

      <section>
        <h3 className="mb-3 font-medium">{t("setupCosts")}</h3>
        <div className="grid gap-4 sm:grid-cols-3">
          <label className="block text-sm">
            <span className="mb-1 block text-gray-700">{t("infrastructure")}</span>
            <input
              type="number"
              value={settings.setup_costs.infrastructure_jpy}
              onChange={(event) => updateSetupCost("infrastructure_jpy", event.target.value)}
              className={inputClassName}
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-gray-700">{t("tooling")}</span>
            <input
              type="number"
              value={settings.setup_costs.tooling_jpy}
              onChange={(event) => updateSetupCost("tooling_jpy", event.target.value)}
              className={inputClassName}
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-gray-700">{t("thirdParty")}</span>
            <input
              type="number"
              value={settings.setup_costs.third_party_jpy}
              onChange={(event) => updateSetupCost("third_party_jpy", event.target.value)}
              className={inputClassName}
            />
          </label>
        </div>
      </section>

      <section>
        <h3 className="mb-3 font-medium">{t("monthlyRcItems")}</h3>
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left font-medium text-gray-700">{t("itemName")}</th>
                <th className="px-3 py-2 text-left font-medium text-gray-700">{t("amount")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {settings.monthly_rc_items.map((item, index) => (
                <tr key={`${item.name}-${index}`}>
                  <td className="px-3 py-2">
                    <input
                      type="text"
                      value={item.name}
                      onChange={(event) => updateMonthlyItem(index, "name", event.target.value)}
                      className={inputClassName}
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="number"
                      value={item.amount_jpy}
                      onChange={(event) => updateMonthlyItem(index, "amount_jpy", event.target.value)}
                      className={inputClassName}
                    />
                  </td>
                </tr>
              ))}
              <tr className="bg-gray-50 font-semibold">
                <td className="px-3 py-2">{t("monthlyRcSubtotal")}</td>
                <td className="px-3 py-2">¥{monthlyRcSubtotal.toLocaleString()}</td>
              </tr>
              <tr className="bg-gray-50 font-semibold">
                <td className="px-3 py-2">{t("monthlyRcTotal")}</td>
                <td className="px-3 py-2">¥{monthlyRcTotal.toLocaleString()}</td>
              </tr>
              <tr className="bg-indigo-50 font-semibold text-indigo-900">
                <td className="px-3 py-2">{t("annualRcTotal")}</td>
                <td className="px-3 py-2">¥{(monthlyRcTotal * 12).toLocaleString()}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs text-gray-500">{t("monthlyRcHint")}</p>
      </section>
    </div>
  );
}
