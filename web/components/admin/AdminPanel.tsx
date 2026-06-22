"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import AdminHelpReference from "@/components/admin/AdminHelpReference";
import AiSettingsPanel from "@/components/admin/AiSettingsPanel";
import DiscountSettingsPanel from "@/components/admin/DiscountSettingsPanel";
import FormTemplatesPanel from "@/components/admin/FormTemplatesPanel";
import FormulasReference from "@/components/admin/FormulasReference";
import SmtpSettingsPanel from "@/components/admin/SmtpSettingsPanel";
import SystemHealthPanel from "@/components/admin/SystemHealthPanel";
import UserManager from "@/components/admin/UserManager";

type AdminTab =
  | "users"
  | "formTemplates"
  | "discountSettings"
  | "aiSettings"
  | "smtpSettings"
  | "formulas"
  | "help"
  | "system";

const tabs: AdminTab[] = [
  "users",
  "formTemplates",
  "discountSettings",
  "aiSettings",
  "smtpSettings",
  "formulas",
  "help",
  "system",
];

function isAdminTab(value: string | null): value is AdminTab {
  return tabs.includes(value as AdminTab);
}

export default function AdminPanel() {
  const t = useTranslations("admin");
  const router = useRouter();
  const searchParams = useSearchParams();
  const tabParam = searchParams.get("tab");
  const activeTab: AdminTab = isAdminTab(tabParam) ? tabParam : "users";

  const tabLabels: Record<AdminTab, string> = {
    users: t("tabs.users"),
    formTemplates: t("tabs.formTemplates"),
    discountSettings: t("tabs.discountSettings"),
    aiSettings: t("tabs.aiSettings"),
    smtpSettings: t("tabs.smtpSettings"),
    formulas: t("tabs.formulas"),
    help: t("tabs.help"),
    system: t("tabs.system"),
  };

  function setActiveTab(tab: AdminTab) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("tab", tab);
    router.replace(`?${params.toString()}`, { scroll: false });
  }

  return (
    <>
      <div className="mb-6 border-b border-gray-200">
        <nav className="-mb-px flex flex-wrap gap-4" aria-label={t("title")}>
          {tabs.map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              aria-current={activeTab === tab ? "page" : undefined}
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

      {activeTab === "users" && <UserManager />}
      {activeTab === "formTemplates" && <FormTemplatesPanel />}
      {activeTab === "discountSettings" && <DiscountSettingsPanel />}
      {activeTab === "aiSettings" && <AiSettingsPanel />}
      {activeTab === "smtpSettings" && <SmtpSettingsPanel />}
      {activeTab === "formulas" && <FormulasReference />}
      {activeTab === "help" && <AdminHelpReference />}
      {activeTab === "system" && <SystemHealthPanel />}
    </>
  );
}
