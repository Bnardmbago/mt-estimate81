"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import AiSettingsPanel from "@/components/admin/AiSettingsPanel";
import RateCardEditor from "@/components/admin/RateCardEditor";
import SystemHealthPanel from "@/components/admin/SystemHealthPanel";
import UserManager from "@/components/admin/UserManager";

type AdminTab = "rateCards" | "users" | "aiSettings" | "system";

const tabs: AdminTab[] = ["rateCards", "users", "aiSettings", "system"];

export default function AdminPanel() {
  const t = useTranslations("admin");
  const [activeTab, setActiveTab] = useState<AdminTab>("rateCards");

  const tabLabels: Record<AdminTab, string> = {
    rateCards: t("tabs.rateCards"),
    users: t("tabs.users"),
    aiSettings: t("tabs.aiSettings"),
    system: t("tabs.system"),
  };

  return (
    <>
      <div className="mb-6 border-b border-gray-200">
        <nav className="-mb-px flex flex-wrap gap-4">
          {tabs.map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`border-b-2 px-1 py-2 text-sm font-medium transition-colors ${
                activeTab === tab
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
              }`}
            >
              {tabLabels[tab]}
            </button>
          ))}
        </nav>
      </div>

      {activeTab === "rateCards" && <RateCardEditor />}
      {activeTab === "users" && <UserManager />}
      {activeTab === "aiSettings" && <AiSettingsPanel />}
      {activeTab === "system" && <SystemHealthPanel />}
    </>
  );
}
